# -*- coding: utf-8 -*-
"""
Created on Wed Sep 15 10:39:45 2021

@author: Ivan Gamma
"""

import psycopg2
from pyproj import Proj, transform
from shapely.geometry import Point, shape, Polygon
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
def get_epsg_code(cordlist):
    return f'326{(float(cordlist[0])+186)//6}'[:-2]
def get_city_ids():
    conn=psycopg2.connect(dbname='mostransport', user='readonly', 
                              password='Alex2', host='84.201.146.240')
    cursor=conn.cursor()
    cursor.execute('select * from cities')
    cities=cursor.fetchall()
    cities_dict=dict()
    for city in cities:
        cities_dict.update({city[1]: city[0]})
    # print(cities_dict)
    cursor.close()
    conn.close()
    return cities_dict
def get_buf_of_point(cordlist):
    point=get_point(cordlist)
    buf=point.buffer(1250)
    # print(buf)
    return buf
def get_point(cordlist):
    ox, oy=cordlist[0],cordlist[1]
    inProj=Proj(init='epsg:4326')
    outProj=Proj(init=f'epsg:{get_epsg_code(cordlist)}')
    nx, ny=transform(inProj, outProj, ox, oy)
    point=Point(nx, ny)
    return point
def get_num_of_houses(city_id):
    conn=psycopg2.connect(dbname='mostransport', user='readonly', 
                      password='Alex2', host='84.201.146.240')
    cursor=conn.cursor()
    cursor.execute(f'select * from houses where city_id = {city_id}')
    len_houses=len(cursor.fetchall())
    cursor.close()
    conn.close()
    return len_houses

def get_houses(f, s, city_id): #f, s - начало, конец
    conn=psycopg2.connect(dbname='mostransport', user='readonly', 
                      password='Alex2', host='84.201.146.240')
    cursor=conn.cursor()
    cursor.execute(f'select * from houses where city_id = {city_id}')
    houses=[]
    for house in cursor:
        if f<s:
            # print(f, house[15]['coordinates'])
            f+=1
            buf=get_buf_of_point(house[15]['coordinates'])
            source=get_point(house[15]['coordinates'])
            houses.append({'id': f, 'source':source.coords[0], 'iso':list(buf.exterior.coords)})
            # print(f)
    return houses
def get_amenity(city):
    nominatim = Nominatim()
    areaId = nominatim.query(city).areaId()
    # print(areaId)
    overpass=Overpass()
    building=overpassQueryBuilder(area=areaId, 
                                     elementType=['way', 'relation'],
                                     selector="amenity", out='body', 
                                     includeGeometry=True)
    result=overpass.query(building)
    # print(result.elements())
    amenity=[]
    for i in range(len(result.elements())):
        if type(result.elements()[i].geometry()['coordinates'][0][0][0]) == float:
        # if result.elements()[i].tags()['building'] in tags:
            cordlist=result.elements()[i].geometry()['coordinates'][0][0]
            projected=get_point(cordlist)
            amenity.append(([projected.x, projected.y], result.elements()[i].tags()['amenity']))
    return amenity
def get_amenity_in_buf(buf, amenity):
    buf_shape=Polygon(buf)
    # print(buf_shape)
    for i in range(len(amenity)):
        amenity_point=Point(amenity[i][0][0], amenity[i][0][0])
        # print(amenity_point)
        if amenity_point.within(buf_shape):
            # print(amenity[i])
            print('yeah')
            return True
city='Южно-Сахалинск'
# print("____Requesting houses (mostransport db)")
city_ids=get_city_ids()
city_id=city_ids[city]
len_houses=get_num_of_houses(city_id)
f=0
s=10
result=get_houses(f, s, city_id)
amenity=get_amenity(city)
get_amenity_in_buf(result[0]['iso'], amenity)