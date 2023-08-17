#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 23 18:01:51 2023

@author: user
"""
import pandas as pd
import ftplib
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
            
# Now read in the eMOLT realtime data and output x,y,temp
df=pd.read_csv('https://emolt.org/emoltdata/emolt_QCed.csv')
df=df[df['flag']==0].reset_index()
#df=df[0:10]
x,y=[],[]
for k in range(len(df)):
    xx,yy=p(df.lon[k],df.lat[k])
    x.append(xx);y.append(yy)
df['x']=x;df['y']=y
dfo=pd.DataFrame([df['datet'],df['x'],df['y'],df['lon'],df['lat'],df['depth'],df['mean_temp']]).T
dfo['datet']= pd.to_datetime(dfo['datet'])
dfo.sort_values('datet', inplace=True)
dfo.to_csv('/home/user/emolt/emolt_with_xy.csv')
eMOLT_cloud(['/home/user/emolt/emolt_with_xy.csv'])
