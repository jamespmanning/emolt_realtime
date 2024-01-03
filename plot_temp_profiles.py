#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  2 17:21:46 2024
derived from my circa 2021 "plot_ctd_sta_profiles.py"
@author: JiM
"""

import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import netCDF4
import ftplib
import glob
import os,imageio
# add some homegrown functions
from conversions import c2f,m2fth

mode='gif'
area='NE'
st='Profiling%20Up' #segment_type
startt=(dt.datetime.now()-dt.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')#'2023-12-01T13:53:21Z'
surf_or_bot='bottom'

def eMOLT_cloud(ldata):# send file to SD machine where "ldata" is an array in bracketts like ['file1','file2']
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

def make_gif(gif_name,png_dir,frame_length = 0.2,end_pause = 4 ):
    '''use images to make the gif
    frame_length: seconds between frames
    end_pause: seconds to stay on last frame
    the format of start_time and end time is string, for example: %Y-%m-%d(YYYY-MM-DD)'''
    
    if not os.path.exists(os.path.dirname(gif_name)):
        os.makedirs(os.path.dirname(gif_name))
    allfile_list = glob.glob(os.path.join(png_dir,'*.png')) # Get all the pngs in the current directory
    file_list=allfile_list
    list.sort(file_list, key=lambda x: x.split('/')[-1].split('t')[0]) # Sort the images by time, this may need to be tweaked for your use case
    images=[]
    # loop through files, join them to image array, and write to GIF called 'wind_turbine_dist.gif'
    for ii in range(0,len(file_list)):       
        file_path = os.path.join(png_dir, file_list[ii])
        if ii==len(file_list)-1:
            for jj in range(0,int(end_pause/frame_length)):
                images.append(imageio.imread(file_path))
        else:
            images.append(imageio.imread(file_path))
    # the duration is the time spent on each image (1/duration is frame rate)
    imageio.mimsave(gif_name, images,'GIF',duration=frame_length)
# loading coastlines & bathy lines
#coastfilename='c:/users/james.manning/Downloads/basemaps/capecod_coastline_detail.csv'
coastfilename='us_coast.dat'
dfc=pd.read_csv(coastfilename,delim_whitespace=True,names=['lon','lat'])
bathyfile='necs_60m.bty'
dfb=pd.read_csv(bathyfile,delim_whitespace=True,names=['lon','lat','d1','d2'])
dfb=dfb[dfb.lat!=0]
dfb['lon']=dfb['lon']*-1

gb= list(map(str, getgbox(area)))# returns a list of strings
url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E='+startt+'&latitude%3E='+gb[2]+'&latitude%3C='+gb[3]+'&longitude%3E='+gb[0]+'&longitude%3C='+gb[1]+''
#url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?segment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E=2023-12-01T13%3A53%3A21Z&latitude%3E=41.5&latitude%3C=42.3&longitude%3E=-70.75&longitude%3C=-70.'
df=pd.read_csv(url)
df.rename(columns={'latitude (degrees_north)':'lat','longitude (degrees_east)':'lon','depth (m)':'depth','temperature (degree_C)':'temp'},inplace=True)

dfs=df.drop_duplicates(subset='tow_id')# cast positions
dfs.sort_values("lat", inplace=True)
stas=dfs.tow_id.values
dts=dfs['time (UTC)']
dtow=dfs['tow_id']

count=0
for i in dtow:
    if mode=='just_station_plot':
        fig, ax1 = plt.subplots(1, 1) 
    else:
        fig, (ax1, ax2) = plt.subplots(1, 2)
    #plot coast
    ax1.plot(dfc.lon,dfc.lat,'k.',markersize=1)
    ax1.plot(dfb.lon,dfb.lat,'g.',markersize=1)
    ax1.text(-71.,39.,'60m isobath',color='g')
    ax1.text(-71.,38.5,'200m isobath',color='purple')
    
    # plot stations
    ax1.plot(dfs.lon,dfs.lat,'r.',markersize=12)
    df1=df[df['tow_id']==i]
    ax1.plot(df1.lon.values[0],df1.lat.values[0],'k.',markersize=30)
    ax1.set_title('eMOLT realtime',fontsize=12)
    ax1.set_ylim(min(dfs.lat)-.1,max(dfs.lat)+.1)
    ax1.set_xlim(min(dfs.lon)-.1,max(dfs.lon)+.1)
    ax1.text(-71.,38.,df1.tow_id.values[0],color='k')
    ax1.text(-74.5,44.,str(i)[:-3])
    if mode=='just_station_plot':
        for j in range(len(dfs)):
            ax1.text(dfs.lon.values[j],dfs.lat.values[j],dfs.tow_id.values[j],color='k',verticalalignment='center',horizontalalignment='center',fontsize=6)
        break
    box = ax1.get_position()
    box.x0 = box.x0 - 0.05
    box.x1 = box.x1 - 0.05
    ax1.set_position(box)
    # plot profiles
    
    #df1=df1[df1['depth']>2.0]
    #id=np.where(np.diff(df1['depth'])<0)
    #id=np.where(df1['depth']==max(df1['depth']))[0][0]
    #df1=df1[0:id]#downcast
    #ax2.plot(df1['temp'].values[id[0]],df1['depth'].values[id[0]]*-1.,'r-')
    ax2.set_title(df1['time (UTC)'].values[0][:10]+' raw upcast in '+str(max(df1['depth'].values))+' meters')
    ax2.plot(df1['temp'].values,df1['depth'].values*-1.,'r-')
    ax2.set_ylim(-100.,0)
    ax2.set_xlabel('tow_id '+str(df1['tow_id'].values[0])+' temp (degC)',color='r')
    ax2.set_ylabel('depth (meters)')
    
    '''
    ax3 = ax2.twiny()
    ax3.plot(df1['salt'].values,df1['depth'].values*-1.,'c-')
    ax3.set_xlim(31.,36.)
    ax3.set_title('salinity (PSU)',color='c')
    '''
    count=count+1
    #fig.savefig('plots/'+"{:03d}".format(count)+'.png')
    ib=str(i).replace(' ','_')
    ib=ib.replace(':','')
    #fig.savefig('plots/'+ib+'.png')
    fig.savefig('plots/'+str(count)+'.png')
    plt.close(fig)

if mode=='gif':
    make_gif('gif/plot_temp_profiles.gif','/home/user/sst/plots',frame_length=2.0)
else:
    fig.savefig('station_plot.png')
#eMOLT_cloud(['gif/plot_temp_profiles.gif'])