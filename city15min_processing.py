# -*- coding: utf-8 -*-
"""
Created on Tue Jan  3 22:37:06 2023

@author: gamma
Какие удобства расположены в буфере 0,8 км для жилых домов
По данным OpenStreetMap
Апдейт: репроекция в метры и буфер в метрах, затем репроекция обратно
"""

from shapely.geometry import Point, Polygon, MultiPolygon
#import folium
import json
import openrouteservice
from openrouteservice.isochrones import isochrones
from pyproj import Proj, transform
import pyproj
from shapely.ops import transform

def ors_init():
    client=openrouteservice.Client(key='5b3ce3597851110001cf6248fc5c075192aa43fc8a1cc0e108d50d75')
    return client
def get_amenities(data): #сбор всех данных по удобствам
    result=[]
    for feature in data:
        # print(feature['properties'].keys())
        if feature['properties']['amenity'] is not None:
            result.append(feature)
            # print(feature['properties'])
        elif feature['properties']['shop'] is not None:
            result.append(feature)
    return result
def reproject(geom, geomtype, purpose):
    if geomtype=='Point':
        g1=Point(geom)
    elif geomtype=='Polygon':
        g1=Polygon(geom)
    wgs84 = pyproj.CRS('EPSG:4326')
    utm = pyproj.CRS('EPSG:32643')
    if purpose=='to_utm':
        project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    elif purpose=='to_wgs':
        project = pyproj.Transformer.from_crs(utm, wgs84, always_xy=True).transform
    g2 = transform(project, g1)
    return g2
    
def get_buf(living_house): #буфер жилого дома
    if living_house['geometry']['type']=='MultiPolygon':
        reproj=reproject(living_house['geometry']['coordinates'][0][0], 'Polygon', 'to_utm')
        buffered=reproj.centroid.buffer(800)
        reproj_back=reproject(buffered, 'Polygon', 'to_wgs')
    elif living_house['geometry']['type']=='Polygon':
        reproj=reproject(living_house['geometry']['coordinates'][0], 'Polygon', 'to_utm')
        buffered=reproj.centroid.buffer(800)
        reproj_back=reproject(buffered, 'Polygon', 'to_wgs')
    elif living_house['geometry']['type']=='Point':
        reproj=reproject(living_house['geometry']['coordinates'], 'Point', 'to_utm')
        buffered=reproj.centroid.buffer(800)
        reproj_back=reproject(buffered, 'Polygon' 'to_wgs')
    return reproj_back

def get_buf_ors(living_house): #только если геодезические координаты, квота 500 запросов
    if living_house['geometry']['type']=='MultiPolygon':
        centroid=Polygon(living_house['geometry']['coordinates'][0][0]).centroid
    elif living_house['geometry']['type']=='Polygon':
        centroid=Polygon(living_house['geometry']['coordinates'][0]).centroid
    elif living_house['geometry']['type']=='Point':
        centroid=Point(living_house['geometry']['coordinates']).centroid
    ors=ors_init()
    iso=ors.isochrones(locations=[centroid.coords[0]], profile='foot-walking', range_type='time', range=[900])
    iso_poly=Polygon(iso['features'][0]['geometry']['coordinates'][0])
    return iso_poly

def check_containing(living_house_buf, amenity):
    living_house_buff=reproject(living_house_buf, 'Polygon', 'to_utm')
    if amenity['geometry']['type']=='Point':
        amenity_buff=reproject(amenity['geometry']['coordinates'], amenity['geometry']['type'], 'to_utm')
        if living_house_buff.contains(amenity_buff.buffer(1)) or living_house_buff.intersects(amenity_buff.buffer(1)):
            return True
    elif amenity['geometry']['type']=='Polygon':
        amenity_buff=reproject(amenity['geometry']['coordinates'][0], amenity['geometry']['type'], 'to_utm')
        if living_house_buff.contains(amenity_buff) or living_house_buf.intersects(amenity_buff):
            return True

def amenities_in_buf(living_house, amenities): #находит все удобства, что попадают в буфер 1,5 км
    amenities_id_list=[]
    living_house_buf=living_house['properties']['buffer']
    for amenity in amenities:
        if check_containing(living_house_buf, amenity):
            amenities_id_list.append(amenity['properties']['id'])
    return amenities_id_list

def get_living_houses(data, amenities): #сбор всех данных по домам и параллельное добавление к ним геоданных буфера: координаты буфера и id всех удобств
    result=[]
    for feature in data:
        if 'building' in feature['properties'].keys():
            tag=feature['properties']['building']
            if tag=='residential' or tag=='apartments' or tag=='detached' or tag=='house' or tag=='dormitory' or tag=='hotel':
                buf=get_buf(feature)
                #feature['properties']['buffer_shapely']=buf_ors
                feature['properties']['buffer']=buf #!!!
                feature['properties']['buffer_coords']=list(buf.exterior.coords)
                feature['properties']['amenities_in_buf']=amenities_in_buf(feature, amenities) #!!!
                result.append(feature)
                print(feature['properties']['id'])
    print('end')
    return result

def weight_reduction(living_houses): #лучше не юзать
    result=[]
    for feature in living_houses:
        props=list(feature['properties'])
        for prop in props:
            if feature['properties'][prop] is None:
                del feature['properties'][prop]
        if 'buffer' in props:
            del feature['properties']['buffer']
        result.append(feature)
    return result

def mapbox_aggregate(living_houses_lite, amenities):
    res={'type': 'FeatureCollection', 'features': []}
    for fet in living_houses_lite:
        amenities_in_buf=[x.split('/')[1] for x in fet['properties']['amenities_in_buf']]
        new_fet={'type': 'Feature', 'id': fet['properties']['id'].split('/')[1], 'geometry': fet['geometry'], 'properties': {'amenities_in_buf': amenities_in_buf, 'id': fet['properties']['id'].split('/')[1]}}
        res['features'].append(new_fet)
    for fet in amenities:
        geom=fet['geometry']
        if geom['type']=='Point':
            geom_mb=geom
        elif geom['type']=='Polygon':
            geom_mb={'type': 'Point', 'coordinates': list(Polygon(geom['coordinates'][0]).centroid.coords)[0]}
        new_fet={'type': 'Feature', 'id': fet['properties']['id'].split('/')[1], 'geometry': geom_mb, 'properties': {'amenity_type': fet['properties']['amenity'], 'shop_type': fet['properties']['shop'], 'bus_station': fet['properties']['public_transport'], 'amenities_in_buf': 'null', 'id': fet['properties']['id'].split('/')[1]}}
        res['features'].append(new_fet)
    return res

data=json.load(open("sovetsk_4326.geojson", mode='r', encoding='utf-8'))['features']

amenities=get_amenities(data)
living_houses=get_living_houses(data, amenities)
res=mapbox_aggregate(living_houses, amenities)
with open('sovetsk.geojson', 'w') as f:
    f.write(json.dumps(res))