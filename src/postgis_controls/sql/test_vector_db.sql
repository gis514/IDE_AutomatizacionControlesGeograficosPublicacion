/*

functions

*/

CREATE OR REPLACE FUNCTION get_point (t_x int, t_y int) RETURNS geometry AS $$
	SELECT ST_Translate(
			ST_GeomFromText('POINT(0 0)', 4326),
			t_x,
			t_y
	);
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION get_linestring (l_x int, l_y int, t_x int, t_y int, r_d int) RETURNS geometry AS $$
	SELECT ST_Translate(
		ST_Rotate(
			ST_GeomFromText(
				format(
					'LINESTRING(0 0,%1$s %1$s)',
					GREATEST(COALESCE(l_x, 1), 1),
					GREATEST(COALESCE(l_y, 1), 1)
				),
				4326
			),
			r_d * pi() / 180
		),
		t_x,
		t_y
	);
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION get_polygon (l_x int, l_y int, t_x int, t_y int, r_d int) RETURNS geometry AS $$
	SELECT ST_Translate(
		ST_Rotate(
			ST_GeomFromText(
				format(
					'POLYGON((0 0,0 %2$s,%1$s %2$s,%1$s 0,0 0))',
					GREATEST(COALESCE(l_x, 1), 1),
					GREATEST(COALESCE(l_y, 1), 1)
				),
				4326
			),
			r_d * pi() / 180
		),
		t_x,
		t_y
	);
$$ LANGUAGE SQL;

/*
SELECT ST_AsText(get_point(0, 0));
SELECT ST_AsText(get_point(10, 5));
SELECT ST_AsText(get_linestring(1, 1, 0, 0, 0));
SELECT ST_AsText(get_linestring(1, 1, 1, 1, 90));
SELECT ST_AsText(get_polygon(1, 1, 0, 0, 0));
SELECT ST_AsText(get_polygon(3, 1, 1, 1, 180));
*/

/*
	Invalid Geometries
*/
CREATE SCHEMA IF NOT EXISTS invalid_geoms;

DROP TABLE IF EXISTS invalid_geoms.linestrings;
CREATE TABLE invalid_geoms.linestrings (
	id serial,
	geom geometry(LineString, 4326)
);
INSERT INTO invalid_geoms.linestrings ( geom ) VALUES
	(ST_GeomFromText('LineString(0 4,2 3,1 2,3 0)', 4326)),/* valid */
	(ST_GeomFromText('LineString(0 4,3 1,4 3,0 0)', 4326)),/* invalid */
	(ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326)),/* valid */
	(ST_GeomFromText('LineString(2 4,0 3,3 2,4 1,3 0,1 1,2 4)', 4326)),/* invalid */
	(ST_GeomFromText('LineString(0 0,0 0,0 0)', 4326))/* invalid */
;

DROP TABLE IF EXISTS invalid_geoms.polygons;
CREATE TABLE invalid_geoms.polygons (
	id serial,
	geom geometry(Polygon, 4326)
);
INSERT INTO invalid_geoms.polygons (geom) VALUES
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,3 1,2 3,2 2)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,4 1,2 2)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(1 3,2 2,3 3,1 3)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(1 3,2 2,2 4,1 3)', 4326)]
	)),
	(ST_GeomFromText('Polygon((2 4,2 3,1 3,1 1,2 0,4 1,3 3,2 3,2 4))', 4326)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(1 2,1 1,2 0,4 1,3 2,1 2)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 4,1 3,3 3,2 4)', 4326)]
	))
;

/*
	Duplicate Geometries
*/
CREATE SCHEMA IF NOT EXISTS duplicate_geoms;

DROP TABLE IF EXISTS duplicate_geoms.points;
CREATE TABLE duplicate_geoms.points (
	id serial,
	geom geometry(Point, 4326)
);
INSERT INTO duplicate_geoms.points (geom) VALUES
	(ST_GeomFromText('Point(0 4)', 4326)),
	(ST_GeomFromText('Point(0 4)', 4326)),
	(ST_GeomFromText('Point(2 4)', 4326)),
	(ST_GeomFromText('Point(2 4)', 4326)),
	(ST_GeomFromText('Point(0 4)', 4326))
;

DROP TABLE IF EXISTS duplicate_geoms.linestrings;
CREATE TABLE duplicate_geoms.linestrings (
	id serial,
	geom geometry(LineString, 4326)
);
INSERT INTO duplicate_geoms.linestrings (geom) VALUES
	(ST_GeomFromText('LineString(0 4,2 3,1 2,3 0)', 4326)),
	(ST_GeomFromText('LineString(0 4,2 3,1 2,3 0)', 4326)),
	(ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326)),
	(ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326)),
	(ST_GeomFromText('LineString(0 4,2 3,1 2,3 0)', 4326))
;

DROP TABLE IF EXISTS duplicate_geoms.polygons;
CREATE TABLE duplicate_geoms.polygons (
	id serial,
	geom geometry(Polygon, 4326)
);
INSERT INTO duplicate_geoms.polygons (geom) VALUES
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,3 1,2 3,2 2)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,4 1,2 2)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,3 1,2 3,2 2)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,4 1,2 2)', 4326)]
	)),
	(ST_MakePolygon(
		ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326),
		ARRAY[ST_GeomFromText('LineString(2 2,2 1,4 1,2 2)', 4326)]
	))
;

/*
	Multipart Geometries
*/
CREATE SCHEMA IF NOT EXISTS multi_geoms;

DROP TABLE IF EXISTS multi_geoms.points;
CREATE TABLE multi_geoms.points (
	id serial,
	geom geometry
);
INSERT INTO multi_geoms.points (geom) VALUES
	(ST_GeomFromText('Point(0 4)', 4326)),
	(ST_GeomFromText('MultiPoint(0 2,0 6,0 8)', 4326)),
	(ST_GeomFromText('Point(2 4)', 4326)),
	(ST_GeomFromText('MultiPoint(1 4,1 12,1 16)', 4326)),
	(ST_GeomFromText('MultiPoint(3 4)', 4326))
;

DROP TABLE IF EXISTS multi_geoms.linestrings;
CREATE TABLE multi_geoms.linestrings (
	id serial,
	geom geometry
);
INSERT INTO multi_geoms.linestrings (geom) VALUES
	(ST_GeomFromText('MultiLineString((0 4,2 3,1 2,3 0),(1 5,3 4,2 3,4 1))', 4326)),
	(ST_GeomFromText('LineString(0 4,2 3,1 2,3 0)', 4326)),
	(ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326)),
	(ST_GeomFromText('MultiLineString((2 4,1 3,1 1,2 0,4 1,3 3,2 4),(1 5,3 4,2 3,4 1))', 4326)),
	(ST_GeomFromText('MultiLineString((0 4,2 3,1 2,3 0))', 4326))
;

DROP TABLE IF EXISTS multi_geoms.polygons;
CREATE TABLE multi_geoms.polygons (
	id serial,
	geom geometry
);
INSERT INTO multi_geoms.polygons (geom) VALUES
	(ST_GeomFromText('MultiPolygon(((2 4,1 3,1 1,2 0,4 1,3 3,2 4)),((20 40,10 30,10 10,20 10,40 10,30 30,20 40)))', 4326)),
	(ST_GeomFromText('Polygon((2 4,1 3,1 1,2 0,4 1,3 3,2 4))', 4326)),
	(ST_GeomFromText('MultiPolygon(((2 2,2 1,3 1,2 3,2 2)),((20 20,20 10,30 10,20 30,20 20)))', 4326)),
	(ST_GeomFromText('Polygon((2 2,2 1,4 1,2 2))', 4326)),
	(ST_GeomFromText('MultiPolygon(((2 2,2 1,4 1,2 2)))', 4326))
;

/*
	Null Geometries
*/
CREATE SCHEMA IF NOT EXISTS null_geoms;

DROP TABLE IF EXISTS null_geoms.points;
CREATE TABLE null_geoms.points (
	id serial,
	geom geometry(Point, 4326)
);
INSERT INTO null_geoms.points (geom) VALUES
	(ST_GeomFromText('Point(0 4)', 4326)),
	(NULL),
	(ST_GeomFromText('Point(2 4)', 4326)),
	(NULL),
	(NULL)
;

DROP TABLE IF EXISTS null_geoms.linestrings;
CREATE TABLE null_geoms.linestrings (
	id serial,
	geom geometry(LineString, 4326)
);
INSERT INTO null_geoms.linestrings (geom) VALUES
	(NULL),
	(ST_GeomFromText('LineString(0 4,2 3,1 2,3 0)', 4326)),
	(ST_GeomFromText('LineString(2 4,1 3,1 1,2 0,4 1,3 3,2 4)', 4326)),
	(NULL),
	(NULL)
;

DROP TABLE IF EXISTS null_geoms.polygons;
CREATE TABLE null_geoms.polygons (
	id serial,
	geom geometry(Polygon, 4326)
);
INSERT INTO null_geoms.polygons (geom) VALUES
	(NULL),
	(ST_GeomFromText('Polygon((2 4,1 3,1 1,2 0,4 1,3 3,2 4))', 4326)),
	(NULL),
	(ST_GeomFromText('Polygon((2 2,2 1,4 1,2 2))', 4326)),
	(NULL)
;
