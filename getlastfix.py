# -*- coding: utf-8 -*-
"""
Routine to detect last date a transmitter reported
originally coded by JiM in July 2016 
Note: It reads output of "getap2s.py" which is /net/pubweb_html/drifter/emolt.dat 
Note: In May 2017, I added emolt_ap3.dat
Note: In May 2018, I started adding "day last fished"
Note: In Jan 2019, I added DOPPIO (currently subtracts 4 days to pick up file needed)
Note: In Feb 2019, I made a temp file "lastfix_temp.html" until routine was complete
Note: In Mar 2019, I added GOMOFS and fixed "getlastwifi" and revised gomofs_modules method
Note: In Mar 2019, I added "mindistfromharbor" to avoid request from dock to appear in lastfix website
Note: In Apr 2019, I added a) a check on depth compared to NGDC depth and b) a fix to check harborlist
Note: In May 2019, I fixed the getlastwifi function
Note: In Aug 2020, I started implementing the "datatables" sort function
"""

from datetime import datetime as dt
from datetime import timedelta
from dateutil import parser
import pandas as pd
import pytz
import glob
import numpy as np
import netCDF4
import os
from conversions import c2f,dd2dm # converts celcius to fahrenheight and decimal degrees to degrees-minutes format
import zlconversions as zl # Lei Zhao's conversion routines
#import gomofs_modules_zl2 as gomofs_modules # lei Zhao's GOMOFS functions
import gomofs_modules # lei Zhao's final quick version GOMOFS functions
import doppio_modules
#
# HARDCODES:
maxdiff=10. # maximum model error to report
mindistfromharbor=0.4 # mimimum distance in miles from harbor to be considered real
mindist_allowed=0.4 # minimum distance from nearest NGDC depth in km 

# function to get vessel_name and probe serial number given vessel_number
def getclim(lat1=43.,lon1=-73.0,yrday=dt.now().strftime('%j').lstrip('0'),var='Bottom_Temperature/BT_'): 
  # gets climatology of Bottom_Temperature  (note:Surface_Temperature, Bottom_Salinity, or Surface_Salinity also available)
  # as calculated by Chris Melrose from 30+ years of NEFSC CTD data on the NE Shelf 
  # where "lat1", "lon1", and "yrday" are the position and yearday of interest
  # where "var" is the variable of interest (usually Bottom_Temperature) 
  inputdir='/net/data5/jmanning/clim/' # hardcoded climatology directory name "/home/pi/clim/"
  dflat=pd.read_csv(inputdir+'LatGrid.csv',header=None)
  dflon=pd.read_csv(inputdir+'LonGrid.csv',header=None)
  lat=np.array(dflat[0])   # gets the first col (35 to 45)
  lon=np.array(dflon.ix[0])# gets the first row (-75 to -65)
  clim=pd.read_csv(inputdir+var+str(int(yrday))+'.csv',header=None) # gets bottom temp for this day of year
  idlat = np.abs(lat - lat1).argmin() # finds the neareast lat to input lat1
  idlon = np.abs(lon - lon1).argmin() # finds the neareast lon to input lon1
  return clim[idlon][idlat]

def getvesselname(vessel_number):
  df=pd.read_csv('/net/data5/jmanning/drift/codes_temp.dat',sep='\s+',header=None)
  vn=df[df[0]==vessel_number][3].values[0] #
  sn=df[df[0]==vessel_number][4].values[-1]# gets the last one
  form=df[df[0]==vessel_number][5].values[-1]# fixed or mobile as "f" or "m"
  #sn=sn[2:4]# just use the last two characters
  return vn,sn,form

def getlastwifi(sn):
  #if (sn[0:2]=='7a') or (sn[0:2]=='4d'): # case of Lowell Instruments
  if (sn[0]!='1'): # case of Lowell Instruments where serial numbers starting with "1" are aquatec (change made 3/13/19)
    #filenames=glob.glob('/net/data5/jmanning/li/Matdata/temporary/li_*.csv')
    filenames=glob.glob('/home/jmanning/py/aq_main/aqmain_and_raw_check/raw_data_check/result/Matdata/li_*.csv') # change made after lei Zhao's method was implemented in Aug 2019
    #mrf=[s for s in filenames if "li_"+sn[2:4] in s]
    #mrf=[s for s in filenames if "li_"+sn in s] # change made 3/13/2019
    #mrf=[s for s in filenames if "li_"+sn[-5:-1] in s] # change made 4/9/2019 to account for some new sn having 6 characters but only four in filenames
    mrf=[s for s in filenames if "li_"+sn[-4:] in s] # change made 5/16/2019 
  else: # case of Aquatec
    filenames=glob.glob('/home/jmanning/py/api/aqu_data/Logger_sn_*.csv')
    mrf=[s[-19:] for s in filenames if "Logger_sn_"+sn in s]
    #print sn
  if len(mrf)==0:# empty string
    last_wifi_date='never'
  else:  
    mrf=max(mrf)
    print mrf
    try:
      mrf=mrf.split('Matdata/')[1] # this gets the last file according to date
    except:
      pass
 
    if sn[0]!='1': # case of Lowell Instruments
      i=[x for x, v in enumerate(mrf) if v == '_'][1]# finds index of 2nd underscore in the filename
      
      last_wifi_date=dt(int(mrf[i+1:i+5]),int(mrf[i+5:i+7]),int(mrf[i+7:i+9]),0,0,0).strftime("%b %d,%Y")
    else: # aquatec case
      #print mrf
      last_wifi_date=dt(int(mrf[0:4]),int(mrf[4:6]),int(mrf[6:8]),0,0,0).strftime("%b %d,%Y")  
  return last_wifi_date

def getlastfished(vn,mindistfromharbor):
   # function to determine when the last date the vessel "reported" away from the dock
   # assuming the dock position is entered in "harborlist.txt" file
   df=pd.read_csv('/net/pubweb_html/drifter/emolt_ap3_reports.dat',sep=',',header=None) # this file is created during the "getap3.py" run
   df1=df[df[0]==vn] # this assumes the vessel names in "codes_temp.dat" are exactly the same as those on the AssetLink site but with the "F/V " prefix removed
   if len(df1)>0:
     yorn=[] # yes  or no near a harbor
     for k in range(len(df1)): # get positions away from the dock
        [la,lo]=dd2dm(list(df1[2])[k],list(df1[3])[k])# converts to ddmm format
        yorn.append(gps_compare_JiM(la,lo,mindistfromharbor))
     df1[4]=yorn # this is a list of yes and no's
     df2=df1[df1[4]=='no'] # forms a new dataframe with only those positions away from the dock
     list_of_dates=list(df2[1])
     if len(list_of_dates)==0:
        last_fished_date='unknown'
     else:
        last_fished_date=parser.parse(max(list_of_dates)).strftime("%b %d,%Y") # last date away from the dock
   else:
     last_fished_date='unknown'
   if vn=='Lady_Jane':
     last_fished_date='retired'
   return last_fished_date# return the last date the vessel fished

def gps_compare_JiM(lat,lon,mindistfromharbor): #check to see if the boat is in the harbor derived from Huanxin's "wifipc.py" functions   
    # function returns yes if this position is with "mindistfromharbor" miles of a dock
    file='/home/jmanning/py/harborlist.txt' # has header line lat, lon, harbor
    df=pd.read_csv(file,sep=',')
    indice_lat=[i for i ,v in enumerate(abs(np.array(df['lat'])-lat)<mindistfromharbor) if v]
    indice_lon=[i for i ,v in enumerate(abs(np.array(df['lon'])-lon)<mindistfromharbor) if v]
    harbor_point_list=[i for i, j in zip(indice_lat,indice_lon) if i==j]
    if len(harbor_point_list)>0:
       near_harbor='yes'
    else:
       near_harbor='no'
    return near_harbor #yes or no

def get_depth(loni,lati,mindist_allowed):
    # routine to get depth (meters) using vol1 from NGDC
    url='https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol1.nc'
    nc = netCDF4.Dataset(url).variables 
    lon=nc['x'][:]
    lat=nc['y'][:]
    xi,yi,min_dist= nearlonlat_zl(lon,lat,loni,lati) 
    if min_dist>mindist_allowed:
      depth=np.nan
    else:
      depth=nc['z'][yi,xi]
    return depth#,min_dist

def nearlonlat_zl(lon,lat,lonp,latp): # needed for the next function get_FVCOM_bottom_temp 
    """ 
    used in "get_depth"
    """ 
    # approximation for small distance 
    cp=np.cos(latp*np.pi/180.) 
    dx=(lon-lonp)*cp
    dy=lat-latp 
    xi=np.argmin(abs(dx)) 
    yi=np.argmin(abs(dy))
    min_dist=111*np.sqrt(dx[xi]**2+dy[yi]**2)
    return xi,yi,min_dist

def nearlonlat(lon,lat,lonp,latp): # needed for the next function get_FVCOM_bottom_temp
    """
    i=nearlonlat(lon,lat,lonp,latp) change
    find the closest node in the array (lon,lat) to a point (lonp,latp)
    input:
        lon,lat - np.arrays of the grid nodes, spherical coordinates, degrees
        lonp,latp - point on a sphere
        output:
            i - index of the closest node
            For coordinates on a plane use function nearxy           
            Vitalii Sheremet, FATE Project  
    """
    cp=np.cos(latp*np.pi/180.)
    # approximation for small distance
    dx=(lon-lonp)*cp
    dy=lat-latp
    dist2=dx*dx+dy*dy
    i=np.argmin(dist2)
    return i

def get_FVCOM_bottom_temp(lati,loni,dtime,layer): # gets modeled temp using GOM3 forecast
        '''
        Taken primarily from Rich's blog at: http://rsignell-usgs.github.io/blog/blog/2014/01/08/fvcom/ on July 30, 2018
        where lati and loni are the position of interest, dtime is the datetime, and layer is "-1" for bottom
        '''
        #urlfvcom = 'http://www.smast.umassd.edu:8080/thredds/dodsC/fvcom/hindcasts/30yr_gom3'
        #urlfvcom = 'http://www.smast.umassd.edu:8080/thredds/dodsC/FVCOM/NECOFS/Forecasts/NECOFS_FVCOM_OCEAN_MASSBAY_FORECAST.nc'
        urlfvcom = 'http://www.smast.umassd.edu:8080/thredds/dodsC/FVCOM/NECOFS/Forecasts/NECOFS_GOM3_FORECAST.nc'
        nc = netCDF4.Dataset(urlfvcom).variables
        #first find the index of the grid 
        lat = nc['lat'][:]
        lon = nc['lon'][:]
        inode = nearlonlat(lon,lat,loni,lati)
        #second find the index of time
        time_var = nc['time']
        itime = netCDF4.date2index(dtime,time_var,select='nearest')# where startime in datetime
        return nc['temp'][itime,layer,inode]


#MAIN PROGRAM

# open output html file and write header line
outfile=open('/net/pubweb_html/drifter/lastfix_temp.html','w')
#outfile=open('/net/pubweb_html/drifter/lastfix_temp4.html','w')
#outfile=open('/net/newfish_www/html/nefsc/emolt/lastfix_temp.html','w')

outfile.write('<html><style>.redtext {color: red;}</style>\n')
outfile.write('<head><script src="https://code.jquery.com/jquery-latest.min.js" type="text/javascript"></script>\n')
outfile.write('<script type="text/javascript" src="https://cdn.datatables.net/1.10.16/js/jquery.dataTables.min.js"></script>\n')  
outfile.write('<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.21/css/jquery.dataTables.min.css">\n')
outfile.write('<script type="text/javascript"> $(document).ready( function () {$(\'#table_id\').DataTable();} );</script></head>\n')

outfile.write('<h3>commercial fishing vessels telemetering realtime bottom temperatures from the Northeast Shelf</h3>\n')
outfile.write('<table id="table_id" border="1" class="display">\n')
outfile.write('<thead><tr><th>vessel</th><th>date_last_telemetered</th><th>last_obs (degF)</th><th>FVCOM</th><th>DOPPIO</th><th>GOMFS (degF)</th><th>Climatology</th><th>#Transmitted</th><th>probe SN</th><th>last_wifi_upload</th><th>last_fished</th></tr></thead>\n')
outfile.write('<tbody>\n')

# read input file assuming that emolt_ap3.dat has been appended to this at 10, 40 minutes after even hour
df=pd.read_csv('https://nefsc.noaa.gov/drifter/emolt.dat',sep='\s+',header=None) 
#df=pd.read_csv('https://apps-nefsc.fisheries.noaa.gov/drifter/emolt.dat',sep='\s+',header=None)           # assetlink results and assumes rockblock hauls already appended to AL by "getap3.py" 8/19/2020

# create a datetime for all fixes
datet=[]
for k in range(len(df)): # for each fix
  datet.append(dt(df[16][k],df[2][k],df[3][k],df[4][k],df[5][k]))
df['datet']=datet

# for each vessel find the last datetime and write to file
ves=list(set(df[0])) # list of unique vessels numbers

sumnum=0
anomaly,moderror,moderror_doppio,moderror_gomofs=[],[],[],[]# intitialize a few variables for appending later
for j in range(len(ves)): # for each vessel
  print ves[j]
  df1=df[df[0]==ves[j]]# gets all the records for this one vessel in new dataframe "df1"
  # added the following 6 lines 29 Mar 2019
  yorn=[] # yes  or no near a harbor
  for k in range(len(df1)): # get positions away from the dock
        #[la,lo]=dd2dm(list(df1[2])[k],list(df1[3])[k])# converts to ddmm format
        [la,lo]=dd2dm(list(df1[8])[k],list(df1[7])[k])# converts to ddmm format change indexes 4/9/2019
        yorn.append(gps_compare_JiM(la,lo,mindistfromharbor))
  df1[4]=yorn # this is a list of yes and no's
  df1=df1[df1[4]=='no'] # forms a new dataframe with only those positions away from the dock
  ####
  if len(df1)>0:# note in some cases the vessel may have only reported temps from the dock
    [vn,sn,form]=getvesselname(ves[j])#gets vessel name, probe serial number, and fixed_or_mobile for this vessel number
    print vn
    last_wifi_date=getlastwifi(sn)# gets date of last wifi for this serieal number
    last_fishing_date=getlastfished(vn,mindistfromharbor) 
    obst=str(round(c2f(float(df1[14][-1:].values[0]))[0],1)) # last observation for this vessel
    climt=str(round(c2f(getclim(df1[8][-1:].values[0],df1[7][-1:].values[0],str(int(max(df1.datet).to_pydatetime().strftime('%j')))))[0],1))# climatology for this day based on Melrose
    print 'looking for NGDC depth'
    depth_ngdc=get_depth(df1[7][-1:].values[0],df1[8][-1:].values[0],mindist_allowed)# ngdc bottom depth estimate
    if abs(df1[11][-1:].values[0]-depth_ngdc)/depth_ngdc>0.15:# big difference in observed and NGDC depth
      obst=obst+'*'
    #get FVCOM
    print 'looking for FVCOM'
    if max(df1.datet).to_pydatetime()>dt.now()-timedelta(days=3): # if within model forecast time period 
      try:
        # JiM modified the "str(round(" prefix on 7/8/2020
        modt=str(round(c2f(get_FVCOM_bottom_temp(df1[8][-1:].values[0],df1[7][-1:].values[0],max(df1.datet).to_pydatetime(),-1))[0],1))
        #modt='%.3g' % c2f(get_FVCOM_bottom_temp(df1[8][-1:].values[0],df1[7][-1:].values[0],max(df1.datet).to_pydatetime(),-1))[0]# model based on FVCOM GOM3 FORECAST where "-1" is bottom layer
        if abs(float(obst)-float(modt))>maxdiff: #something must be wrong
          modt='nan'
      except:
        print 'FVCOM is down?'
        modt='nan' # the FVCOM must be down
    else:
      modt='nan'
    # get DOPPIO
    if max(df1.datet).to_pydatetime()>=dt(2017,11,1,0,0,0):
      print 'looking for DOPPIO'
      try:
        modt_doppio=str(round(c2f(doppio_modules.get_doppio(lat=df1[8][-1:].values[0],lon=df1[7][-1:].values[0],depth='bottom',time=max(df1.datet).to_pydatetime()-timedelta(days=4),fortype='temperature'))[0],1))
      except:
        modt_doppio=np.nan
      print 'looking for GOMOFS'
      try:
        modt_gomofs=str(round(c2f(gomofs_modules.get_gomofs(max(df1.datet).to_pydatetime()-timedelta(days=0),df1[8][-1:].values[0],df1[7][-1:].values[0],'bottom'))[0],1))
      except:
        modt_gomofs=np.nan
    if (last_fishing_date!='unknown') and (last_fishing_date!='retired'):
      if form=='f':
        days_to_worry=10 # fixed gear case because they do not always haul the trap each trip
      else:
        days_to_worry=1 # mobile case
      if max(df1.datet).to_pydatetime()<parser.parse(last_fishing_date)-timedelta(days=days_to_worry): # makes sure there are at least two days difference
         add_color=' class=redtext'
      else:
         add_color=''
    else:
      add_color=''
    outfile.write('<tr><td'+add_color+'>'+vn+'</td>'+'<td>'+max(df1.datet).strftime("%Y-%m-%d")+'</td><td>'+obst+'</td><td>'+modt+'</td><td>'+str(modt_doppio)+'</td><td>'+str(modt_gomofs)+'</td><td>'+climt+'</td><td>'+str(len(df1))+'</td><td>'+sn+'</td><td>'+last_wifi_date+'</td><td>'+last_fishing_date+'</td></tr>\n')
    #outfile.write('<tr><td'+add_color+'>'+vn+'</td>'+'<td>'+max(df1.datet).strftime("%b %d,%Y")+'</td><td>'+obst+'</td><td>'+modt+'</td><td>'+modt_doppio+'</td><td>coming soon</td><td>'+climt+'</td><td>'+str(len(df1))+'</td><td>'+sn+'</td><td>'+last_wifi_date+'</td><td>'+last_fishing_date+'</td></tr>\n')
    
    sumnum=sumnum+len(df1)
    if ~np.isnan(float(climt)):
       anomaly.append(float(obst)-float(climt))
    if ~np.isnan(float(modt)):
       moderror.append(float(obst)-float(modt))
    if ~np.isnan(float(modt_doppio)):
       moderror_doppio.append(float(obst)-float(modt_doppio))
    if ~np.isnan(float(modt_gomofs)):
       moderror_gomofs.append(float(obst)-float(modt_gomofs))

outfile.write('<tr><td><b>TOTAL</td><td></td><td></td><td></td><td></td><td></td><td></td><td><b>'+str(sumnum)+'</td><td></td><td></td><td></td></tr>\n')
outfile.write('</tbody></table>')
outfile.write('<br><br> * indicates maximum observed depth is more than 15% different from what the bottom depth is at that location (according to NGDC)')
outfile.write('<br><br> Most recent mean observed minus Melrose-30-year-climatology = '+str(round(np.mean(anomaly),1))+' degF')
if str(round(np.mean(moderror),1))=='nan':
  outfile.write('<br><br> Note: FVCOM model is evidently down.')
else:
  outfile.write('<br><br> Most recent mean observed minus FVCOM GOM3 forecast model = '+str(round(np.mean(moderror),1))+' degF')
outfile.write('<br><br> Most recent mean observed minus DOPPIO forecast model = '+str(round(np.mean(moderror_doppio),1))+' degF')
outfile.write('<br><br> Most recent mean observed minus GOMOFS forecast model = '+str(round(np.mean(moderror_gomofs),1))+' degF')
outfile.write('<br><br> Note: Vessels highlighted in red may require some attention.')
outfile.write('<br><br> Note: To see a map of the last month of observations, click <a href=''http://studentdrifters.org/huanxin/telemetry.html''>here</a>.')
outfile.close()
os.system('cp /net/pubweb_html/drifter/lastfix_temp.html /net/pubweb_html/drifter/lastfix.html')# changed from "mv" to "cp" on 4/9/2019
#os.system('cp /net/newfish_www/html/nefsc/emolt/lastfix_temp.html /net/newfish_www/html/nefsc/emolt/lastfix.html')# changed from "mv" to "cp" on 4/9/2019

