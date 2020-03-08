""" Module that controls the correct flow of the hydrography.

Examples:
  $python main_pyqgis_controls.py -h.
  $python main_pyqgis_controls.py dbname dbschema user password output rem conf.  
  $python main_pyqgis_controls.py dbname dbschema user password output rem conf.
  $python main.py test_vector_db duplicate_geoms test_user test_password output --server localhost --port 5432.

Attributes:
  _: gettext

pyqgis_controls.main_pyqgis_controls
"""
import sys
import argparse
import json
import gettext
import logging

from qgis.core import QgsApplication, QgsDataSourceUri, QgsVectorLayer
from qgis.core import QgsGeometry, QgsSpatialIndex, QgsWkbTypes, QgsFeature
from PyQt5.QtGui import *
from src.common.time import (
    get_time
)
from common.file import FileManager, FileManagerError

_ = gettext.gettext
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_args():
    """ Get and return arguments from input. """
    parser = argparse.ArgumentParser(
        description=_(
            'check the correct direction of the flow, the existence endorheic basin and that' +
            ' the surfaces at rest have no flow direction.'
        )
    )
    parser.add_argument('dbname', help=_('database name'))
    parser.add_argument('dbschema', help=_('database schema'))
    parser.add_argument('user', help=_('database user'))
    parser.add_argument('password', help=_('database password'))
    parser.add_argument('output', help=_('output folder'))
    parser.add_argument('rem', help=_(
        'shapefile of the polyline with the limits of the consignment'
    ))
    parser.add_argument('conf', help=_('json file with the configuration of the control'))
    parser.add_argument('-s', '--server', default='localhost', help=_('database host'))
    parser.add_argument('-p', '--port', type=int, default=5432, help=_('database port'))
    parser.add_argument('-q', '--dirqgis', default='C:\\OSGeo4W64\\apps\\qgis\\', help=_(
        'osgeo app qgis directori'
    ))
    parser.add_argument('-tol1', '--t1', type=float, default=0.1, help=_('Z lines tolerance'))
    parser.add_argument('-tol2', '--t2', type=float, default=0.01, help=_('Z polygon tolerance'))
    args = parser.parse_args()
    return args

def qgs_init(pp):
    """ PyQGIS initialization. """
    QgsApplication.setPrefixPath(pp, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    return qgs

def qgs_exit(qgs):
    """ Exit PyQGIS. """
    qgs.exitQgis()

def create_indexes(l, u, args):
    """ Return list and dictionary with spatial indexes. """
    logger.info('{}.'.format(_('Constructing spatial indexes...')))

    dic_featid = {}
    l_ind = {}

    for i in l:
        u.setDataSource(args.dbschema, i, "geom")
        vector_layer = QgsVectorLayer(u.uri(False), i, "postgres")
        it_features = vector_layer.getFeatures()
        index = QgsSpatialIndex(it_features)
        l_ind[i] = index

        all_features = {feature.id(): feature['id'] for feature in vector_layer.getFeatures()}
        dic_featid[i] = all_features

    logger.info('{}.'.format(_('Finished contruction of spatial indexes...')))
    return l_ind, dic_featid

def init_file_manager(out_dir):
    """ Initialize and return the file manager, and create output folders. """
    fman = None
    try:
        fman = FileManager(out_dir, '.')
    except FileManagerError as err:
        logger.error('{}: {}'.format(_('ERROR'), str(err)), exc_info=True)
        fman = None
    return fman

def get_intersections_continuity(c, json_cont):
    """ Return list with the layers to intersect, given one layer. """
    return json_cont[c]

def control_1(capa1, uri, args, nom_sal, fman):
    """ Verify the correct flow of the layer. """
    uri.setDataSource(args.dbschema, capa1, "geom")
    capa_eje = QgsVectorLayer(uri.uri(False), capa1, "postgres")
    iterador_features = capa_eje.getFeatures()
    cantidad_errores = 0
    for feature in iterador_features:
        geometria_feature = feature.geometry()
        vertices_feature = geometria_feature.vertices()
        cantidad_vertices = 0
        min_altura = 0
        max_altura = 0
        flujo = ''
        pedir_nuevo_punto = False
        tiene_error = False
        while (vertices_feature.hasNext() and (not tiene_error)):
            cantidad_vertices = cantidad_vertices + 1
            punto_vertice = vertices_feature.next()
            if cantidad_vertices == 1:
                first_vertex = punto_vertice.z()

            if ((cantidad_vertices == 2) or pedir_nuevo_punto):
                altura_2 = punto_vertice.z()
                if abs(altura_2 - first_vertex) > args.t1:
                    if (altura_2 - first_vertex) > 0:
                        flujo = _('up')
                        pedir_nuevo_punto = False
                        max_altura = altura_2
                    elif (altura_2 - first_vertex) < 0:
                        flujo = _('down')
                        pedir_nuevo_punto = False
                        min_altura = altura_anterior
                else:
                    pedir_nuevo_punto = True
            elif (cantidad_vertices != 1 and not pedir_nuevo_punto):
                # Verify that the next vertex has the same flow direction with the previous
                if flujo == _('down'):
                    if (punto_vertice.z() - altura_anterior > args.t1) or (
                            punto_vertice.z() - min_altura > args.t1):
                        if (punto_vertice.z() - altura_anterior) > args.t1:
                            dif_imprimir = punto_vertice.z() - altura_anterior
                            texto_imprimir = _('Error - Previous vertex inflexion')
                        else:
                            dif_imprimir = punto_vertice.z() - min_altura
                            texto_imprimir = _('Error - Relative inflexion')
                        tiene_error = True
                        cantidad_errores = cantidad_errores + 1
                        fman.append_csv_file(nom_sal, [
                            capa1, feature['id'], texto_imprimir, punto_vertice.z(),
                            abs(dif_imprimir), punto_vertice.x(), punto_vertice.y()])
                    if punto_vertice.z() < min_altura:
                        min_altura = punto_vertice.z()
                else:
                    if (punto_vertice.z() - altura_anterior < -1 * args.t1) or (
                            punto_vertice.z() - max_altura < -1 * args.t1):
                        if (punto_vertice.z() - altura_anterior) < (-1 * args.t1):
                            dif_imprimir = punto_vertice.z() - altura_anterior
                            texto_imprimir = _('Error - Previous vertex inflexion')
                        else:
                            dif_imprimir = punto_vertice.z() - max_altura
                            texto_imprimir = _('Error - Relative inflexion')
                        tiene_error = True
                        cantidad_errores = cantidad_errores + 1
                        fman.append_csv_file(nom_sal, [
                            capa1, feature['id'], texto_imprimir, punto_vertice.z(),
                            abs(dif_imprimir), punto_vertice.x(), punto_vertice.y()
                            ])
                    if punto_vertice.z() > max_altura:
                        max_altura = punto_vertice.z()
            altura_anterior = punto_vertice.z()

def control(capa_verificar, c, l_capas_interectar, u, lindx, n_sal, args, df, l_continuity, fman):
    """ Return two list. The first list has the features to be possible max height,
     and the second list possible endorreics. """
    posible_endorreica = []
    posible_cota_1 = []
    posible_cota_2 = []
    contador = 0
    indice_capa = lindx[c]

    hrow = [_('Input_Layer'), _('OBJECTID'), _('Description'), _('Height'),
            _('Height_difference'), _('X_Coordinate'), _('Y_Coordinate')]
    fman.start_csv_file(n_sal, hrow)

    it_features = capa_verificar.getFeatures()
    lc_inter = get_intersections_continuity(c, l_continuity)

    for feature in it_features:
        feature_id = feature['id']
        contador = contador + 1
        feature_id2 = feature.id()

        contador_intersecciones = 0
        c_1 = 0
        c_2 = 0

        geometria = feature.geometry()
        if (not geometria.isNull() and not geometria.isEmpty()):
            lines = geometria.constGet()
            n_vertices = lines.vertexCount()

            primer_vertice = geometria.vertexAt(0)
            ultimo_vertice = geometria.vertexAt(n_vertices-1)
            (c_1, c_2) = interseccion_misma_z(
                c, u, primer_vertice, ultimo_vertice, fman, n_sal, feature_id,
                indice_capa, args, df, lindx, lc_inter)

            contador_intersecciones = c_1 + c_2
            # Posible endorreics
            if contador_intersecciones == 2:
                posible_endorreica.append(feature_id2)
            else:
                # Posible max height
                if c_1 == 1:
                    posible_cota_1.append([feature_id2, primer_vertice.z()])
                if c_2 == 1:
                    posible_cota_2.append([feature_id2, ultimo_vertice.z()])
    posibles_cotas = posible_cota_1 + posible_cota_2
    return (posibles_cotas, posible_endorreica)

def interseccion_misma_z(
        in_capa, in_uri, v1, v2, fman, n_out, fid, indx, args, df, lindx, lc_inter
    ):
    """ Return the number of intersection of the first and last vertex with the input layer."""
    altura1 = v1.z()
    altura2 = v2.z()
    geom_v1 = QgsGeometry(v1)
    geom_v2 = QgsGeometry(v2)
    contador1 = 0
    contador2 = 0

    in_uri.setDataSource(args.dbschema, in_capa, "geom")
    capa_iterar = QgsVectorLayer(in_uri.uri(False), in_capa, "postgres")

    lista_i1 = indx.intersects(geom_v1.boundingBox())
    features_intersect1 = capa_iterar.getFeatures(lista_i1)
    lista_features_inter1 = []

    for feature2 in features_intersect1:
        geometria2 = feature2.geometry()
        if geom_v1.intersects(geometria2):
            contador1 = contador1 + 1
            geom_inter = geom_v1.intersection(geometria2)
            lista_features_inter1.append(feature2.id())
            interseccion_misma_z2(in_capa, geom_inter, altura1, fid, fman, n_out, args)
    bandera_repetido = False
    if contador1 == 2:
        # If exists two intersection, check the continuity
        # Verify if the features have the same atributes
        if same_feat(lista_features_inter1, capa_iterar):
            f = QgsFeature(fid)
            f.setGeometry(geom_v1)

            # Chequeo si intersecta otra capa de las definidas
            if not interseccion_todas_capas(in_capa, f, lc_inter, lindx, args):
                bandera_repetido = True
                fman.append_csv_file(n_out, [in_capa, fid, _('Error - Continuity'), '', ''])

    lista_i2 = indx.intersects(geom_v2.boundingBox())
    features_intersect2 = capa_iterar.getFeatures(lista_i2)
    lista_features_inter2 = []

    for feature2 in features_intersect2:
        geometria2 = feature2.geometry()
        if geom_v2.intersects(geometria2):
            contador2 = contador2 + 1
            geom_inter = geom_v2.intersection(geometria2)
            lista_features_inter2.append(feature2.id())
            interseccion_misma_z2(in_capa, geom_inter, altura2, fid, fman, n_out, args)
    if contador2 == 2:
        if ((not bandera_repetido) and (same_feat(lista_features_inter2, capa_iterar))):
            f = QgsFeature(fid)
            f.setGeometry(geom_v2)

            # Verify if intersects with the other layers
            if not interseccion_todas_capas(in_capa, f, lc_inter, lindx, args):
                fman.append_csv_file(n_out, [in_capa, fid, _('Error - Continuity'), '', ''])

    return (contador1, contador2)

def same_feat(lf, c):
    """ Return True if the two features have the same atributes. """
    feat1 = c.getFeature(lf[0])
    feat2 = c.getFeature(lf[1])
    return feat1.attributes()[1:] == feat2.attributes()[1:]

def interseccion_misma_z2(c, g, altura, fid, fman, n_out, args):
    """ Writes in file if the intersect geometry has different height from the vertex. """
    # Point intersection
    if g.wkbType() == QgsWkbTypes.PointZ:
        if abs(g.constGet().z() - altura) >= args.t2:
            fman.append_csv_file(
                n_out, [
                    c, fid, _('Error - Difference in height intersection'),
                    altura, abs(g.constGet().z() - altura), g.constGet().x(), g.constGet().y()])

    # Polyline intersection
    elif (g.wkbType() == QgsWkbTypes.LineStringZ or g.wkbType() == QgsWkbTypes.MultiLineStringZ):
        it_vertices = g.vertices()
        has_error = False
        while (it_vertices.hasNext() and (not has_error)):
            p_vertice = it_vertices.next()
            if abs(p_vertice.z() - altura) >= args.t2:
                fman.append_csv_file(
                    n_out, [
                        c, fid, _('Error - Difference in height intersection'),
                        altura, abs(p_vertice.z() - altura), p_vertice.x(), p_vertice.y()])
                has_error = True

    # MultiPoint intersection
    elif g.wkbType() == QgsWkbTypes.MultiPointZ:
        multipolygon = g.constGet()
        num_geom = g.numGeometries()
        for i in range(num_geom):
            punto = multipolygon.geometryN(i)
            if abs(punto.z() - altura) >= args.t2:
                fman.append_csv_file(
                    n_out, [
                        c, fid, _('Error - Difference in height intersection'), altura,
                        abs(punto.z() - altura), punto.x(), punto.y()])
                break

def is_max_height(c, c_nom, l_fid, l_ci, l_index, args):
    """ Return list of errors of nodes whos have not the max height. """
    id_itera = []
    alt_itera = []
    resultado = []
    for fid in l_fid:
        id_itera.append(fid[0])
        alt_itera.append(fid[0])
    count = 0
    it_feat3 = c.getFeatures(id_itera)
    for feat_id in it_feat3:
        geom_f = feat_id.geometry()
        vertices_f = geom_f.vertices()
        encontre = False
        while (vertices_f.hasNext() and not encontre):
            p_verti = vertices_f.next()
            if p_verti.z() > alt_itera[count]:
                encontre = True
        if encontre:
            ritc = interseccion_todas_capas(c_nom, feat_id, l_ci, l_index, args)
            if not ritc:
                resultado.append([
                    c_nom, feat_id['id'], _('Error - Node with no maximum height'), '', '', '', ''])
        count = count + 1
    return resultado

def is_endorreics(c, le, u, geom_remesa, l_index, l_inter, args):
    """ Return list of endorheic currents."""
    u.setDataSource(args.dbschema, c, "geom")
    capa = QgsVectorLayer(u.uri(False), c, "postgres")
    resultado = []
    for e in le:
        f = capa.getFeature(e)
        fid = f['id']
        if not f.geometry().intersects(geom_remesa):
            existe_inter = interseccion_todas_capas(c, f, l_inter, l_index, args)
            if not existe_inter:
                resultado.append([c, fid, _('Error - Endorheic'), '', '', '', ''])
    return resultado

def interseccion_todas_capas(c, f, lc, l_index, args):
    """ Return true if exist intesection with other layers, false otherwise. """
    uri2 = QgsDataSourceUri()
    uri2.setConnection(args.server, str(args.port), args.dbname, args.user, args.password)

    geom = f.geometry()
    bbox_geom = geom.boundingBox()

    for cap in lc:
        if cap != c:
            index_capa = l_index[cap]
            lfea = index_capa.intersects(bbox_geom)
            uri2.setDataSource(args.dbschema, cap, "geom")
            capa_inter = QgsVectorLayer(uri2.uri(False), cap, 'postgres')
            if lfea != []:
                it_feat = capa_inter.getFeatures(lfea)
                for f_inter in it_feat:
                    geom_inter = f_inter.geometry()
                    if geom_inter.intersects(geom):
                        return True
    return False

def control_4(capa_4, uri, indices, args, nam_sal, lista_intersectar, fman):
    """ Verify that the height is constant. """
    uri.setDataSource(args.dbschema, capa_4, "geom")
    capa_eje = QgsVectorLayer(uri.uri(False), capa_4, "postgres")
    iterador_features = capa_eje.getFeatures()

    hrow = [_('Input_Layer'), _('OBJECTID'), _('Description'), _('Intersection_Layer'),
            _('OBJECTID'), _('Height'), _('Height_difference'), _('X_Coordinate'), _('Y_Coordinate')
            ]
    fman.start_csv_file(nam_sal, hrow)

    # Iterate with the features of the layer
    for feature in iterador_features:
        geometria_feature = feature.geometry()
        vertices_feature = geometria_feature.vertices()
        primer_vertice = True
        hay_error = False
        alt_total = 0
        # The first vertex determine the height of the polygon
        while vertices_feature.hasNext():
            punto_vertice = vertices_feature.next()
            alt_actual = punto_vertice.z()
            if primer_vertice:
                alt_total = alt_actual
                primer_vertice = False
            if abs(alt_total - alt_actual) >= args.t2:
                fman.append_csv_file(
                    nam_sal, [
                        capa_4, feature['id'], _('Error - Polygon height'), '', '',
                        alt_total, abs(alt_total - alt_actual), punto_vertice.x(),
                        punto_vertice.y()])
                hay_error = True
        # Verify the intersection has the same height
        if not hay_error:
            for capa in lista_intersectar:
                intersectar_capa(
                    capa, geometria_feature, alt_total, capa_4,
                    feature['id'], uri, indices, args, fman, nam_sal)

def intersectar_capa(
        c, g_f, altura_pol, c_original, fea_original, uri, indexs, args, fman, nam_sal):
    """ Intersect with layer verifing that the height is the same. """
    uri.setDataSource(args.dbschema, c, "geom")
    capa_cargada = QgsVectorLayer(uri.uri(False), c, "postgres")

    index = indexs[c]
    hay_error = False
    lista_resultante = index.intersects(g_f.boundingBox())
    features_intersect = capa_cargada.getFeatures(lista_resultante)
    for f in features_intersect:
        if g_f.intersects(f.geometry()):
            geom_interseccion = g_f.intersection(f.geometry())
            # Interseccion punto
            if geom_interseccion.wkbType() == QgsWkbTypes.PointZ:
                if abs(geom_interseccion.get().z() - altura_pol) >= args.t2:
                    fman.append_csv_file(nam_sal, [
                        c_original, fea_original, _('Error - Intersection  height'), c, f['id'],
                        altura_pol, altura_pol - geom_interseccion.get().z()])

            # Interseccion linea o multilinea
            elif (
                    geom_interseccion.wkbType() == QgsWkbTypes.LineStringZ or
                    geom_interseccion.wkbType() == QgsWkbTypes.MultiLineStringZ):
                it_vertices = geom_interseccion.vertices()
                while (it_vertices.hasNext() and (not hay_error)):
                    p_vertice = it_vertices.next()
                    if abs(p_vertice.z() - altura_pol) >= args.t2:
                        fman.append_csv_file(
                            nam_sal, [
                                c_original, fea_original, _('Error - Intersection  height'), c,
                                f['id'], altura_pol, altura_pol - p_vertice.z()])
                        hay_error = True

            # Interseccion multipunto
            elif geom_interseccion.wkbType() == QgsWkbTypes.MultiPointZ:
                multipolygon = geom_interseccion.get()
                num_geom = multipolygon.numGeometries()
                for i in range(num_geom):
                    punto = multipolygon.geometryN(i)
                    if abs(punto.z() - altura_pol) >= args.t2:
                        fman.append_csv_file(nam_sal, [
                            c_original, fea_original, _('Error - Intersection  height'), c, f['id'],
                            altura_pol, altura_pol - punto.z()])
                        break
            else:
                fman.append_csv_file(nam_sal, [geom_interseccion.wkbType()])

def get_geometry_layer(dir_layer):
    """ Return the geometry of one feature of a layer. """
    vector_layer = QgsVectorLayer(dir_layer, 'layer', "ogr")
    it_features = vector_layer.getFeatures()
    for feature in it_features:
        f = feature
    return f.geometry()

def load_config(dir_file_conf):
    """ Return the json configuration of the control. """
    with open(dir_file_conf) as json_data:
        file = json.load(json_data)
    return file

if __name__ == '__main__':
    args = get_args()
    params = ' '.join(sys.argv)

    # start qgis
    qgs = qgs_init(args.dirqgis)

    # uri conection db
    uri = QgsDataSourceUri()
    uri.setConnection(args.server, str(args.port), args.dbname, args.user, args.password)

    # load configuration
    f_config = load_config(args.conf)

    # initialization of variables
    l_ind = {}
    d_feat = {}
    l_continuity = f_config["continuidad"]
    fman = init_file_manager(args.output)
    consignment_geometry = get_geometry_layer(args.rem)

    l_ind, d_feat = create_indexes(f_config["indices"], uri, args)

    # iteration of layers to verify control 1, 2, 3
    for name_l_flow in f_config["flujo"]:
        date_time = get_time().strftime("%Y%m%d_%H%M%S_")
        logger.info('{}: {}.'.format(_('Control 1,2,3: Verifing layer'), name_l_flow))
        uri.setDataSource(args.dbschema, name_l_flow, "geom")
        layer_check = QgsVectorLayer(uri.uri(False), name_l_flow, "postgres")
        result_name = args.dbschema + '_' + date_time \
            + 'Control_Vertex_Height_' + name_l_flow +'.csv'
        cotas, endorreicas = control(
            layer_check, name_l_flow, f_config["endorreicas"],
            uri, l_ind, result_name, args, d_feat, l_continuity, fman)
        r_cota = is_max_height(
            layer_check, name_l_flow, cotas, f_config["endorreicas"], l_ind, args)
        r_endo = is_endorreics(
            name_l_flow, endorreicas, uri, consignment_geometry,
            l_ind, f_config["endorreicas"], args)
        fman.append_csv_file(result_name, r_cota)
        fman.append_csv_file(result_name, r_endo)

        control_1(name_l_flow, uri, args, result_name, fman)

    # iteration of layers to verify control 4
    for name_l_constant_height in f_config["altura_area"]:
        date_time = get_time().strftime("%Y%m%d_%H%M%S_")
        logger.info('{}: {}.'.format(_('Control 4: Verifing layer'), name_l_constant_height))
        result_name = args.dbschema + '_' + date_time + 'Control_Polygon_Height_' \
            + name_l_constant_height +'.csv'
        control_4(name_l_constant_height, uri, l_ind, args, result_name, f_config["flujo"], fman)

    logger.info('{}.'.format(_('End')))
    # exit qgis
    qgs_exit(qgs)
