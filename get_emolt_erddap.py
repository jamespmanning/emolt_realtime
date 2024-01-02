#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routine to extract temperature data from the new eMOLT  ERDDAP server 
according to "area".
First developed without regard to flags & sensor type until I learn what the flags mean
Created on Sun Dec 31 06:11:32 2023

@author: user
"""


import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import netCDF4
from conversions import c2f,m2fth
import ftplib

###HARDCODES####
area='NE'
st='Profiling%20Up' #segment_type
startt=(dt.datetime.now()-dt.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')#'2023-12-01T13:53:21Z'
surf_or_bot='bottom'

def map_emolt_erddap(df,add_border=0.2,resolution='i',surf_or_bot='surface',startt='2023-12-01T13:53:21Z'):
    # add_border is in degrees lat/lon to allow for extra (in order to possibly see land)
    # resolution is c, i, or f for crude, intermediate, or full (i by default)
    # surf_or_bot is "surface" or "bottom" color coded sta by temp
    import os,imageio
    import glob
    import conda # added this 12/28/2023
    conda_file_dir = conda.__file__
    conda_dir = conda_file_dir.split('lib')[0]
    proj_lib = os.path.join(os.path.join(conda_dir, 'share'), 'proj')
    from mpl_toolkits.basemap import Basemap
    from scipy.interpolate import griddata as gd
    import warnings
    warnings.filterwarnings("ignore") # JiM added Sep 2020 to supopress the "matplotlibDeprecationWarning"
    a=add_border # add to boundary
    if surf_or_bot=='surface':
        df['new'] = df.groupby('tow_id')['depth (m)'].transform('min')
    else:
        df['new'] = df.groupby('tow_id')['depth (m)'].transform('max')
    df=df[df['depth (m)'] == df['new']]# now we have just one layer
    df=add_old_emolt_csv(df,startt)# add old emolt_QCed data
    lat=df['latitude (degrees_north)'].values
    lon=df['longitude (degrees_east)'].values
    temp=c2f(df['temperature (degree_C)'].values)
    gbox=[min(lon)-a,max(lon)+a,min(lat)-a,max(lat)+a] # inside_CCBAY # uses the getgbox function to define lat/lon boundary
    latsize=[gbox[2],gbox[3]]
    lonsize=[gbox[0],gbox[1]]
    tick_int=gbox[3]-gbox[2] # allow for 3-4 tick axis label intervals
    if tick_int>=1:
        tick_int=int(tick_int/2.)   # make the tick_interval integer increments
    elif (tick_int>.5) & (tick_int<1):
        tick_int=.5
    else:
        tick_int=.2
        
    fig,ax=plt.subplots()
    m = Basemap(projection='merc',llcrnrlat=min(latsize),urcrnrlat=max(latsize),\
                llcrnrlon=min(lonsize),urcrnrlon=max(lonsize),resolution=resolution)
    m.fillcontinents(color='gray')
    parallels = np.arange(0.,90,tick_int)
    m.drawparallels(parallels,labels=[1,0,0,0],fontsize=12)
    # draw meridians
    meridians = np.arange(180.,360.,tick_int)
    m.drawmeridians(meridians,labels=[0,0,0,1],fontsize=12)
    #m.drawparallels(np.arange(min(latsize),max(latsize)+1,tick_int),labels=[1,0,0,0])
    #m.drawmeridians(np.arange(min(lonsize),max(lonsize)+1,tick_int),labels=[0,0,0,1])
    x,y=m(lon,lat)
    plot=m.scatter(x,y,s=60, c = temp, cmap='coolwarm')
    fig.colorbar(plot)
    #plot_depth(m,mode='isobaths')
    mind="{:0.0f}".format(m2fth(min(df['depth (m)'])))
    maxd="{:0.0f}".format(m2fth(max(df['depth (m)'])))
    plt.title(str(len(df))+' hauls with depth ranges: '+mind+' to '+maxd+' fths w/109 fth (200m) isobath plotted',fontsize=10)
    df['datet']=pd.to_datetime(df['time (UTC)'])
    df['datet_naive'] = df['datet'].apply(lambda t: t.replace(tzinfo=None))
    df.set_index('datet_naive',inplace=True)
    print(str(min(df.index))[:10])
    plt.suptitle(' eMOLT realtime '+surf_or_bot+' temperature (degF): '+str(min(df.index))[:10]+' to '+str(max(df.index))[:10] ,fontsize='10')
    plt.savefig('map_emolt_erddap.png')
    
def plot_depth(m,depthint=[100.,200.],mode='fill'):
    # uses FVCOM grid values
    # where "m" is a basemap object
    # where depth int is the depth desired
    url='http://www.smast.umassd.edu:8080/thredds/dodsC/fvcom/hindcasts/30yr_gom3'
    nc = netCDF4.Dataset(url).variables
    lats = nc['lat'][:]
    lons = nc['lon'][:]
    depth = nc['h'][:]  # depth
    xs,ys=m(lons,lats)
    if mode=='fill':
        plt.tricontourf(xs,ys,depth,[200.,1000.],colors='violet',zorder=0)
    else:
        plt.tricontour(xs,ys,depth,[200.],linewidths=0.3,linestyles='dashed',zorder=0)

def add_old_emolt_csv(df,startt):
    # reads old _emolt_QCed.csv and makes a dataframe similar to that derived from the new ERDDAP
    df=df.drop(['tow_id','segment_type'],axis=1)
    dfo=pd.read_csv('http://emolt.org/emoltdata/emolt_QCed.csv')
    dfo.drop(['Unnamed: 0','vessel','depth_range','hours','std_temp','flag'],axis=1,inplace=True)
    dfo.rename(columns={'datet':'time (UTC)','lat':'latitude (degrees_north)','lon':'longitude (degrees_east)','mean_temp':'temperature (degree_C)','depth':'depth (m)'}, inplace=True)
    dfo['datet']=pd.to_datetime(dfo['time (UTC)'])
    dfo=dfo[dfo['datet']>pd.to_datetime(startt).tz_localize(None)]
    dfo.drop('datet',axis=1,inplace=True)
    df=pd.concat([df,dfo])
    return df
    
def plt_profiles(df): # plot profiles like the old "plt_ctd_sta_profiles.py"
    # loading coastlines & bathy lines
    #coastfilename='c:/users/james.manning/Downloads/basemaps/capecod_coastline_detail.csv'
    coastfilename='c:/users/james.manning/Downloads/basemaps/us_coast.dat'
    dfc=pd.read_csv(coastfilename,delim_whitespace=True,names=['lon','lat'])
    bathyfile='c:/users/james.manning/Downloads/basemaps/necs_60m.bty'
    dfb=pd.read_csv(bathyfile,delim_whitespace=True,names=['lon','lat','d1','d2'])
    dfb=dfb[dfb.lat!=0]
    dfb['lon']=dfb['lon']*-1
    url='http://www.smast.umassd.edu:8080/thredds/dodsC/fvcom/hindcasts/30yr_gom3'
    nc = netCDF4.Dataset(url).variables
    lats = nc['lat'][:]
    lons = nc['lon'][:]
    depth = nc['h'][:]  # depth
    # plot bathy
    
    dfs=df.drop_duplicates(subset='sta')# cast positions
    stas=dfs.sta.values
    dts=dfs.dtime
    #stas=stas[0:24]
    count=0
    for i in dts:
        if mode=='just_station_plot':
            fig, ax1 = plt.subplots(1, 1) 
        else:
            fig, (ax1, ax2) = plt.subplots(1, 2)
        #plot coast
        ax1.plot(dfc.lon,dfc.lat,'k.',markersize=1)
    
        # plot bathy
        ax1.tricontour(lons,lats,depth,[200.],colors='purple')
        ax1.plot(dfb.lon,dfb.lat,'g.',markersize=1)
        ax1.text(-71.,39.,'60m isobath',color='g')
        ax1.text(-71.,38.5,'200m isobath',color='purple')
    
        # plot stations
        ax1.plot(dfs.lon,dfs.lat,'r.',markersize=12)
        df1=df[df['dtime']==i]
        ax1.plot(df1.lon[0],df1.lat[0],'k.',markersize=30)
        ax1.set_title('R/V Henry Bigelow June 2022',fontsize=12)
        ax1.set_ylim(min(dfs.lat)-.1,max(dfs.lat)+.1)
        ax1.set_xlim(min(dfs.lon)-.1,max(dfs.lon)+.1)
        ax1.text(-71.,38.,df1.sta[0],color='k')
        ax1.text(-74.5,44.,str(i)[:-3])
        if mode=='just_station_plot':
            for j in range(len(dfs)):
                ax1.text(dfs.lon.values[j],dfs.lat.values[j],dfs.sta.values[j],color='k',verticalalignment='center',horizontalalignment='center',fontsize=6)
            break
        box = ax1.get_position()
        box.x0 = box.x0 - 0.05
        box.x1 = box.x1 - 0.05
        ax1.set_position(box)
        # plot profiles
    
        df1=df1[df1['depth']>2.0]
        #id=np.where(np.diff(df1['depth'])<0)
        id=np.where(df1['depth']==max(df1['depth']))[0][0]
        df1=df1[0:id]#downcast
        #ax2.plot(df1['temp'].values[id[0]],df1['depth'].values[id[0]]*-1.,'r-')
        ax2.plot(df1['temp'].values,df1['depth'].values*-1.,'r-')
        ax2.set_ylim(-100.,0)
        ax2.set_xlabel(df1['sta'].values[0]+' temp (degC)',color='r')
        ax2.set_ylabel('depth (meters)')
        
    
        ax3 = ax2.twiny()
        ax3.plot(df1['salt'].values,df1['depth'].values*-1.,'c-')
        ax3.set_xlim(31.,36.)
        ax3.set_title('salinity (PSU)',color='c')
    
        count=count+1
        #fig.savefig('plots/'+"{:03d}".format(count)+'.png')
        ib=str(i).replace(' ','_')
        ib=ib.replace(':','')
        fig.savefig('plots/'+ib+'.png')
        plt.close(fig)
    if mode=='gif':
        make_gif('c:/users/james.manning/Downloads/ctd/plots/HB2204.gif','c:/users/james.manning/Downloads/ctd/plots/',frame_length=2.0)
    else:
        fig.savefig('station_plot.png')
    

def getgbox(area):
  # gets geographic box based on area
  if area=='SNE':
    gbox=[-71.,-66.,39.,42.] # for SNE
  elif area=='OOI':
    gbox=[-72.,-69.5,39.5,41.5] # for OOI
  elif area=='GBANK':
    gbox=[-70.5,-66.,40.5,42.5] # for GBANK
  elif area=='GS':           
    gbox=[-71.,-63.,38.,42.5] # for Gulf Stream
  elif area=='NorthShore':
    gbox=[-71.,-69.5,41.5,43.] # for north shore
  elif area=='WNERR':
    gbox=[-71.,-69.,41.0,44.] # for WNERR deployment
  elif area=='DESPASEATO':
    gbox=[-71.,-69.5,42.6,43.25] # for miniboat Despaseato deployment
  elif area=='CCBAY':
    gbox=[-70.75,-69.8,41.5,42.3] # CCBAY
  elif area=='inside_CCBAY':
    gbox=[-70.75,-70.,41.7,42.15] # inside_CCBAY
  elif area=='NEC':
    gbox=[-69.,-64.,39.,43.5] # NE Channel
  elif area=='NE':
    gbox=[-76.,-66.,35.,44.5] # NE Shelf 
  return gbox

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
            
gb= list(map(str, getgbox(area)))# returns a list of strings
url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E='+startt+'&latitude%3E='+gb[2]+'&latitude%3C='+gb[3]+'&longitude%3E='+gb[0]+'&longitude%3C='+gb[1]+''
#url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?segment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E=2023-12-01T13%3A53%3A21Z&latitude%3E=41.5&latitude%3C=42.3&longitude%3E=-70.75&longitude%3C=-70.'
df=pd.read_csv(url)

map_emolt_erddap(df,add_border=.2,resolution='i',surf_or_bot='bottom',startt=startt)
eMOLT_cloud(['/home/user/sst/map_emolt_erddap.png'])