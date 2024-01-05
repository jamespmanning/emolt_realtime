#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 23 18:01:51 2023

@author: JiM
modified in 3 Jan 2024 to include the ERDDAP-served hauls
"""
import pandas as pd
import ftplib
import numpy as np
from pyproj import Proj
p = Proj(init='nad83:1802')

# TEST CODE AS FOLLOWS:
#where lon=-70.16666;lat=42.8333333 results in close to 900000 , 0 this is the "origin" with "false easting" of 900 Km
#lon=-70.16666;lat=42.8333333
#x,y=p(lon,lat)
#print(x,y)

def eMOLT_cloud(ldata):# send file to SD machine
        # function to upload a list of files to SD machine
        for filename in ldata:
            # print u
            session = ftplib.FTP('66.114.154.52', 'huanxin', '123321')
            file = open(filename, 'rb')
            #session.cwd("/BDC")
            #session.cmd("/tracks")
            # session.retrlines('LIST')               # file to send
            session.storbinary("STOR " + filename.split('/')[-1], fp=file)  # send the file
            # session.close()
            session.quit()  # close file and FTP
            #time.sleep(1)
            file.close()
            print(filename.split('/')[-1], 'uploaded in SD endpoint')
            
# Now read in the old eMOLT QCed realtime data and output x,y,temp
dfeq=pd.read_csv('https://emolt.org/emoltdata/emolt_QCed.csv')
dfeq=dfeq[dfeq['flag']==0].reset_index()

# Now read in the new emolt ERDDAP
url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature%2Csensor_type'
dfed=pd.read_csv(url) 
dfed=dfed[dfed['segment_type']=='Fishing'].reset_index()
# for each tow_id, calculate mean_temp
dfed['mean'] = dfed.groupby('tow_id')['temperature (degree_C)'].transform('mean')
#Make a dataframe similar to dfeq
dfed=dfed.drop_duplicates(subset='tow_id')
dfedr=pd.DataFrame([dfed['time (UTC)'],dfed['latitude (degrees_north)'],dfed['longitude (degrees_east)'],dfed['depth (m)'],dfed['mean']]).T
dfedr.rename(columns={'time (UTC)':'datet','latitude (degrees_north)':'lat','longitude (degrees_east)':'lon','depth (m)':'depth','mean':'mean_temp'},inplace=True)
#dfedr=dfedr.style.format({'mean_temp': '{:.2f}'})
#dfedr['mean_temp']=dfedr['mean_temp'].values.round(2)
dfedr['mean_temp']=dfedr['mean_temp'].map(lambda x: '{0:.2f}'.format(x)) 
dfeqr = dfeq[dfeq.columns & dfedr.columns] # gets rid of the extra columns not needed in dfeq
df = pd.concat([dfeqr,dfedr],axis=0).reset_index()

x,y=[],[]
for k in range(len(df)):
    xx,yy=p(df.lon.values[k],df.lat.values[k])
    x.append(xx);y.append(yy)
df['x']=x;df['y']=y
dfo=pd.DataFrame([df['datet'],df['x'],df['y'],df['lon'],df['lat'],df['depth'],df['mean_temp']]).T
dfo['datet']= pd.to_datetime(dfo['datet'],utc=True)
dfo.sort_values('datet', inplace=True)
dfo['datet'] = dfo['datet'].astype('datetime64[ns]')
dfo.to_csv('/home/user/emolt/emolt_with_xy.csv',date_format='%Y-%m-%dT%H:%M:%SZ',index=False)#,float_format='{:.2f}')
eMOLT_cloud(['/home/user/emolt/emolt_with_xy.csv'])
