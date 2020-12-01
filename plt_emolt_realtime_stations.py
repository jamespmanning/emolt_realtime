# -*- coding: utf-8 -*-
"""
Created on Tue Dec  1 12:12:23 2020

@author: Joann
"""
from matplotlib import pyplot as plt
from pandas import read_csv
import basemap_options as bm
region='ne'
#bm.basemap_region(region)# needs "necoast_noaa.dat" file
m=bm.basemap_standard([36,45],[-76,-66],[2])
emolt_QCed_path = 'https://apps-nefsc.fisheries.noaa.gov/drifter/emolt_QCed.csv'
df=read_csv(emolt_QCed_path)
df=df[df.flag==0]# good data only
df=df.drop(df[(df.lat>42.) & (df.lon<-71.)].index)
df=df.drop(df[(df.lat>43.9) & (df.lon<-69.)].index)
df=df.drop(df[(df.lat<39.5) & (df.lon>-70.)].index)
[x,y]=m(df.lon.values,df.lat.values)
plt.plot(x,y,'r.',markersize=4,zorder=1)
#[xt,yt]=m(-73.,37.)
#plt.annotate('locations of realtime bottom temperature reports by fishermen',(xt,yt))
plt.suptitle('13K haul-averaged, real-time, bottom-temperature  ', fontsize=10)
plt.title(' reports by fishermen 2015-2020', fontsize=10)
plt.savefig('plt_emolt_realtime_stations.png')