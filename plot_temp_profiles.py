#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  2 17:21:46 2024
derived from "plot_ctd_sta_profiles.py" which plots NEFSC CTD data
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
import conda 
conda_file_dir = conda.__file__
conda_dir = conda_file_dir.split('lib')[0]
proj_lib = os.path.join(os.path.join(conda_dir, 'share'), 'proj')
from mpl_toolkits.basemap import Basemap
import warnings
warnings.filterwarnings("ignore") # JiM added Sep 2020 to supopress the "matplotlibDeprecationWarning"
# add some homegrown functions
from conversions import c2f,m2fth

#HARDCODES
area='NE'
st='Profiling%20Up' #segment_type
st='2' # made this change June 2025
startt=(dt.datetime.now()-dt.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')#'2023-12-01T13:53:21Z'
surf_or_bot='bottom'
try:
    url='http://www.smast.umassd.edu:8080/thredds/dodsC/fvcom/hindcasts/30yr_gom3'
    nc = netCDF4.Dataset(url).variables
    lats = nc['lat'][:]
    lons = nc['lon'][:]
    depths = nc['h'][:]  # depth
    depths_down='no'
except:
    print('30yr_gom3 down')
    depths_down='yes'

# clean up the plots directory for this new run
files = os.listdir("/home/user/sst/plots/")
for file in files:
    os.remove('/home/user/sst/plots/'+file) # delete all files
    
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

def make_basemap(gbox,resolution='i'):
    latsize=[gbox[2],gbox[3]]
    lonsize=[gbox[0],gbox[1]]
    tick_int=gbox[3]-gbox[2] # allow for 3-4 tick axis label intervals
    if (tick_int>=1):
        tick_int=1.   # make the tick_interval integer increments
    elif (tick_int>.5) & (tick_int<1):
        tick_int=.5
    else:
        tick_int=.2
    
    #fig,ax=plt.subplots()
    m = Basemap(projection='merc',llcrnrlat=min(latsize),urcrnrlat=max(latsize),\
                llcrnrlon=min(lonsize),urcrnrlon=max(lonsize),resolution=resolution)
    m.fillcontinents(color='gray')
    #parallels = np.arange(0.,90,tick_int)
    #m.drawparallels(parallels,labels=[1,0,0,0],fontsize=12)
    # draw meridians
    #meridians = np.arange(180.,360.,tick_int)
    #m.drawmeridians(meridians,labels=[0,0,0,1],fontsize=12)
    #return m,fig,(ax1,ax2)
    return m

def plot_depth(m,lons,lats,depths,depthint=[100.,200.],mode='fill'):
    # uses FVCOM grid values
    # where "m" is a basemap object
    # where depth int is the depth desired
    ''' the following might be included in main program
    url='http://www.smast.umassd.edu:8080/thredds/dodsC/fvcom/hindcasts/30yr_gom3'
    nc = netCDF4.Dataset(url).variables
    lats = nc['lat'][:]
    lons = nc['lon'][:]
    depths = nc['h'][:]  # depth
    '''
    xs,ys=m(lons,lats)
    if mode=='fill':
        plt.tricontourf(xs,ys,depths,[200.,1000.],colors='violet',zorder=0)
    else:
        plt.tricontour(xs,ys,depths,[200.],linewidths=0.3,linestyles='dashed',zorder=0)

def make_gif(gif_name,png_dir,frame_length = 0.2,end_pause = 4,ss=10):
    '''use images to make the gif
    frame_length: seconds between frames
    end_pause: seconds to stay on last frame
    the format of start_time and end time is string, for example: %Y-%m-%d(YYYY-MM-DD)'''
    
    if not os.path.exists(os.path.dirname(gif_name)):
        os.makedirs(os.path.dirname(gif_name))
    allfile_list = glob.glob(os.path.join(png_dir,'*.png')) # Get all the pngs in the current directory
    file_list=allfile_list
    #print(file_list)
    #list.sort(file_list, key=lambda x: x.split('/')[-1].split('t')[0]) # Sort the images by time, this may need to be tweaked for your use case
    images=[]
    # loop through files, join them to image array, and write to GIF 
    for ii in range(0,len(file_list),ss):       
        file_path = os.path.join(png_dir, file_list[ii])
        if ii==len(file_list)-1:
            for jj in range(0,int(end_pause/frame_length)):
                images.append(imageio.imread(file_path))
        else:
            images.append(imageio.imread(file_path))
    # the duration is the time spent on each image (1/duration is frame rate)
    imageio.mimsave(gif_name, images,'GIF',duration=3000)#,duration=frame_length)

#MAIN CODE
gbox=getgbox(area) # returns a list of corners [minlon,maxlon,minlat,maxlat]
gb= list(map(str, gbox))# returns a list of strings
url='http://erddap.emolt.net/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type='+st+'&time%3E='+startt+'&latitude%3E='+gb[2]+'&latitude%3C='+gb[3]+'&longitude%3E='+gb[0]+'&longitude%3C='+gb[1]+''
#url='http://erddap.emolt.net/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E='+startt+'&latitude%3E='+gb[2]+'&latitude%3C='+gb[3]+'&longitude%3E='+gb[0]+'&longitude%3C='+gb[1]+''
#url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?tow_id%2Csegment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E='+startt+'&latitude%3E='+gb[2]+'&latitude%3C='+gb[3]+'&longitude%3E='+gb[0]+'&longitude%3C='+gb[1]+''
#url='http://54.208.149.221:8080/erddap/tabledap/eMOLT_RT_QAQC.csvp?segment_type%2Ctime%2Clatitude%2Clongitude%2Cdepth%2Ctemperature&segment_type=%22'+st+'%22&time%3E=2023-12-01T13%3A53%3A21Z&latitude%3E=41.5&latitude%3C=42.3&longitude%3E=-70.75&longitude%3C=-70.'
df=pd.read_csv(url)
df.rename(columns={'latitude (degrees_north)':'lat','longitude (degrees_east)':'lon','depth (m)':'depth','temperature (degree_C)':'temp'},inplace=True)

dfs=df.drop_duplicates(subset='tow_id')# cast positions
dfs.sort_values("lat", inplace=True)
stas=dfs.tow_id.values
dts=dfs['time (UTC)']
dtow=dfs['tow_id']
numtows=len(dtow)
count=0

for i in dtow:#[0:1]:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8,10))
    plt.sca(ax1) # set the current axis

    #plot coast
    m=make_basemap(gbox)
    
    # plot stations
    x,y=m(dfs.lon.values,dfs.lat.values)    
    bx=(max(x)-min(x))/20.
    by=(max(y)-min(y))/20.
    ax1.plot(x,y,'r.',markersize=12)
    df1=df[df['tow_id']==i]
    x1,y1=m(df1.lon.values,df1.lat.values)
    #print(y1[0])
    ax1.plot(x1[0],y1[0],'k.',markersize=30)
    plt.title(str(numtows)+' tows/profiles in the last 30 days of realtime eMOLT',fontsize=10)
    if depths_down=='no':
        plot_depth(m,lons,lats,depths,mode='isobaths')
        ax1.set_xlabel("{:0.0f}".format(m2fth(max(df1['depth'].values)))+' fth haul w/109 fth (200m) dashed line plotted')

    box = ax1.get_position()
    box.x0 = box.x0 - 0.05
    box.x1 = box.x1 - 0.05
    ax1.set_position(box)

    # plot profiles
    ax2.set_title(df1['time (UTC)'].values[0][:10]+' raw upcast in degF')
    ax2.plot(df1['temp'].values,df1['depth'].values*-1.,'r-')
    ax2.set_ylim(-100.,0)
    ax2.set_xlabel('tow_id '+str(df1['tow_id'].values[0])+' temp (degC)')
    ax2.set_ylabel('depth (meters)')
    
    ax3 = ax2.twiny()
    xl=ax2.get_xlim()
    ax3.plot(c2f(df1['temp'].values)[0],df1['depth'].values*-1.,'m-')
    ax3.set_xlim(c2f(xl[0])[0],c2f(xl[1])[0])
    ax3.set_ylim(-100.,0)
    ax4 = ax2.twinx()
    yl=ax2.get_ylim()
    ax4.plot(df1['temp'].values,m2fth(df1['depth'].values*-1.),'m-')
    ax4.set_ylim(m2fth(yl[0]),m2fth(yl[1]))
    ax4.set_ylabel('depth (fathoms)')
    count=count+1
    ib=str(i).replace(' ','_')
    ib=ib.replace(':','')
    fig.savefig('/home/user/sst/plots/'+str(count+1000)+'.png')
    plt.close(fig)

make_gif('gif/plot_temp_profiles.gif','/home/user/sst/plots',frame_length=.2,ss=10)
eMOLT_cloud(['gif/plot_temp_profiles.gif'])
