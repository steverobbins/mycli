import re
import logging
from codecs import open

import click

from . import export
from .main import special_command, NO_QUERY, PARSED_QUERY
from .favoritequeries import favoritequeries

TIMING_ENABLED = False
use_expanded_output = False

@export
def set_timing_enabled(val):
    global TIMING_ENABLED
    TIMING_ENABLED = val

@special_command('\\timing', '\\t', 'Toggle timing of commands.', arg_type=NO_QUERY, aliases=('\\t', ), case_sensitive=True)
def toggle_timing():
    global TIMING_ENABLED
    TIMING_ENABLED = not TIMING_ENABLED
    message = "Timing is "
    message += "on." if TIMING_ENABLED else "off."
    return [(None, None, None, message)]

@export
def is_timing_enabled():
    return TIMING_ENABLED

@export
def set_expanded_output(val):
    global use_expanded_output
    use_expanded_output = val

@export
def is_expanded_output():
    return use_expanded_output

def quit(*args):
    raise NotImplementedError

def stub(*args):
    raise NotImplementedError

_logger = logging.getLogger(__name__)

@export
def editor_command(command):
    """
    Is this an external editor command?
    :param command: string
    """
    # It is possible to have `\e filename` or `SELECT * FROM \e`. So we check
    # for both conditions.
    return command.strip().endswith('\\e') or command.strip().startswith('\\e')

@export
def get_filename(sql):
    if sql.strip().startswith('\\e'):
        command, _, filename = sql.partition(' ')
        return filename.strip() or None

@export
def open_external_editor(filename=None, sql=''):
    """
    Open external editor, wait for the user to type in his query,
    return the query.
    :return: list with one tuple, query as first element.
    """

    sql = sql.strip()

    # The reason we can't simply do .strip('\e') is that it strips characters,
    # not a substring. So it'll strip "e" in the end of the sql also!
    # Ex: "select * from style\e" -> "select * from styl".
    pattern = re.compile('(^\\\e|\\\e$)')
    while pattern.search(sql):
        sql = pattern.sub('', sql)

    message = None
    filename = filename.strip().split(' ', 1)[0] if filename else None

    MARKER = '# Type your query above this line.\n'

    # Populate the editor buffer with the partial sql (if available) and a
    # placeholder comment.
    query = click.edit(sql + '\n\n' + MARKER, filename=filename,
            extension='.sql')

    if filename:
        try:
            with open(filename, encoding='utf-8') as f:
                query = f.read()
        except IOError:
            message = 'Error reading file: %s.' % filename

    if query is not None:
        query = query.split(MARKER, 1)[0].rstrip('\n')
    else:
        # Don't return None for the caller to deal with.
        # Empty string is ok.
        query = sql

    return (query, message)

@special_command('\\f', '\\f [name]', 'List or execute favorite queries.', arg_type=PARSED_QUERY, case_sensitive=True)
def execute_favorite_query(cur, arg):
    """Returns (title, rows, headers, status)"""
    if arg == '':
        return list_favorite_queries()

    query = favoritequeries.get(arg)
    title = '> %s' % (query)
    if query is None:
        message = "No favorite query: %s" % (arg)
        return [(None, None, None, message)]
    cur.execute(query)
    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(title, cur, headers, None)]
    else:
        return [(title, None, None, None)]

def list_favorite_queries():
    """List of all favorite queries.
    Returns (title, rows, headers, status)"""

    headers = ["Name", "Query"]
    rows = [(r, favoritequeries.get(r)) for r in favoritequeries.list()]

    if not rows:
        status = '\nNo favorite queries found.' + favoritequeries.usage
    else:
        status = ''
    return [('', rows, headers, status)]

@special_command('\\fs', '\\fs name query', 'Save a favorite query.')
def save_favorite_query(arg, **_):
    """Save a new favorite query.
    Returns (title, rows, headers, status)"""

    usage = 'Syntax: \\fs name query.\n\n' + favoritequeries.usage
    if not arg:
        return [(None, None, None, usage)]

    name, _, query = arg.partition(' ')

    # If either name or query is missing then print the usage and complain.
    if (not name) or (not query):
        return [(None, None, None,
            usage + 'Err: Both name and query are required.')]

    favoritequeries.save(name, query)
    return [(None, None, None, "Saved.")]

@special_command('\\fd', '\\fd [name]', 'Delete a favorite query.')
def delete_favorite_query(arg, **_):
    """Delete an existing favorite query.
    """
    usage = 'Syntax: \\fd name.\n\n' + favoritequeries.usage
    if not arg:
        return [(None, None, None, usage)]

    status = favoritequeries.delete(arg)

    return [(None, None, None, status)]

