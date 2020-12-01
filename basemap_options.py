#!/usr/bin/python
import sys
from decimal import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib 
from utilities import lat2str, lon2str
from pydap.client import open_url
import netCDF4
import urllib
import os
os.environ['PROJ_LIB'] = 'c:\\Users\\Joann\\anaconda3\\pkgs\\proj4-5.2.0-ha925a31_1\\Library\share'
from mpl_toolkits.basemap import Basemap

def adjustFigAspect(fig,aspect=1/1.3):
    '''
    Adjust the subplot parameters so that the figure has the correct
    aspect ratio.
    '''
    xsize,ysize = fig.get_size_inches()
    minsize = min(xsize,ysize)
    xlim = .4*minsize/xsize
    ylim = .4*minsize/ysize
    if aspect < 1:
        xlim *= aspect
    else:
        ylim /= aspect
    fig.subplots_adjust(left=.5-xlim,
                        right=.5+xlim,
                        bottom=.5-ylim,
                        top=.5+ylim)

################################################################################


##plot the basemap
#parallels_interval mean the interval of xaxis and yaxis,if parallels_interval=0.1 the min(lat)=40.15 max(lat)=40.35, the yaxis label will be 40.2, 40.3 
#lat,lon should be list, if lat just has one value, the format is: lat=[43.5]
# plot the coastline,river,boundary, but the coastline is not good
def basemap_standard(lat,lon,parallels_interval):
    # parallels_interval is the # of degrees between longitude labels
    ## plot the coastline   
    #set up the map in a Equidistant Cylindrical projection
    #Note: See "oceanographic_python.doc" on how to download and install the 3rd party "Basemap" package
    
    #m = Basemap(projection='cyl',llcrnrlat=min(lat)-0.01,urcrnrlat=max(lat)+0.01,\
    #        llcrnrlon=min(lon)-0.01,urcrnrlon=max(lon)+0.01,resolution='h')#,fix_aspect=False)
    m = Basemap(projection='mill',llcrnrlat=min(lat),urcrnrlat=max(lat),\
            llcrnrlon=min(lon),urcrnrlon=max(lon),resolution='h')#,fix_aspect=False)
    #  draw coastlines
    #m.drawcoastlines()
    m.fillcontinents(color='grey')
    m.drawmapboundary()
    #draw major rivers
    #m.drawrivers()
    #print 'new3\n'
    #print str(parallels_interval)
    if  parallels_interval[0]<6.0:
        parallels_interval=parallels_interval[0]
        #draw parallels
        #m.drawparallels(np.arange(int(min(lat)),int(max(lat))+1,float(parallels_interval)),linewidth=0,labels=[1,0,0,0],fmt=lat2str,dashes=[1,1])
        #draw meridians
        #m.drawmeridians(np.arange(int(min(lon)),int(max(lon))+1,float(parallels_interval)),linewidth=0,labels=[0,0,0,1],fmt=lon2str,dashes=[2,2])     
        m.drawparallels(np.arange(min(lat),max(lat)+1,float(parallels_interval)),linewidth=0,labels=[1,0,0,0],fmt=lat2str,dashes=[1,1])
        #draw meridians
        #m.drawmeridians(np.arange(min(lon),max(lon)+1,float(parallels_interval)),linewidth=1,labels=[0,0,0,1],fmt=lon2str,dashes=[2,2],labelstyle='+/-')     
        m.drawmeridians(np.arange(min(lon),max(lon)+1,float(parallels_interval)),linewidth=0,labels=[0,0,0,1],dashes=[2,2])     
    else:
        parallels_interval=parallels_interval[0]
        m.drawparallels(np.arange(min(lat),max(lat)+1,float(parallels_interval)),linewidth=1,labels=[1,0,0,0],fmt=lat2str,dashes=[1,1])
        m.drawmeridians(np.arange(min(lon),max(lon)+1,float(parallels_interval)),linewidth=1,labels=[0,0,0,1],fmt=lon2str,dashes=[1,1])     
        #print 'this is '+str(parallels_interval)
    return m

def basemap_usgs(points,bathy,cont_range,ss):
    #plot the coastline and, if bathy is True, bathymetry is plotted
    #"points" is any list of lat and lon can be any list of positions in decimal degrees
    #parallels_interval is the tick interval on axis
    #cont_range is the depth contours to plot
    #ss is the subsample rate to make things quicker
    lons = points['lons']
    lats = points['lats']
    size = 0.2
    parallels_interval=2

    map_lon = [min(lons)-size,max(lons)+size]
    map_lat = [min(lats)-size,max(lats)+size]
    dmap = Basemap(projection='cyl',
                   llcrnrlat=map_lat[0], llcrnrlon=map_lon[0],
                   urcrnrlat=map_lat[1], urcrnrlon=map_lon[1],
                   resolution='h')#,ax=ax)# resolution: c,l,i,h,f.
    #dmap.drawcoastlines()# draw the coast line
    dmap.fillcontinents(color='grey')
    dmap.drawparallels(np.arange(min(lats),max(lats)+1,float(parallels_interval)),linewidth=1,labels=[1,0,0,0],fmt=lat2str,dashes=[1,1])#url='http://geoport.whoi.edu/thredds/dodsC/bathy/crm_vol1.nc'
    dmap.drawmeridians(np.arange(min(lons),max(lons)+1,float(parallels_interval)),linewidth=1,labels=[0,0,0,1],dashes=[2,2]) 

    if bathy==True: # get some detail bathymetry from USGS
      base_url='http://coastwatch.pfeg.noaa.gov/erddap/griddap/usgsCeSrtm30v6.nc?'
      isub=1  # make isub =1 in production mode

      query='topo[(%f):%d:(%f)][(%f):%d:(%f)]' % (map_lat[1],isub,map_lat[0],map_lon[0],isub,map_lon[1])

      url = base_url+query
      file='usgsCeSrtm30v6.nc'
      urllib.urlretrieve (url, file)
      nc = netCDF4.Dataset(file)
      ncv = nc.variables

      basemap_lat=ncv['latitude'][:]
      basemap_lon=ncv['longitude'][:]
      basemap_topo=ncv['topo'][:]
    
      index_minlat=0#int(round(np.interp(map_lat[0],basemap_lat,range(0,basemap_lat.shape[0]))))
      index_maxlat=int(round(np.interp(map_lat[1],basemap_lat,range(0,basemap_lat.shape[0]))))
      index_minlon=int(round(np.interp(map_lon[0],basemap_lon,range(0,basemap_lon.shape[0]))))
      index_maxlon=int(round(np.interp(map_lon[1],basemap_lon,range(0,basemap_lon.shape[0]))))
    
      min_index_lat=min(index_minlat,index_maxlat)
      max_index_lat=max(index_minlat,index_maxlat)
      min_index_lon=min(index_minlon,index_maxlon)
      max_index_lon=max(index_minlon,index_maxlon)
      #ss=5 #subsample
      print("Using the USGS high res bathy with topo indexes: "+str(min_index_lat)+','+str(max_index_lat)+','+str(min_index_lon)+','+str(max_index_lon))
      X,Y=np.meshgrid(basemap_lon[min_index_lon:max_index_lon:ss],basemap_lat[min_index_lat:max_index_lat:ss])

      # You can set negative contours to be solid instead of dashed:
      matplotlib.rcParams['contour.negative_linestyle'] = 'solid'
      #CS=plt.contourf(X,Y,basemap_topo.topo[min_index_lat:max_index_lat:ss,index_minlon:index_maxlon:ss],cont_range)#,colors=['0.8'])#,linewith=0.05)#cont_range)#,color
      CS=plt.contour(X,Y,basemap_topo[min_index_lat:max_index_lat:ss,index_minlon:index_maxlon:ss],cont_range,linewidths=0.5)#cont_range)#,colors=['0.75','0.80','0.85','0.90'],linewith=0.05)
      plt.clabel(CS, fmt='%5.0f m', colors='b', fontsize=8)

      if min_index_lat==max_index_lat:
        print("No basemap_usgs data available for this area")
      if bathy_shade==True:
        plt.contourf(X,Y,basemap_topo[min_index_lat:max_index_lat:ss,min_index_lon:max_index_lon:ss],[-100,-50,-20,0])#color='red')
          

def basemap_region(region):
    # this is the simplest basemap plotting local coastlines from data in files
    path="" # Y:/bathy/"#give the path if these data files are store elsewhere
    #if give the region, choose the filename
    if region=='sne':
        filename='/net/data5/jmanning/bathy/sne_coast.dat'
    if region=='cc':
        filename='/net/data5/jmanning/bathy/capecod_outline.dat'
    if region=='bh':
        filename='/net/data5/jmanning/bathy/bostonharbor_coast.dat'
    if region=='cb':
        filename='cascobay_coast.dat'
    if region=='pb':
        filename='penbay_coast.dat'
    if region=='ma': # mid-atlantic
        filename='/net/data5/jmanning/bathy/necscoast_noaa.dat'
    if region=='ne': # northeast
        filename='/net/data5/jmanning/bathy/necoast_noaa.dat'   
    if region=='wv': # world vec
        filename='/net/data5/jmanning/bathy/necscoast_worldvec.dat'        
    
    #open the data
    f=open(path+filename)

    lon,lat=[],[]
    for line in f:#read the lat, lon
	    lon.append(line.split()[0])
	    lat.append(line.split()[1])
    nan_location=[]
    # plot the lat,lon between the "nan"
    for i in range(len(lon)):#find "nan" location
        if lon[i]=="nan":
            nan_location.append(i)

    for m in range(1,len(nan_location)):#plot the lat,lon between nan
        lon_plot,lat_plot=[],[]
        for k in range(nan_location[m-1],nan_location[m]):
            lat_plot.append(lat[k])
            lon_plot.append(lon[k])
        plt.plot(lon_plot,lat_plot,'k') 
