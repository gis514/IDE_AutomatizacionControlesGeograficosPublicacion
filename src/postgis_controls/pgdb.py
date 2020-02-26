'''
vector.sources.py
'''

import psycopg2
import uuid
import json
import logging
import gettext

class InvalidGeomResult:
  def __init__(self, id=None, reason=None, location=None):
    self.id = id
    self.reason = reason
    self.location = location
  
  def from_list(self, arr):
    self.id = arr[0]
    self.reason = arr[1]
    self.location = arr[2]

  def to_list(self):
    return [self.id, self.reason, self.location]

class DuplicateGeomResult:
  def __init__(self, id=None, number=None):
    self.id = id
    self.number = number
  
  def from_list(self, arr):
    self.id = arr[0]
    self.number = arr[1]

  def to_list(self):
    return [self.id, self.number]

class MultipartGeomResult:
  def __init__(self, id=None, number=None):
    self.id = id
    self.number = number
  
  def from_list(self, arr):
    self.id = arr[0]
    self.number = arr[1]

  def to_list(self):
    return [self.id, self.number]

class NullGeomResult:
  def __init__(self, id=None):
    self.id = id
  
  def from_list(self, arr):
    self.id = arr[0]

  def to_list(self):
    return [self.id]

class IntersectGeomResult:
  def __init__(self, table1=None, id1=None, table2=None, id2=None, int_geom=None, msg=None):
    self.table1 = table1
    self.id1 = id1
    self.table2 = table2
    self.id2 = id2
    self.int_geom - int_geom
    self.msg = msg
  
  def from_list(self, arr):
    self.table1 = arr[0]
    self.id1 = arr[1]
    self.table2 = arr[1]
    self.id2 = arr[2]
    self.int_geom = arr[3]
    self.msg = arr[4]
  
  def to_list(self):
    return [
      self.table1,
      self.id1,
      self.table2,
      self.id2,
      self.int_geom,
      self.msg
    ]

class NotAllowedIntersectionsResult:
  def __init_(self, point=[], line=[], polygon=[], collection=[]):
    self.point = point
    self.line = line
    self.polygon = polygon
    self.collection = collection

def invalid_geoms_query(schema, table):
  return (
      'SELECT id, '
      'reason(ST_IsValidDetail(geom)), '
      'ST_AsText(location(ST_IsValidDetail(geom))) '
      'FROM {}.{} '
      'WHERE ST_IsValid(geom) = false '
      'ORDER BY id'
    ).format(schema, table)

def duplicate_geoms_query(schema, table):
  return (
      'SELECT id, row '
      'FROM ('
      'SELECT id, ROW_NUMBER() OVER(PARTITION BY geom ORDER BY id asc) AS row '
      'FROM ONLY {}.{} '
      'WHERE geom IS NOT NULL'
      ') dups '
      'WHERE dups.row > 1 '
      'ORDER BY id'
    ).format(schema, table)

def multipart_geoms_query(schema, table):
  return (
      'SELECT id, ST_NumGeometries(geom) '
      'FROM {}.{} '
      'WHERE ST_NumGeometries(geom) > 1 '
      'ORDER BY id'
    ).format(schema, table)

def null_geoms_query(schema, table):
  return (
      'SELECT id '
      'FROM {}.{} '
      'WHERE geom IS NULL '
      'ORDER BY id'
    ).format(schema, table)

def point_in_geojson_geom(point, geom):
  if geom['type'] == 'LineString':
    return point in geom['coordinates']
  elif geom['type'] == 'Polygon' or geom['type'] == 'MultiLineString':
    for coords in geom['coordinates']:
      if point in coords:
        return True
  elif geom['type'] == 'MultiPolygon':
    for pols in geom['coordinates']:
      for coords in pols:
        if point in coords:
          return True
  return False

def intersection_query(schema, table1, table2):
  return (
    'SELECT '
    't1id,'
    't2id,'
    'ST_AsGeoJSON(gi, 3),'
    'ST_AsGeoJSON(g1, 3),'
    'ST_AsGeoJSON(g2, 3),'
    'ST_AsText(ST_Multi(gi)),'
    't1_crosses_t2,'
    'ST_Dimension(gi)'
    'FROM ('
      'SELECT '
      't1.id AS t1id,'
      't2.id AS t2id,'
      't1.geom AS g1,'
      't2.geom AS g2,'
      'ST_Intersection(t1.geom, t2.geom) AS gi,'
      'ST_Crosses(t1.geom, t2.geom) AS t1_crosses_t2'
      'FROM {0}.{1} AS t1, {0}.{2} AS t2'
      'WHERE ST_Intersects(t1.geom, t2.geom) AND NOT ST_Touches(t1.geom, t2.geom)'
      'ORDER BY t1.id'
    ') AS foo'
  ).format(schema, table1, table2)

class PGDBManagerError(Exception):
  pass

class PGDBManager:

  def __init__(
    self,
    host='localhost',
    port=5432,
    dbname=None,
    username='postgres',
    password=None,
    logger=None
    ):
    # parameters
    self.host = host
    self.port = port
    self.dbname = dbname
    self.username = username
    self.password = password
    self.logger = logger or logging.getLogger(__name__)
    # internal
    self._conn = None
    self._cursor = None
    self._ = gettext.gettext

  def connect(self):
    connstr = "host='{}' port='{}' dbname='{}' user='{}' password='{}'"\
    .format(self.host, self.port, self.dbname, self.username, self.password)
    try:
      self._conn = psycopg2.connect(connstr)
      self._cursor = self._conn.cursor()
    except:
      self._conn = None
      self._cursor = None
      msg = '{} {}'.format(self._('Cannot connect to database'), self.dbname)
      self.logger.error(msg, exc_info=True)
      raise PGDBManagerError(msg)

  def get_query_result(self, query):
    sp = uuid.uuid1().hex
    self._cursor.execute('SAVEPOINT "{}"'.format(sp))
    try:
      self._cursor.execute(query)
      rows = self._cursor.fetchall()
    except Exception:
      self._cursor.execute('ROLLBACK TO SAVEPOINT "{}"'.format(sp))
      raise
    else:
      self._cursor.execute('RELEASE SAVEPOINT "{}"'.format(sp))
    return rows

  def get_schema_table_names(self, schema):
    query = (
      'SELECT tablename '
      'FROM pg_tables '
      "WHERE schemaname='{}' "
      'ORDER BY tablename'
    ).format(schema)
    try:
      rows = self.get_query_result(query)
    except:
      msg = '{} {}'.format(self._('Cannot retrieve table names from schema'), schema)
      self.logger.error(msg, exc_info=True)
      raise PGDBManagerError(msg)
    return rows

  def get_invalid_geoms_from_table(self, schema, table):
    query = invalid_geoms_query(schema, table)
    try:
      rows = self.get_query_result(query)
    except:
      msg = '{} {}.{}'.format(
        self._('Cannot retrieve features with invalid geometries from table'),
        schema,
        table
      )
      self.logger.error(msg, exc_info=True)
      raise PGDBManagerError(msg)
    return [InvalidGeomResult(row[0], row[1], row[2]) for row in rows]

  def get_duplicate_geoms_from_table(self, schema, table):
    query = duplicate_geoms_query(schema, table)
    try:
      rows = self.get_query_result(query)
    except:
      msg = '{} {}.{}'.format(
        self._('Cannot retrieve  features with duplicate geometries from table'),
        schema,
        table
      )
      self.logger.error(msg, exc_info=True)
      raise PGDBManagerError(msg)
    return [DuplicateGeomResult(row[0], row[1]) for row in rows]

  def get_multipart_geoms_from_table(self, schema, table):
    query = multipart_geoms_query(schema, table)
    try:
      rows = self.get_query_result(query)
    except:
      msg = '{} {}.{}'.format(
        self._('Cannot retrieve features with multipart geometries from table'),
        schema,
        table
      )
      self.logger.error(msg, exc_info=True)
      raise PGDBManagerError(msg)
    return [MultipartGeomResult(row[0], row[1]) for row in rows]

  def get_null_geoms_from_table(self, schema, table):
    query = null_geoms_query(schema, table)
    try:
      rows = self.get_query_result(query)
    except:
      msg = '{} {}.{}'.format(
        self._('Cannot retrieve features with null geometries from table'),
        schema,
        table
      )
      self.logger.error(msg, exc_info=True)
      raise PGDBManagerError(msg)
    return [NullGeomResult(row[0]) for row in rows]

  def get_not_allowed_intersection(self, schema, table, tables, admissibles):
    values = NotAllowedIntersectionsResult()
    for table2 in tables:
      query = intersection_query(schema, table, table2)
      self.logger.debug(
        '{}: {} - {}'.format(self._('Intersection'), table, table2)
      )
      try:
        rows = self.get_query_result(query)
      except:
        msg = '{0} {1}.{2} {1}.{3}'.format(
          self._('Cannot retrieve intersection geometries between tables'),
          schema,
          table,
          table2
        )
        self.logger.error(msg, exc_info=True)
      for row in rows:
        msg = ''
        geomi = json.loads(row[2])
        # check if intersection is admissible
        if admissibles and table2 in admissibles:
          # check if intersection is a cross
          if row[6]:
            # check if intersection is point or line
            if geomi['type'] == 'Point' or geomi['type'] == 'LineString':
              points = []
              if geomi['type'] == 'Point':
                points = [geomi['coordinates']]
              else:
                points = [geomi['coordinates'][0], geomi['coordinates'][len(geomi['coordinates'])-1]]
              geom1 = json.loads(row[3])
              geom2 = json.loads(row[4])
              # check if is line-line or line-polygon intersection
              if (
                geom1['type'] in ['LineString', 'MultiLineString']
                and
                geom2['type'] in ['LineString', 'MultiLineString']
              ) or\
              (
                geom1['type'] in ['LineString', 'MultiLineString']
                and
                geom2['type'] in ['Polygon', 'MultiPolygon']
              ) or\
              (
                geom1['type'] in ['Polygon', 'MultiPolygon']
                and
                geom2['type'] in ['LineString', 'MultiLineString']
              ):
                ptoi = 0
                while ptoi < len(points) and\
                  (
                    point_in_geojson_geom(points[ptoi], geom1)
                    or
                    point_in_geojson_geom(points[ptoi], geom2)
                  ):
                  ptoi += 1
                if ptoi == len(points):
                  msg = self._('crosses')
              else:
                msg = self._('not a line-line or line-polygon intersection')
            else:
              msg = self._('result intersection is not point or line')
          else:
            msg = self._('invalid addmissible intersection')
        else:
          msg = self._('not addmissible intersection')
        value = IntersectGeomResult(table, row[0], table2, row[1], row[5], msg)
        if msg:
          if geomi['type'] == 'GeometryCollection':
            values.collection.append(value)
          else:
            if row[7] == 0:
              values.point.append(value)
            elif row[7] == 1:
              values.line.append(value)
            else:
              values.polygon.append(value)
    return values
