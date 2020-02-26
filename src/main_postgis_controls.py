'''
postgis_controls.main_postgis_controls
'''
import sys
import argparse
import gettext
import logging

from postgis_controls.enums import Rule
from postgis_controls.pgdb import (
  PGDBManager, PGDBManagerError, InvalidGeomResult, DuplicateGeomResult,
  MultipartGeomResult, NullGeomResult, InvalidGeomResult
)
from common.file import FileManager, FileManagerError
from common.time import TimeManager, TimeManagerError, TimeUnit

_ = gettext.gettext
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_args():
  ''' Get and return arguments from input. '''
  parser = argparse.ArgumentParser(
    description=_(
      'check if all tables in a schema comply or not with selected rules'
    )
  )
  parser.add_argument('dbname', help=_('database name'))
  parser.add_argument('dbschema', help=_('database schema'))
  parser.add_argument('user', help=_('database user'))
  parser.add_argument('password', help=_('database password'))
  parser.add_argument('output', help=_('output folder'))
  parser.add_argument(
    '--host',
    default='localhost',
    help=_('database host')
  )
  parser.add_argument(
    '--port',
    type=int,
    default=5432,
    help=_('database port')
  )
  parser.add_argument(
    '--rule',
    choices=[
      Rule.invalid.value,
      Rule.duplicate.value,
      Rule.multipart.value,
      Rule.intersect.value,
      Rule.null.value,
      Rule.all.value
    ],
    default=Rule.all.value,
    help=_('rule')
  )
  parser.add_argument(
    '--summary',
    default='resumen.txt',
    help=_('summary file name'))
  parser.add_argument(
    '--admissibles',
    help=_('admissible intersections file name'))
  args = parser.parse_args()
  return args

def initFileManager(out_dir, in_dir, rule):
  ''' Initialize and return the file manager, and create output folders. '''
  fman = None
  try:
    fman = FileManager(out_dir, '.')
    if rule == Rule.invalid.value or rule == Rule.all.value:
      fman.add_dir(Rule.invalid.value)
    if rule == Rule.duplicate.value or rule == Rule.all.value:
      fman.add_dir(Rule.duplicate.value)
    if rule == Rule.multipart.value or rule == Rule.all.value:
      fman.add_dir(Rule.multipart.value)
    if rule == Rule.null.value or rule == Rule.all.value:
      fman.add_dir(Rule.null.value)
    if rule == Rule.intersect.value:
      fman.add_dir(Rule.intersect.value)
  except FileManagerError as err:
    logger.error('{}: {}'.format(_('ERROR'), str(err)), exc_info=True)
    fman = None
  return fman

def initPGDB(host, port, dbname, username, password):
  ''' Initialize and return the postgis database manager. '''
  pgdb = None
  try:
    pgdb = PGDBManager(
      host,
      port,
      dbname,
      username,
      password
    )
    pgdb.connect()
  except PGDBManagerError as err:
    logger.error('{}: {}'.format(_('ERROR'), str(err)), exc_info=True)
    pgdb = None
  return pgdb

def initSummaryData(in_params, num_tables, summary_data):
  ''' Initialize and return the summary data. ''' 
  summary_data[_('Parameters')] = in_params
  summary_data[_('Number of tables')] = num_tables
  summary_data[Rule.invalid.value] = []
  summary_data[Rule.duplicate.value] = []
  summary_data[Rule.multipart.value] = []
  summary_data[Rule.null.value] = []
  summary_data[Rule.intersect.value] = []
  return summary_data

def endSummaryData(tman, summary_data):
  ''' Update the process start and end time of the summary data. '''
  summary_data[_('Start time')] = tman.dt_start
  summary_data[_('End time')] = tman.dt_end

def process_result(fman, rule, table, hrow, rows, ks=None):
  ''' Write control result to the detail output file. '''
  if ks:
    for g in ks:
      if rows[g]:
        fman.write_csv_file(
          rule,
          '{}_{}.csv'.format(table, g),
          hrow,
          rows[g].to_list()
        )
  else:
    fman.write_csv_file(rule, '{}.csv'.format(table), hrow, rows)

def control_table(fman, pgdb, rule, dbschema, table, tables, admissibles, summary_data):
  ''' Execute the control to a table. '''
  if rule == Rule.invalid.value or rule == Rule.all.value:
    invs = pgdb.get_invalid_geoms_from_table(dbschema, table)
    if invs:
      process_result(
        fman,
        Rule.invalid.value,
        table,
        [_('id'), _('reason'), _('location')],
        [inv.to_list() for inv in invs]
      )
      summary_data[Rule.invalid.value].append(table)
  if rule == Rule.duplicate.value or rule == Rule.all.value:
    dups = pgdb.get_duplicate_geoms_from_table(dbschema, table)
    if dups:
      process_result(
        fman,
        Rule.duplicate.value,
        table,
        [_('id'), _('amount')],
        [dup.to_list() for dup in dups]
      )
      summary_data[Rule.duplicate.value].append(table)
  if rule == Rule.multipart.value or rule == Rule.all.value:
    muls = pgdb.get_multipart_geoms_from_table(dbschema, table)
    if muls:
      process_result(
        fman,
        Rule.multipart.value,
        table,
        [_('id'), _('number')],
        [mul.to_list() for mul in muls]
      )
      summary_data[Rule.multipart.value].append(table)
  if rule == Rule.null.value or rule == Rule.all.value:
    gmr = pgdb.get_null_geoms_from_table(dbschema, table)
    if gmr:
      process_result(fman, Rule.null.value, table, [_('id')], gmr)
      summary_data[Rule.null.value].append(table)
  if rule == Rule.intersect.value:
    i = tables.index(table) + 1
    if i < len(tables):
      ints = pgdb.get_not_allowed_intersection(
        dbschema,
        table,
        tables[i:],
        admissibles
      )
      if ints:
        process_result(
          fman,
          Rule.intersect.value,
          table,
          [_('table-1'), _('table-1-id'), _('table-2'), _('table-2-id'), 'int', 'err'],
          ints,
          ['point', 'line', 'polygon', 'collection']
        )
        summary_data[Rule.intersect.value].append(table)

if __name__ == '__main__':
  args = get_args()
  fman = initFileManager(args.output, '.', args.rule)
  if not fman:
    sys.exit()
  pgdb = initPGDB(
    args.host,
    args.port,
    args.dbname,
    args.user,
    args.password
  )
  if not pgdb:
    sys.exit()
  admissibles = fman.read_json_file(args.admissibles)
  tables = pgdb.get_schema_table_names(args.dbschema)
  tman = TimeManager()
  summary_data = {}
  initSummaryData(' '.join(sys.argv), len(tables), summary_data)
  logger.info('{}...'.format(_('Processing')))
  logger.info('{}:'.format(_('Tables')))
  for table in tables:
    logger.info('  {}'.format(table[0]))
    control_table(fman, pgdb, args.rule, args.dbschema, table[0], tables, admissibles, summary_data)
  tman.end()
  endSummaryData(tman, summary_data)
  fman.write_txt_file(args.summary, summary_data)
  logger.info('{}.'.format(_('End')))
