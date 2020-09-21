#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 09:10:47 2018
@author: Lei Zhao with help from JiM and Vitalii

Modifications by Lei Zhao Feb 27 2019
-updates the method of calculate the layer_index in function of get doppio
-updated the method of calculate the min,second small and third small distance and index

Modifications by lei Zhao Mar 20, 2019
-updated the way to get temperature quicker

Modifications by JiM Mar 21, 2019
-just added some more documentation and spelling changes
"""

import netCDF4
import datetime
import zlconversions as zl  # this is a set of Lei Zhao's functions that must be in same folder 
import numpy as np

def get_doppio(lat=0,lon=0,depth='bottom',time='2018-11-12 12:00:00',fortype='temperature'):
    """
    notice:
        the format of time is like "%Y-%m-%d %H:%M:%S" this time is utctime  or it can also be datetime
        the depth is under the bottom depth
    the module only output the temperature of point location
    if fortype ='temperature',only return temperature, else return temperature and depth
    """
    if depth==99999:
       depth='bottom'
    if not doppio_coordinate(lat,lon):
        print('the lat and lon out of range in doppio')
        return np.nan,np.nan
    if type(time)==str:
        date_time=datetime.datetime.strptime(time,'%Y-%m-%d %H:%M:%S') # transform time format
    elif type(time)==datetime.datetime:
        date_time=time
    else:
        print('check the type of input time in get_doppio')
    for m in range(0,7):
        try:
            url_time=(date_time-datetime.timedelta(days=m)).strftime('%Y-%m-%d')#
            url=zl.get_doppio_url(url_time)
            #get the data 
            nc=netCDF4.Dataset(url)
            lons=nc.variables['lon_rho'][:]
            lats=nc.variables['lat_rho'][:]
            doppio_time=nc.variables['time']
            doppio_rho=nc.variables['s_rho']
            doppio_temp=nc.variables['temp']
            doppio_h=nc.variables['h']
        except:
            continue
        min_diff_time=abs(datetime.datetime(2017,11,1,0,0,0)+datetime.timedelta(hours=int(doppio_time[0]))-date_time)
        min_diff_index=0
        for i in range(1,len(doppio_time)):
            diff_time=abs(datetime.datetime(2017,11,1,0,0,0)+datetime.timedelta(hours=int(doppio_time[i]))-date_time)
            if diff_time<min_diff_time:
                min_diff_time=diff_time
                min_diff_index=i
        #calculate the min,second small and third small distance and index
        target_distance=zl.dist(lat1=lats[0][0],lon1=lons[0][0],lat2=lats[0][1],lon2=lons[0][1])
        index_1,index_2=zl.find_nd(target=target_distance,lat=lat,lon=lon,lats=lats,lons=lons)

        #calculate the optimal layer index added this section Feb 2020
        doppio_depth=nc['h'][index_1][index_2]
        if depth > doppio_depth:# case of bottom
            S_coordinate=1
        else:
            S_coordinate=float(depth)/float(doppio_depth)
        if 0<=S_coordinate<1:
            layer_index=39-int(S_coordinate/0.025)#doppio_temp=temp[itime,39-int(S_coordinate/0.025),index_1,index_2]# because there are 0.025 between each later
        elif S_coordinate==1:
            layer_index=0#doppio_temp=temp[itime][0][index_1][index_2]
        else:
            layer_index=0#doppio_temp=temp[itime][0][index_1][index_2]
        #return doppio_temp
        #layer_index=0  #specify the initial layer index
        '''if depth!='bottom':
            h_distance=depth+doppio_rho[0]*doppio_h[index_1,index_2]  #specify the initial distanc of high
            for i in range(len(doppio_rho)):
                if abs(depth+doppio_rho[0]*doppio_h[index_1,index_2])<=h_distance:
                    h_distance=depth+doppio_rho[i]*doppio_h[index_1,index_2]
                    layer_index=i
                if depth>doppio_h[index_1,index_2]:
                    print ("the depth is out of the depth of bottom:"+str(doppio_h[index_1,index_2]))
        '''
        if index_1==0:
            index_1=1
        if index_1==len(lats)-1:
            index_1=len(lats)-2
        if index_2==0:
            index_2=1
        if index_2==len(lats[0])-1:
            index_2=len(lats[0])-2
        while True:
            point=[[lats[index_1][index_2],lons[index_1][index_2],doppio_temp[min_diff_index,layer_index,index_1,index_2]],\
            [lats[index_1-1][index_2],lons[index_1-1][index_2],doppio_temp[min_diff_index,layer_index,(index_1-1),index_2]],\
            [lats[index_1+1][index_2],lons[index_1+1][index_2],doppio_temp[min_diff_index,layer_index,(index_1+1),index_2]],\
            [lats[index_1][index_2-1],lons[index_1][index_2-1],doppio_temp[min_diff_index,layer_index,index_1,(index_2-1)]],\
            [lats[index_1][index_2+1],lons[index_1][index_2+1],doppio_temp[min_diff_index,layer_index,index_1,(index_2+1)]]]
            break
        point_temp=fitting(point,lat,lon)
        if np.isnan(point_temp):
            continue
        if min_diff_time<datetime.timedelta(hours=1):
            break
    if fortype=='temperature':
        return point_temp
    else:
        return point_temp,doppio_h[index_1,index_2]

def fitting(point,lat,lon):
#represent the value of matrix
    ISum = 0.0
    X1Sum = 0.0
    X2Sum = 0.0
    X1_2Sum = 0.0
    X1X2Sum = 0.0
    X2_2Sum = 0.0
    YSum = 0.0
    X1YSum = 0.0
    X2YSum = 0.0

    for i in range(0,len(point)):
        
        x1i=point[i][0]
        x2i=point[i][1]
        yi=point[i][2]

        ISum = ISum+1
        X1Sum = X1Sum+x1i
        X2Sum = X2Sum+x2i
        X1_2Sum = X1_2Sum+x1i**2
        X1X2Sum = X1X2Sum+x1i*x2i
        X2_2Sum = X2_2Sum+x2i**2
        YSum = YSum+yi
        X1YSum = X1YSum+x1i*yi
        X2YSum = X2YSum+x2i*yi

#  matrix operations
# _mat1 is the mat1 inverse matrix
    m1=[[ISum,X1Sum,X2Sum],[X1Sum,X1_2Sum,X1X2Sum],[X2Sum,X1X2Sum,X2_2Sum]]
    mat1 = np.matrix(m1)
    m2=[[YSum],[X1YSum],[X2YSum]]
    mat2 = np.matrix(m2)
    _mat1 =mat1.getI()
    mat3 = _mat1*mat2

# use list to get the matrix data
    m3=mat3.tolist()
    a0 = m3[0][0]
    a1 = m3[1][0]
    a2 = m3[2][0]
    y = a0+a1*lat+a2*lon

    return y

def doppio_coordinate(lat,lon):
    f1=-0.8777722604596849*lat-lon-23.507489034447012>=0
    f2=-1.072648270137022*lat-40.60872567829448-lon<=0
    f3=1.752828434063416*lat-131.70051451008493-lon>=0
    f4=1.6986954871237598*lat-lon-144.67649951783605<=0
    if f1 and f2 and f3 and f4:
        return True
    else:
        return False

