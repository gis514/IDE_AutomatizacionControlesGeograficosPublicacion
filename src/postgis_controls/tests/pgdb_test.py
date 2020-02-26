import unittest

from src.postgis_controls.pgdb import (
  InvalidGeomResult, DuplicateGeomResult, MultipartGeomResult, NullGeomResult,
  invalid_geoms_query, duplicate_geoms_query, multipart_geoms_query, null_geoms_query,
  point_in_geojson_geom, intersection_query,
  PGDBManager, PGDBManagerError
)

class TestPGDBManager(unittest.TestCase):
  def setUp(self):
    self.pgdb = PGDBManager(
      'local-data-server', 5432, 'test_vector_db', 'postgres', 'diablo2'
    )
  
  def test_connect(self):
    # self.pgdb.host = 'xxx'
    # with self.assertRaises(PGDBManagerError):
    #   self.pgdb.connect()
    # self.pgdb.host = 'local-data-server'
    self.pgdb.connect()
    self.assertIsNotNone(self.pgdb._conn)
    self.assertIsNotNone(self.pgdb._cursor)

  def test_get_query_result(self):
    self.pgdb.connect()
    rows = self.pgdb.get_query_result(
      'SELECT COUNT(*) FROM invalid_geoms.linestrings;'
    )
    self.assertEqual(len(rows), 1)
    self.assertEqual(rows[0][0], 5)
    with self.assertRaises(Exception):
      rows = self.pgdb.get_query_result(
        'SELECT COUNT(*) FROM xxxx.yyyy;'
      )

  def test_get_schema_tables(self):
    self.pgdb.connect()
    actual = self.pgdb.get_schema_table_names('invalid_geoms')
    self.assertEqual(actual, ['linestrings', 'polygons'])
    actual = self.pgdb.get_schema_table_names('public')
    self.assertEqual(actual, [])

  def test_get_invalid_geoms_from_table(self):
    self.pgdb.connect()
    invs = self.pgdb.get_invalid_geoms_from_table('invalid_geoms', 'linestrings')
    actual = [[inv.id, inv.reason, inv.location] for inv in invs]
    self.assertEqual(
      actual,
      [[2, '', None], [4, '', None], [5, '', None]]
    )

  def test_get_duplicate_geoms_from_table(self):
    self.pgdb.connect()
    dups = self.pgdb.get_duplicate_geoms_from_table('duplicate_geoms', 'points')
    actual = [[dup.id, dup.number] for dup in dups]
    self.assertEqual(
      actual,
      [[1, 3], [3, 2]]
    )

  def test_get_multipart_geoms_from_table(self):
    self.pgdb.connect()
    muls = self.pgdb.get_multipart_geoms_from_table('multi_geoms', 'points')
    actual = [[mul.id, mul.number] for mul in muls]
    self.assertEqual(
      actual,
      [[2, 3], [4, 3], [5, 1]]
    )

  def test_get_null_geoms_from_table(self):
    self.pgdb.connect()
    nuls = self.pgdb.get_null_geoms_from_table('null_geoms', 'points')
    actual = [[nul.id] for nul in nuls]
    self.assertEqual(
      actual,
      [[2], [4], [5]]
    )

class TestPGDBFunctions(unittest.TestCase):
  def test_invalid_geoms_query(self):
    schema = 'invalid_geoms'
    table = 'linestring'
    expected = (
      'SELECT id, '
      'reason(ST_IsValidDetail(geom)), '
      'ST_AsText(location(ST_IsValidDetail(geom))) '
      'FROM {}.{} '
      'WHERE ST_IsValid(geom) = false '
      'ORDER BY id'
    ).format(schema, table)
    actual = invalid_geoms_query(schema, table)
    self.assertEqual(
      actual,
      expected
    )
  
  def test_duplicate_geoms_query(self):
    schema = 'duplicate_geoms'
    table = 'points'
    expected = (
      'SELECT id, row '
      'FROM ('
      'SELECT id, ROW_NUMBER() OVER(PARTITION BY geom ORDER BY id asc) AS row '
      'FROM ONLY {}.{} '
      'WHERE geom IS NOT NULL'
      ') dups '
      'WHERE dups.row > 1 '
      'ORDER BY id'
    ).format(schema, table)
    actual = duplicate_geoms_query(schema, table)
    self.assertEqual(
      actual,
      expected
    )
  
  def test_multipart_geoms_query(self):
    schema = 'multipart_geoms'
    table = 'points'
    expected = (
      'SELECT id, ST_NumGeometries(geom) '
      'FROM {}.{} '
      'WHERE ST_NumGeometries(geom) > 1 '
      'ORDER BY id'
    ).format(schema, table)
    actual = multipart_geoms_query(schema, table)
    self.assertEqual(
      actual,
      expected
    )
  
  def test_null_geoms_query(self):
    schema = 'multipart_geoms'
    table = 'points'
    expected = (
      'SELECT id '
      'FROM {}.{} '
      'WHERE geom IS NULL '
      'ORDER BY id'
    ).format(schema, table)
    actual = null_geoms_query(schema, table)
    self.assertEqual(
      actual,
      expected
    )
  
  def test_point_in_geojson_geom(self):
    self.assertTrue(
      point_in_geojson_geom(
        [0, 0],
        {
          'type': 'LineString',
          'coordinates': [[1, 1], [0, 0], [3, 3]]
        }
      )
    )
    self.assertTrue(
      point_in_geojson_geom(
        [0, 0],
        {
          'type': 'Polygon',
          'coordinates': [
            [[3, 3], [0, 3], [0, 0], [3, 0], [3, 3]],
            [[2, 2], [1, 2], [1, 1], [2, 1], [2, 2]]
          ]
        }
      )
    )
    self.assertTrue(
      point_in_geojson_geom(
        [0, 0],
        {
          'type': 'MultiPolygon',
          'coordinates': [[
            [[3, 3], [0, 3], [0, 0], [3, 0], [3, 3]],
            [[2, 2], [1, 2], [1, 1], [2, 1], [2, 2]]
          ]]
        }
      )
    )
  
  def test_intersection_query(self):
    pass