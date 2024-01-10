#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan  7 15:00:47 2024
Gets time series of realtime bottom temps given site code
Written in Jan 2024 to compare Jamien H's realtime with non-realtime minilog bottom temps
which include surface temp
@author: JiM
"""
import pandas as pd
import numpy as np
import matplotlib
from datetime import datetime as dt
from datetime import timedelta as td
from dateutil.relativedelta import relativedelta
from matplotlib import pyplot as plt
from conversions import f2c,c2f,m2fth,fth2m

#HARDCODES
site ='OD08'
site ='AG01'
nrt_dat_file='OD08m60321308.dat' # recent nrt data not yet in NOAA erddap
nrt_dat_file='AG01m60374401.dat'
#nrt_dat_file='AG01m48734301.dat'
st='Fishing'#'Profiling%20Up' # typically 'Fishing' #segment_type
#st='Profiling%20Up'
startt=(dt.now()-relativedelta(months=3)).strftime('%Y-%m-%dT%H:%M:%SZ')

def getsite_latlon(site):
    df=pd.read_csv('/home/user/emolt_non_realtime/emolt/emolt_site.csv')
    df1=df[df['SITE']==site]
    return df1['LAT_DDMM'].values[0],df1['LON_DDMM'].values[0],fth2m(df1['BTM_DEPTH'].values[0])

lat,lon,dep=getsite_latlon(site) # reads emolt_site.csv file to get nominal lat/lons for nrt emolt sites.
miles=.5
search=miles/60. #fraction of a degree where, for example, 1/2 mile is 0.0083
gbox=[lon-search,lon+search,lat-search,lat+search]# 1/2 mile box around site
gb= list(map(str, gbox))# returns a list of strings
url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E='+startt+'&latitude%3E='+gb[2]+'&latitude%3C='+gb[3]+'&longitude%3E='+gb[0]+'&longitude%3C='+gb[1]+''
#url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?segment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E=2023-12-01T13%3A53%3A21Z&latitude%3E=41.5&latitude%3C=42.3&longitude%3E=-70.75&longitude%3C=-70.'
df=pd.read_csv(url) # gets rt data after specific time and within a certain geographic box
if st=='Profiling%20Up': # not typical case of surface temp
    df['new'] = df.groupby('tow_id')['depth (m)'].transform('min')
    df=df[df['depth (m)'] == df['new']]
    marker='*'
else:
    #df['new'] = df.groupby('tow_id')['depth (m)'].transform('max')
    marker='-'
    
df['datet']=pd.to_datetime(df['time (UTC)'])
df.sort_values('datet', inplace=True)

# get minilog data from recent data
cols=['site','sn','ps','date','yd','temp','salt','depth']
dfm=pd.read_csv('/home/user/emolt_non_realtime/emolt/output/'+nrt_dat_file,names=cols)
dfm['datet']=pd.to_datetime(dfm['date'],utc=True)+td(hours=5)
dfm=dfm[dfm['datet']>=min(df['datet'])]# start minilog at start of moana
dfm=dfm[dfm['datet']<=max(df['datet'])]# end minilog at end of moana

# quantify differences by interpolating rt on to nrt times
df=df.resample('60min',on='datet').mean()
dfm=dfm.resample('60min',on='datet').mean()

df=df[df.index>=min(dfm.index)]# start  moana at start of minilog
df=df[df.index<=max(dfm.index)]# end  moana at end of minilog

fig=plt.figure()
#matplotlib.rcParams.update({'font.size': 18})
matplotlib.rc('xtick', labelsize=10)
matplotlib.rc('ytick', labelsize=10)
ax=fig.add_subplot(111)
#ax.plot(df['datet'].values,c2f(df['temperature (degree_C)'].values)[0],label='Moana')
#ax.plot(dfm['datet'].values,dfm['temp'].values,label='Minilog')
#ax.plot(df.index,c2f(df['temperature (degree_C)'].values)[0],'*',label='Moana '+"%0.2f" % np.nanmean(df['temperature (degree_C)'])+' degC')
ax.plot(df.index,c2f(df['temperature (degree_C)'].values)[0],marker,label='mean Moana '+"%0.2f" % np.nanmean(df['temperature (degree_C)'])+' degC in '+"%0.1f" % np.nanmean(df['depth (m)'])+' meters')
t=f2c(np.nanmean(dfm['temp'].values))[0]
d=fth2m(np.nanmean(dfm['depth'].values))
ax.plot(dfm.index,dfm['temp'].values,label='mean Minilog '+"%0.2f" % t +' degC nominally '+"%0.1f" % d +' meters',zorder=0)
ax.legend(loc=3,fontsize=10)# lower left
plt.ylabel('Temperature (degF)',fontsize=18)
ax2=ax.twinx()
ax2.set_ylabel('celsius',fontsize=14)
degFrange=ax.get_ylim()  
ax2.set_ylim((degFrange[0]-32)/1.8,(degFrange[1]-32)/1.8)  
ax2.set_xlabel('time',fontsize=18)
#plt.title(site+' in '+'%0.1f' % np.mean(df['depth (m)'])+' meters (resampled to 60 minutes)')
plt.title('Within '+str(miles)+' miles of '+site+' resampled to 60 minutes')
plt.text(max(df.index),np.nanmax(df['temperature (degree_C)'].values),\
         'STDDEV= %0.2f' % np.nanstd(df['temperature (degree_C)'].values-f2c(dfm['temp'])[0].values)+' degC',ha='right',va='top')
fig.autofmt_xdate()
plt.show()
plt.savefig('Moana_vs_Minilog_'+site+'_'+st+'.png')