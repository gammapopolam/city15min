# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 12:28:15 2022

@author: Ivan Gamma

Какие удобства расположены в буфере 1,5 км для жилых домов
По данным OpenStreetMap


Алярма! Если один раз запустишь полный скрипт сбора изохрон, 
то в следующий раз только с другим API-ключом!

Или используй одиночные запросы для отладки (хотя на начало 07.12.22 все ок)
"""

from shapely.geometry import Point, Polygon, MultiPolygon
import folium
import json
import openrouteservice
from openrouteservice.isochrones import isochrones
from pyproj import Proj, transform
import time

def ors_init():
    client=openrouteservice.Client(key='5b3ce3597851110001cf62486680dafdddd74f879ee1c6a72b5b1286')
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

def get_buf(living_house): #буфер жилого дома
    if living_house['geometry']['type']=='MultiPolygon':
        centroid=Polygon(living_house['geometry']['coordinates'][0][0]).centroid
    elif living_house['geometry']['type']=='Polygon':
        centroid=Polygon(living_house['geometry']['coordinates'][0]).centroid
    elif living_house['geometry']['type']=='Point':
        centroid=Point(living_house['geometry']['coordinates']).centroid
    return centroid.buffer(500)

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

def amenities_in_buf(living_house, amenities): #находит все удобства, что попадают в буфер 1,5 км
    amenities_id_list=[]
    living_house_buf=living_house['properties']['buffer']
    for amenity in amenities:
        if amenity['geometry']['type']=='Point':
            if living_house_buf.contains(Point(amenity['geometry']['coordinates']).buffer(1)) or living_house_buf.intersects(Point(amenity['geometry']['coordinates']).buffer(1)):
                amenities_id_list.append(amenity['properties']['id'])
        elif amenity['geometry']['type']=='Polygon':
            if living_house_buf.contains(Polygon(amenity['geometry']['coordinates'][0])) or living_house_buf.intersects(Polygon(amenity['geometry']['coordinates'][0])):
                amenities_id_list.append(amenity['properties']['id'])
    return amenities_id_list

def get_living_houses(data, amenities): #сбор всех данных по удобствам и параллельное добавление геоданных буфера: координаты буфера и id всех удобств
    result=[]
    num_of_iso=2
    for feature in data:
        if 'building' in feature['properties'].keys():
            tag=feature['properties']['building']
            if tag=='residential' or tag=='apartments' or tag=='detached' or tag=='house' or tag=='dormitory' or tag=='hotel':
                feature['properties']['buffer']=list(get_buf_ors(feature).exterior.coords) #!!!
                feature['properties']['amenities_in_buf']=amenities_in_buf(feature, amenities) #!!!
                result.append(feature)
                num_of_iso+=1
        if num_of_iso%20==0:
            print('sleeping')
            time.sleep(61)
    return result


data=json.load(open("akademicheskiy_4326.geojson", mode='r', encoding='utf-8'))['features']

amenities=get_amenities(data)
living_houses=get_living_houses(data, amenities)
# iso_poly=get_buf_ors(living_houses[0])
# print(list(iso_poly.exterior.coords))












