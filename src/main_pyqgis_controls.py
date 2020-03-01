'''
pyqgis_controls.main_pyqgis_controls
'''
import sys
import os
import errno
import argparse
import csv 
import json
import gettext
import logging

from qgis.core import QgsApplication, QgsDataSourceUri, QgsVectorLayer, QgsGeometry, QgsSpatialIndex, QgsWkbTypes, QgsFeatureRequest, QgsFeature
from osgeo import ogr
from PyQt5.QtGui import *
from src.common.time import (
  get_time
)

_ = gettext.gettext
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def getArgs():
    ''' Get and return arguments from input. '''
    parser = argparse.ArgumentParser(
        description = _(
            'check the correct direction of the flow, the existence endorheic basin and that the surfaces at rest have no flow direction.'
        )
    )
    parser.add_argument('dbname', help=_('database name'))
    parser.add_argument('dbschema', help=_('database schema'))
    parser.add_argument('user', help=_('database user'))
    parser.add_argument('password', help=_('database password'))
    parser.add_argument('output', help=_('output folder'))
    parser.add_argument('rem', help=_('shapefile of the polyline with the limits of the consignment'))
    parser.add_argument('conf', help=_('json file with the configuration of the control'))
    parser.add_argument('-s', '--server', default='localhost', help=_('database host'))    
    parser.add_argument('-p', '--port', type=int, default=5432, help=_('database port'))
    parser.add_argument('-q', '--dirqgis', default='C:\\OSGeo4W64\\apps\\qgis\\', help=_('osgeo app qgis directori'))
    parser.add_argument('-tol1', '--t1', type=float, default=0.1, help=_('Z lines tolerance'))
    parser.add_argument('-tol2', '--t2', type=float, default=0.01, help=_('Z polygon tolerance'))
    args = parser.parse_args()
    return args   

def qgsInit(pp):
    ''' PyQGIS initialization. '''
    QgsApplication.setPrefixPath(pp, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    return qgs

def qgsExit(qgs):
    ''' Exit PyQGIS. '''
    qgs.exitQgis()

def create_indexes(l, u, args):    
    ''' Return list and dictionary with spatial indexes. '''
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

def appendRowsToDetailOutputFile(f, rows):    
    with open(f, 'a', newline = '') as csvfile:
        writer = csv.writer(csvfile)
        for r in rows:    
            writer.writerow(r)

def get_intersecciones_continuidad(c, json_cont):
    # Devuelve lista a intersectar dado una capa para el control de continuidad        
    return json_cont[c]  

def control_1(capa1, uri, args, nom_sal):    
    uri.setDataSource(args.dbschema, capa1, "geom")
    capa_eje = QgsVectorLayer(uri.uri(False), capa1, "postgres")    
    with open(nom_sal, 'a') as csv_file:
        writer = csv.writer(csv_file, lineterminator='\n')  	        
        # Obtengo iterador de los features de la capa
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
                if (cantidad_vertices == 1):
                    first_vertex = punto_vertice.z()
                    
                if ((cantidad_vertices == 2) or pedir_nuevo_punto):
                    altura_2 = punto_vertice.z() 
                    if (abs(altura_2 - first_vertex) > tolerancia):       			
                        if (altura_2 - first_vertex > 0):
                            flujo = 'sube'			
                            pedir_nuevo_punto = False
                            max_altura = altura_2
                        elif (altura_2 - first_vertex < 0):
                            flujo = 'baja'
                            pedir_nuevo_punto = False				
                            min_altura = altura_anterior
                    else:
                        pedir_nuevo_punto = True			    
                elif (cantidad_vertices != 1 and not pedir_nuevo_punto):
                    # Se verifica que el siguiente vertice tenga el mismo flujo que los anteriores
                    if (flujo == 'baja'):                        
                        if (punto_vertice.z() - altura_anterior > tolerancia) or (punto_vertice.z() - min_altura > tolerancia):
                            if (punto_vertice.z() - altura_anterior > tolerancia):
                                dif_imprimir = punto_vertice.z() - altura_anterior
                                texto_imprimir = 'Inflexion vertice anterior'
                            else:
                                dif_imprimir = punto_vertice.z() - min_altura
                                texto_imprimir = 'Inflexion relativa'
                            tiene_error = True                        
                            cantidad_errores = cantidad_errores + 1	
                            writer.writerow([capa1, feature['id'], texto_imprimir, punto_vertice.z(), abs(dif_imprimir),  punto_vertice.x(), punto_vertice.y()])
                        if (punto_vertice.z() < min_altura):
                            min_altura = punto_vertice.z()
                    else: 			
                        if (punto_vertice.z() - altura_anterior < -1 * tolerancia) or (punto_vertice.z() - max_altura < -1 * tolerancia):
                            if (punto_vertice.z() - altura_anterior < -1 * tolerancia):
                                dif_imprimir = punto_vertice.z() - altura_anterior
                                texto_imprimir = 'Inflexion vertice anterior'
                            else:
                                dif_imprimir = punto_vertice.z() - max_altura
                                texto_imprimir = 'Inflexion relativa'
                            tiene_error = True                        
                            cantidad_errores = cantidad_errores + 1                    
                            writer.writerow([capa1, feature['id'], texto_imprimir, punto_vertice.z(), abs(dif_imprimir), punto_vertice.x(), punto_vertice.y()])
                        if (punto_vertice.z() > max_altura):
                            max_altura = punto_vertice.z()	
                altura_anterior = punto_vertice.z()

def control(capa_verificar, c, l_capas_interectar, r, u, lindx, n_sal, args, df, l_continuidad):                
    posible_endorreica = []
    posible_cota_1 = []
    posible_cota_2 = []
    indice_capa = lindx[c]

    with open(n_sal, 'w') as csv_file:
        writer = csv.writer(csv_file, lineterminator='\n')  	
        writer.writerow(['Capa_Entrada', 'OBJECTID', 'Descripcion', 'Altura', 'Diferencia Altura', 'CoordenadaX', 'CoordenadaY'])	        
        it_features = capa_verificar.getFeatures()    

        lc_inter = get_intersecciones_continuidad(c, l_continuidad)     
                
        contador = 0        
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
                (c_1, c_2) = interseccion_misma_z(c, u, primer_vertice, ultimo_vertice, writer, feature_id, indice_capa, args, df, lindx, lc_inter) 
                
                contador_intersecciones = c_1 + c_2                
                # Posible endorreica
                if (contador_intersecciones == 2):
                    posible_endorreica.append(feature_id2)
                else:
                    # Posibles cotas
                    if (c_1 == 1):
                        posible_cota_1.append([feature_id2, primer_vertice.z()])
                    if (c_2 == 1):
                        posible_cota_2.append([feature_id2, ultimo_vertice.z()])                             
        posibles_cotas = posible_cota_1 + posible_cota_2        
        return (posibles_cotas, posible_endorreica)

def interseccion_misma_z(in_capa, in_uri, v1, v2, w, fid, indx, args, df, lindx, lc_inter):    
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
            if (geom_v1.intersects(geometria2)):                
                contador1 = contador1 + 1
                geom_inter =  geom_v1.intersection(geometria2)
                lista_features_inter1.append(feature2.id())
                interseccion_misma_z2(in_capa, geom_inter, altura1, fid, w)            
    bandera_repetido = False
    if (contador1 == 2):
        # Si existen unicamente dos intersecciones, me fijo la continuidad
        # Chequeo si tienen los mismo atributos
        if (iguales_feat(lista_features_inter1, capa_iterar)):
            f = QgsFeature(fid)
            f.setGeometry(geom_v1)
            
            # Chequeo si intersecta otra capa de las definidas            
            if not(interseccion_todas_capas(in_capa, f, lc_inter, lindx, args)):
                bandera_repetido = True
                w.writerow([in_capa, fid, 'Error de continuidad', '', ''])

    lista_i2 = indx.intersects(geom_v2.boundingBox())
    features_intersect2 = capa_iterar.getFeatures(lista_i2)
    lista_features_inter2 = []

    for feature2 in features_intersect2: 
        geometria2 = feature2.geometry()        
        if (geom_v2.intersects(geometria2)):
            contador2 = contador2 + 1
            geom_inter =  geom_v2.intersection(geometria2)
            lista_features_inter2.append(feature2.id())
            interseccion_misma_z2(in_capa, geom_inter, altura2, fid, w)                    
    if (contador2 == 2):
        if ((not bandera_repetido) and (iguales_feat(lista_features_inter2, capa_iterar))): 
            f = QgsFeature(fid)
            f.setGeometry(geom_v2)
            
            # Chequeo si intersecta otra capa de las definidas            
            if not(interseccion_todas_capas(in_capa, f, lc_inter, lindx, args)):           
                w.writerow([in_capa, fid, 'Error de continuidad', '', '']) 
    #print (contador1, contador2)       
    return (contador1, contador2)

def iguales_feat(lf, c):
    # Funcion devuelve true si la lista de features tiene los mismos atributos
    feat1 = c.getFeature(lf[0])
    feat2 = c.getFeature(lf[1])
    return feat1.attributes()[1:] == feat2.attributes()[1:]

def interseccion_misma_z2(c, g, altura, fid, writer):
    # Interseccion punto
    if (g.wkbType() == QgsWkbTypes.PointZ):
        if (abs(g.constGet().z() - altura) >= tolerancia_poligono):
            writer.writerow([c, fid, 'Error en interseccion altura',altura, abs(g.constGet().z() - altura), g.constGet().x(), g.constGet().y()])
            
    # Interseccion linea o multilinea
    elif (g.wkbType() == QgsWkbTypes.LineStringZ or g.wkbType() == QgsWkbTypes.MultiLineStringZ):			
        it_vertices = g.vertices()
        hay_error = False                 				
        while (it_vertices.hasNext() and (not hay_error)):
            p_vertice = it_vertices.next()
            if (abs(p_vertice.z() - altura) >= tolerancia_poligono):
                writer.writerow([c, fid, 'Error en interseccion altura', altura, abs(p_vertice.z() - altura), p_vertice.x(), p_vertice.y()])
                hay_error= True
                
    # Interseccion multipunto			
    elif (g.wkbType() == QgsWkbTypes.MultiPointZ):
        multipolygon = g.constGet()
        num_geom = g.numGeometries()
        for i in range(num_geom):
            punto = multipolygon.geometryN(i)
            if (abs(punto.z() - altura) >= tolerancia_poligono):
                writer.writerow([c, fid, 'Error en interseccion altura', altura, abs(punto.z() - altura), punto.x(), punto.y()])
                break    

def es_cota(c, c_nom, l_fid, l_ci, l_index, args):    
    # Chequeo de altura maxima, si no la tiene busco interseccion con otra capa
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
            if (p_verti.z() > alt_itera[count]):            
                encontre = True
        if (encontre):
            ritc = interseccion_todas_capas(c_nom, feat_id, l_ci, l_index, args)
            if not ritc:
                resultado.append([c_nom, feat_id['id'], 'Error en Nodo, no maxima altura', '', '', '', ''])
        count = count + 1 
    return resultado 

def es_endorreica(c, le, u, geom_remesa, l_index, l_inter, args):
    u.setDataSource(args.dbschema, c, "geom")
    #capa = QgsVectorLayer(os.path.join("C:", os.path.sep, "Users", "Gonzalo", "Downloads", "IDEUy", "canal_l_chico.shp" ), c, "ogr")
    capa = QgsVectorLayer(u.uri(False), c, "postgres")
    resultado = []
    for e in le:
        f = capa.getFeature(e)
        fid = f['id']
        if not(f.geometry().intersects(geom_remesa)):
            existe_inter = interseccion_todas_capas(c, f, l_inter, l_index, args)
            if not existe_inter:
                resultado.append([c, fid, 'Endorreica', '', '', '', ''])
    return resultado

def interseccion_todas_capas(c, f, lc, l_index, args):
    # Devuelve true si existe interseccion con otras capas, false en caso contrario
    uri2 = QgsDataSourceUri()
    uri2.setConnection(args.server, str(args.port), args.dbname, args.user, args.password)

    geom = f.geometry()
    bbox_geom = geom.boundingBox()
       
    for cap in lc:
        if (cap != c):            
            index_capa = l_index[cap]
            lfea = index_capa.intersects(bbox_geom)            
            uri2.setDataSource(args.dbschema, cap, "geom")
            capa_inter = QgsVectorLayer(uri2.uri(False), cap, 'postgres')
            if (lfea != []):                
                it_feat = capa_inter.getFeatures(lfea)
                for f_inter in it_feat:                    
                    geom_inter = f_inter.geometry()                    
                    if (geom_inter.intersects(geom)):
                        return True        
    return False        

def control_4(capa_4, uri, indices, args, nam_sal, lista_intersectar):    
    uri.setDataSource(args.dbschema, capa_4, "geom")
    capa_eje = QgsVectorLayer(uri.uri(False), capa_4, "postgres")   
    print (capa_eje.isValid()) 
    iterador_features = capa_eje.getFeatures()	
    
    with open(nam_sal, 'w') as csv_file:
        writer = csv.writer(csv_file, lineterminator='\n')  	
        writer.writerow(['Capa_Entrada', 'OBJECTID', 'Descripcion', 'CapaInterseccion', 'OBJECTID', 'Altura', 'DiferenciaAltura', 'CoordenadaX', 'CoordenadaY'])	 
		
		# Itero con todos los features de la capa
        for feature in iterador_features:
            geometria_feature = feature.geometry()
            vertices_feature = geometria_feature.vertices()
            primer_vertice = True
            hay_error = False
            alt_total = 0
            # Se toma el primer vertice como la altura del poligono
            while (vertices_feature.hasNext()):
                punto_vertice = vertices_feature.next()
                alt_actual = punto_vertice.z()
                if (primer_vertice):
                    alt_total = alt_actual                			
                    primer_vertice = False				
                if (abs(alt_total - alt_actual) >= tolerancia_poligono):
                    writer.writerow([capa_4, feature['id'], 'Error en altura poligono', '', '', alt_total, abs(alt_total - alt_actual), punto_vertice.x(), punto_vertice.y()])							                    
                    hay_error = True
            # Verifico que tenga la misma altura que interseccion con drenaje				
            if (not hay_error):                
                for capa in lista_intersectar:			
                    intersectar_capa(capa, geometria_feature, alt_total, writer, capa_4, feature['id'], uri, indices, args)        
												
def intersectar_capa(c, g_f, altura_pol, writer, c_original, fea_original, uri, indexs, args):		
    # Se carga la capa
    uri.setDataSource(args.dbschema, c, "geom")
    capa_cargada = QgsVectorLayer(uri.uri(False), c, "postgres")
    #iterador_features_cargado = capa_cargada.getFeatures()
    index = indexs[c]
    hay_error = False
    lista_resultante = index.intersects(g_f.boundingBox())    
    features_intersect = capa_cargada.getFeatures(lista_resultante)
    for f in features_intersect:                
        if (g_f.intersects(f.geometry())):  
            geom_interseccion = g_f.intersection(f.geometry())
            # Interseccion punto
            if (geom_interseccion.wkbType() == QgsWkbTypes.PointZ):
                if (abs(geom_interseccion.get().z() - altura_pol) >= tolerancia_poligono):
                    writer.writerow([c_original, fea_original, 'Error en interseccion altura', c, f['id'], altura_pol, altura_pol - geom_interseccion.get().z()])						
                            
            # Interseccion linea o multilinea
            elif (geom_interseccion.wkbType() == QgsWkbTypes.LineStringZ or geom_interseccion.wkbType() == QgsWkbTypes.MultiLineStringZ):			
                it_vertices = geom_interseccion.vertices()                 				
                while (it_vertices.hasNext() and (not hay_error)):
                    p_vertice = it_vertices.next()
                    if (abs(p_vertice.z() - altura_pol) >= tolerancia_poligono):
                        writer.writerow([c_original, fea_original, 'Error en interseccion altura', c, f['id'], altura_pol, altura_pol - p_vertice.z()])						
                        hay_error= True
                                
            # Interseccion multipunto			
            elif (geom_interseccion.wkbType() == QgsWkbTypes.MultiPointZ):
                multipolygon = geom_interseccion.get()
                num_geom = multipolygon.numGeometries()
                for i in range(num_geom):
                    punto = multipolygon.geometryN(i)
                    if (abs(punto.z() - altura_pol) >= tolerancia_poligono):
                        writer.writerow([c_original, fea_original, 'Error en interseccion altura', c, f['id'], altura_pol, altura_pol - punto.z()])						
                        break
            else:
                writer.writerow([geom_interseccion.wkbType()])                			

def get_geometry_layer(dir_layer):
    ''' Return the geometry of one feature of a layer. '''    
    vector_layer = QgsVectorLayer(args.rem, 'layer', "ogr")	        
    it_features = vector_layer.getFeatures()
    for feature in it_features:
        f = feature
    return f.geometry()  

def load_config(dir_file_conf):
    ''' Return the json configuration of the control. '''
    with open(dir_file_conf) as json_data:
        file = json.load(json_data)
    return file  

if __name__ == '__main__':        
    args = getArgs()
    params = ' '.join(sys.argv)    

    # VER DE SACAR
    tolerancia = args.t1
    tolerancia_poligono = args.t2

    # start qgis
    qgs = qgsInit(args.dirqgis)

    # uri conection db
    uri = QgsDataSourceUri()
    uri.setConnection(args.server, str(args.port), args.dbname, args.user, args.password)

    # load configuration
    f_config = load_config(args.conf)

    # initialization of variables
    l_ind = {}
    d_feat = {}                    
    l_continuidad = f_config["continuidad"]
    consignment_geometry = get_geometry_layer(args.rem)

    l_ind, d_feat = create_indexes(f_config["indices"], uri, args)

    # iteration of layers to verify control 1, 2, 3
    for name_l_flow in f_config["flujo"]:
        date_time = get_time().strftime("%Y%m%d_%H%M%S_")
        logger.info('{}: {}.'.format(_('Control 1,2,3: Verifing layer'), name_l_flow))        
        uri.setDataSource(args.dbschema, name_l_flow, "geom")
        layer_check = QgsVectorLayer(uri.uri(False), name_l_flow, "postgres")        
        result_name = args.salida + '/' + args.dbschema + '_'  + date_time + 'Control_Vertex_Height_' + name_l_flow +'.csv'
        cotas, endorreicas = control(layer_check, name_l_flow, f_config["endorreicas"], args.rem, uri, l_ind, result_name, args, d_feat, l_continuidad)     
        r_cota = es_cota(layer_check, name_l_flow, cotas, f_config["endorreicas"], l_ind, args)
        r_endo = es_endorreica(name_l_flow, endorreicas, uri, consignment_geometry, l_ind, f_config["endorreicas"], args)
        
        appendRowsToDetailOutputFile(result_name, r_cota)        
        appendRowsToDetailOutputFile(result_name, r_endo)

        control_1(name_l_flow, uri, args, result_name)

    # iteration of layers to verify control 4
    for name_l_constant_height in f_config["altura_area"]:        
        date_time = get_time().strftime("%Y%m%d_%H%M%S_")
        logger.info('{}: {}.'.format(_('Control 4: Verifing layer'), name_l_constant_height))        
        result_name = args.salida + '/' + args.dbschema + '_' + date_time + 'Control_Polygon_Height_' + name_l_constant_height +'.csv'
        control_4(name_l_constant_height, uri, l_ind, args, result_name, f_config["flujo"])

    logger.info('{}.'.format(_('End')))
    # exit qgis
    qgsExit(qgs)         