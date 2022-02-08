# -*- coding: utf-8 -*-
"""
Created on Wed Sep 15 10:39:45 2021

@author: Ivan Gamma
"""
import folium 
import psycopg2
import numpy as np
from warnings import filterwarnings
from pyproj import Proj, transform
from shapely.geometry import Point, shape, Polygon, MultiPolygon
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
def get_epsg_code(cordlist): #utm !!!
    # print(cordlist[0])5]
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
    buf=point.buffer(500)
    # print(buf)
    return buf
def get_point(cordlist):
    ox, oy=cordlist[0],cordlist[1]
    inProj=Proj(init='epsg:4326')
    outProj=Proj(init=f'epsg:{get_epsg_code(cordlist)}')
    nx, ny=transform(inProj, outProj, ox, oy)
    point=Point(nx, ny)
    return point
def get_point_in_4326(cordlist, in4326):
    ox, oy=cordlist[0],cordlist[1]
    outProj=Proj(init='epsg:4326')
    inProj=Proj(init=f'epsg:{get_epsg_code(in4326)}')
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

def get_houses(f, s, city_id, city): #f, s - начало, конец
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
            houses.append({'id': f, 'city_id': city_id, 'city':city, 'source':source.coords[0], 'iso':list(buf.exterior.coords)})
            # print(f)
    in4326=[house[15]['coordinates'][0], house[15]['coordinates'][1]]
    return houses, in4326
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
    amenity_in4326=[]
    for i in range(len(result.elements())):
        # print(result.elements()[i].geometry()['coordinates'])
        if type(result.elements()[i].geometry()['coordinates'][0][0])!=float and len(result.elements()[i].geometry()['coordinates'][0][0])>2:
            amenity_c=Polygon(np.array(result.elements()[i].geometry()['coordinates'][0][0])).centroid.coords[0]
        elif type(result.elements()[i].geometry()['coordinates'][0][0])==float:
            amenity_c=Polygon(np.array(result.elements()[i].geometry()['coordinates'])).centroid.coords[0]
        else:
            amenity_c=Polygon(np.array(result.elements()[i].geometry()['coordinates'][0])).centroid.coords[0]
        amenity_in4326.append({'id': i, 'centroid': [amenity_c[1], amenity_c[0]], 'type': result.elements()[i].tags()['amenity'], 'city': city})
        # print(amenity_c)
        if type(result.elements()[i].geometry()['coordinates'][0][0]) == list:
        # if result.elements()[i].tags()['building'] in tags:
            cordlist=result.elements()[i].geometry()['coordinates'][0][0]
            if type(cordlist[0])==list:
                projected=get_point(cordlist[0])
            else:
                projected=get_point(cordlist)
            amenity.append(([projected.x, projected.y], result.elements()[i].tags()['amenity']))
            
        else:
            cordlist=result.elements()[i].geometry()['coordinates'][0]
            if type(cordlist[0])==list:
                projected=get_point(cordlist[0])
            else:
                projected=get_point(cordlist)
            amenity.append(([projected.x, projected.y], result.elements()[i].tags()['amenity']))
            
    return amenity, amenity_in4326
def get_amenity_in_buf(house, amenity, in4326):
    # print(house['iso'])
    buf_shape=Polygon(house['iso'])
    out_data=[]
    amenity_list=[]
    house_elem=get_point_in_4326(house['source'], in4326)
    # print('buf_shape: ',buf_shape)
    for i in range(len(amenity)):
        amenity_point=Point(amenity[i][0][0], amenity[i][0][1])
        # print('amenity_point:   ',amenity_point)
        # print('amenity_point_buf:   ',amenity_point.buffer(1))
        if buf_shape.contains(amenity_point.buffer(1)):
            # print(amenity[i])
            # print('yeah')
            # return True
            amenity_elem=get_point_in_4326(amenity[i][0], in4326)
            amenity_list.append(i)
    out_data.append({'id': house['id'], 'coord': [house_elem.y, house_elem.x], 'containing_amenity': amenity_list})
    return out_data
def map_html(base, amenity_in4326):
    for i in range(len(base)):
        map_f=folium.Map(location=base[i]['coord'])
        folium.Marker(location=base[i]['coord'], popup=str(base[i]['id'])).add_to(map_f)
        for j in range(len(base[i]['containing_amenity'])):
            for k in range(len(amenity_in4326)):
                if base[i]['containing_amenity'][j]==amenity_in4326[k]['id']:
                    folium.Marker(location=amenity_in4326[k]['centroid'], popup=str(f'type: {amenity_in4326[k]["type"]}')).add_to(map_f)
        map_f.save(f"C:\Git\city15min\{base[i]['id']}.html")
conn=psycopg2.connect(user='postgres', 
                              password='2195', host='localhost', port='5432', database='sample')
cursor=conn.cursor()
filterwarnings("ignore")
city='Псков'
# print("____Requesting houses (mostransport db)")
city_ids=get_city_ids()
city_id=city_ids[city]
len_houses=get_num_of_houses(city_id)
f=0
s=10
houses, in4326=get_houses(f, s, city_id, city)
amenity, amenity_in4326=get_amenity(city)
result=[]
for i in range(len(houses)):
    result.append(get_amenity_in_buf(houses[i], amenity, in4326)[0])
    # map_html(result, amenity_in4326)
for i in range(len(result)):
        cursor.execute("INSERT INTO houses (id, city_id, source, amenity_id, city_name) VALUES (%s, %s, %s, %s, %s)", (result[i]['id'], city_id, f'POINT({str(result[i]["coord"])[1:-1]})', result[i]['containing_amenity'], city))
        # cursor.execute(f"INSERT INTO houses (id, source) VALUES ({result[i]['id']}, POINT({str(result[i]['coord'])[1:-1]})")
# cursor.execute(f'INSERT INTO amenity (id, city_id, city_name, type, centroid) VALUES ({amenity_in4326[0]["id"]}, {city_id}, {city}, {amenity_in4326[0]["type"]}, {str(amenity_in4326[0]["centroid"])[1:-1]})')
# for i in range(len(amenity_in4326)):
    # cursor.execute(f"INSERT INTO amenity (id, city_id, city_name, type, centroid) VALUES ({amenity_in4326[i]['id']}, {city_id}, '{city}', '{amenity_in4326[i]['type']}', 'POINT({str(amenity_in4326[i]['centroid'])[1:-1]})')")
# cursor.execute('INSERT')
conn.commit()
cursor.close()
conn.close()