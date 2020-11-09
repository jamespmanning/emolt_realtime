# -*- coding: utf-8 -*-
"""
Created on Tue Dec 22 13:51:53 2015
Accesses AP3 temperature files on the AssetLink FTp site and stores a reformatted emolt_ap3.dat file
which gets appended to the AP2s (GLOBALSTAR) emolt.dat 
@author: hxu
Modifications beginning in Feb 2018
- Feb 7, 2018 JiM now only downloads todays files
- May 31,2018 JiM added fixed or mobile gear options
- Oct 1, 2018 JiM tried to add a exception for Lady Jane being retired when her transmitter is used elsewhere
- Aug 7, 2019 JiM, Huanxin, and Dylan had to recode after AL apparently added some parameters to the JASON files
- Jan 21,2020 JiM added more "point_index" options after discovering some request not getting picked up
- Jan 31,2020 JiM added case where there is no "PointLoc" in the json file
- Aug 19,2020 JiM concantenated "rock_emolt2.dat" to emolt.dat near the bottom
"""
from matplotlib.dates import date2num
from datetime import datetime as dt
import time
import pysftp
import urllib
import os
import sys
import subprocess
from dateutil import parser
import glob
import json
import datetime
import numpy as np
from conversions import f2c
def read_codes():
  # get id,depth from /data5/jmanning/drift/codes_temp.dat
  inputfile1="codes_temp.dat"
  path1="/net/data5/jmanning/drift/"
  #path1='/home/hxu/Downloads/'
  f1=open(path1+inputfile1,'r')
  esn,id,depth,form=[],[],[],[]
  for line in f1:
    esn.append(line.split()[0])
    id.append(line.split()[1])
    depth.append(line.split()[2])
    form.append(line.split()[-1])
  return esn,id,depth,form
  
esn2,ide,depth,form=read_codes()
#print esn2
timenow=datetime.datetime.now()
mth=str(timenow.month).zfill(2)
day=str(timenow.day).zfill(2)
year=str(timenow.year).zfill(4)
os.chdir('/home/jmanning/py/backup')
with pysftp.Connection('mapdata.assetlinkglobal.com', username='noaafisheries', password='TransientEddyFormations') as sftp:
    for fname in sftp.listdir('outgoing'):
        #print fname
        if fname.startswith(year+mth+day):# added day in Feb 2018 and changed from 2018 to 2019 on Jan 3, 2019
            sftp.get('outgoing/'+fname)
files=sorted(glob.glob('/home/jmanning/py/backup/*.json'))
sftp.close()


f_output=open('/net/pubweb_html/drifter/emolt_ap3.dat','w')  
f_output2=open('/net/pubweb_html/drifter/emolt_ap3_reports.dat','w')

esn,date,lat,lon,battery,data_send,meandepth,rangedepth,timelen,meantemp,sdeviatemp=[],[],[],[],[],[],[],[],[],[],[],
c=0
date_all=[];addfiles=[]
for i in files:
    try:
      with open(i) as data_file:    
        data = json.load(data_file)
      # heres where we archive the "reports" from fishing vessels (not request)
      
      if data['momentForward'][0]['Device']['name'][0:3]=='F/V': # This finds reports from Fishing Vessels!!!
              # function to find where the "pointloc" is in the set of points
              try: # In order to get lat/lon we need to try 3 different possible places depending on the generation of AP3s
                lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][3]['PointLoc']['Lat']
                lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][3]['PointLoc']['Lon']
              except:
                try:
                   lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][5]['PointLoc']['Lat'] #possibly has problem to read this data
                   lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][5]['PointLoc']['Lon']
                except:
                   try:
                     lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][4]['PointLoc']['Lat'] #possibly has problem to read this data
                     lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][4]['PointLoc']['Lon']
                   except:
                     try:
                       lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][6]['PointLoc']['Lat'] #possibly has problem to read this data
                       lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][6]['PointLoc']['Lon']
                     except: # added this case in Jan 2020 when there was no PointLoc in Nathaniel_Lee case
                       lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][1]['Point']['MetaLat'] 
                       lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][1]['Point']['MetaLon']
              f_output2.write(data['momentForward'][0]['Device']['name'][4:]+','+str(parser.parse(data['momentForward'][0]['Device']['moments'][0]['Moment']['date']))+','+str(lat)+','+str(lon)+'\n')
            # Here's where we need to define the start of the requested data.  It apparently varies with transmitter and we have to make an adjustment
      esn=data['momentForward'][0]['Device']['esn']
      point_index=2
      try:
          hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
      except:
          point_index=point_index+1 #point_index=3
          try:
            hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
          except:
            point_index=point_index+1 #point_index=4
            try:
              hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex'] 
            except:
              point_index=point_index+1 #point_index=5
              try:
                hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
              except:
                  point_index=point_index+1 # point_index=6
                  try:
                    hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
                  except:
                    point_index=point_index+1 #point_index=7 added Jan 2020
                    try:
                       hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
                    except:
                       point_index=point_index+1 # point_index=8
                       try:
                         hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
                       except:
                         point_index=point_index+1 #point_index=9 added Jan 2020
                         try:
                           hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
                         except:
                           point_index=point_index+1 #point_index=10
                           try:
                             hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
                           except:
                             point_index=point_index+1 #point_index=11 
                             try:
                               hex=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][point_index]['PointHex']['hex']
                             except:
                               continue   
      st=18 # usually digit where data starts with a "9"
      if (hex[st:st+1]!='9') or (hex[st+1:st+2]=='9'):
        st=19 # in some cases it might start at 19 although I have not seen this
      if (hex[st:st+1]!='9') or (hex[st+1:st+2]=='9'):
        st=20 # in some cases it starts at 20 depending on generation of AP3?
      if (hex[st:st+1]!='9') or (hex[st+1:st+2]=='9'):
        st=21 # in some cases it starts at 21 as in the case of Virginia Marise in June 2018
      if (hex[st:st+1]!='9') or (hex[st+1:st+2]=='9'):
        st=22 # in some cases it starts at 22 as in the case of Debbie Sue in June 2018      # now check again that we have the "9" and do not have the "b" for weather data  
      s=hex[:]
      ib=[i for i, letter in enumerate(s[18:21]) if letter == 'b']# finds the 'b' that refers to weather data
      if len(ib)!=0: # still need to check if s[18:] has an eee because, if it does, this is NOT a weather station added this 28 May 2019
         if 'eee' in s[18:]:
            ib=[]
      #if (data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][2]['PointHex']['hex'][st:st+1]=='9') and (data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][2]['PointHex']['hex'][-18]!='b'): #make sure that is temperature data
      if (hex[st:st+1]=='9') and (len(ib)==0): #make sure that is temperature data
       
        if int(parser.parse(data['momentForward'][0]['Device']['moments'][0]['Moment']['date']).strftime('%s')) not in date_all: #checks for repeats
              date_all.append(int(parser.parse(data['momentForward'][0]['Device']['moments'][0]['Moment']['date']).strftime('%s')))

              try:
                  if hex[st:st+1]=='9': #make sure that is temperature data
                          if hex[st+1:st+2]=='9': # checking to make sure we do not have a double "9", added 4/8/19
                            st=st+1
                          addfiles.append(i)
                          # added this if group in Apr 2019 to make sure we are getting right values... making use of the 'eee' string 
                          index_idn1=(np.where(str(esn[-6:])==np.array(ide)))[0][0] # index of the codes_temp file
                          
                          if 'eee' in s:
                             ie=[i for i in range(len(s[18:])) if s[18:].startswith('eee', i)][0]# finds the index of the first 'e' in the 'eee' string skips by the lat/lon fields
                             ie=ie+18 # added 5/28/2019 after having a 'eee' appear in the lat/lon part of the hex
                             meandepth=float(hex[ie-17:ie-14])
                             rangedepth=float(hex[ie-14:ie-11])
                             if form[index_idn1]=='m':
                               timelen=float(hex[ie-11:ie-8])/60.
                             else:
                               timelen=float(hex[ie-11:ie-8]) 
                             meantemp=float(hex[ie-8:ie-4])/100
                             sdeviatemp=float(hex[ie-4:ie])/100
                          else:   
                            sdeviatemp=float(hex[st+14:st+18])/100
                            meantemp=float(hex[st+10:st+14])/100
                            if form[index_idn1]=='m':
                              timelen=float(hex[st+7:st+10])/60.#minutes assumed in mobile gear case
                            else:
                              timelen=float(hex[st+7:st+10])#hours assumed in fixed gear case
                            rangedepth=float(hex[st+4:st+7])
                            meandepth=float(hex[st+1:st+4])
                          
                          try:
                            lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][3]['PointLoc']['Lat'] #possiblly have problem to read this data
                            lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][3]['PointLoc']['Lon']
                            #battery=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][5]['Point']['Battery']
                          except:
                            try:
                              lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][5]['PointLoc']['Lat'] #possiblely have problem to read this data
                              lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][5]['PointLoc']['Lon']
		                      #battery=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][6]['Point']['Battery']
                            except:
                              try:
		                        lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][4]['PointLoc']['Lat'] #possiblely have problem to read this data
		                        lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][4]['PointLoc']['Lon']
		                        #battery=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][6]['Point']['Battery']                              
                              except:
                                try:
		                          lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][6]['PointLoc']['Lat'] #possiblely have problem to read this data
		                          lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][6]['PointLoc']['Lon']
		                          #battery=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][7]['Point']['Battery']
                                except: # added this Jan 31,2020 when Nathaniel_Lee had no pointloc
                                   lat=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][1]['Point']['MetaLat'] 
                                   lon=data['momentForward'][0]['Device']['moments'][0]['Moment']['points'][1]['Point']['MetaLon']                                                               
                          date=parser.parse(data['momentForward'][0]['Device']['moments'][0]['Moment']['date'])
                          yr1=date.year
                          mth1=date.month
                          day1=date.day
                          hr1=date.hour
                          mn1=date.minute
                          
                          yd1=date2num(datetime.datetime(yr1,mth1,day1,hr1,mn1))-date2num(datetime.datetime(yr1,1,1,0,0))
                          datet=datetime.datetime(yr1,mth1,day1,hr1,mn1,tzinfo=None)                    
                          data_send=hex
                  
                  try :
                      
                    if meantemp<30:
                      if (esn[-6:]=='319270') and (datet>dt(2018,5,9,0,0,0)):# added this 9/28 since Bingwei started using this transmitter 
                         print 'should be skipping this Lady Jane case at '+str(datet)
                      else:   
                        index_idn1=(np.where(str(esn[-6:])==np.array(ide)))[0][0] # index of the codes_temp file
                        id_idn1=esn2[index_idn1] # where is the consecutive time this unit was used
                        depth_idn1=-1.0*float(depth[index_idn1]) # make depth negative
                        f_output.write(str(id_idn1).rjust(10)+" "+str(esn[-6:]).rjust(7)+ " "+str(mth1).rjust(2)+ " " +
                            str(day1).rjust(2)+" " +str(hr1).rjust(3)+ " " +str(mn1).rjust(3)+ " " )
                        f_output.write(("%10.7f") %(yd1))
                        f_output.write(" "+("%10.5f") %(lon)+' '+("%10.5f") %(lat)+' '+str(float(depth_idn1)).rjust(4)+ " "
                            +str(np.nan))
                        f_output.write(" "+str(meandepth).rjust(10)+' '+str(rangedepth).rjust(10)+("%6.1f") %(timelen) + ("%6.2f") %(meantemp)+ " "
                              +("%6.2f") %(sdeviatemp)+("%6.0f") %(yr1)+'\n')          
                  except:
                      pass
                  
              except:
                  c=c+1
                  pass
    except:
        pass        
f_output.close()
f_output2.close()
noext=sys.argv[1]
print noext[:-4]
#os.system('cp /net/pubweb_html/drifter/emolt_temp.dat /net/pubweb_html/drifter/emolt.dat')
os.system('cat /net/pubweb_html/drifter/emolt_ap3.dat >> /net/pubweb_html/drifter/emolt.dat')
# Here's where we want to concantenate RockBlock transmissions to AP3 on 8/19/2020
urllib.urlretrieve ("https://studentdrifters.org/posthuanxin/rock_emolt2.dat", "rock_emolt2.dat") # commented out on 9/4/2020 when bad data came through
#urllib.urlretrieve ("https://studentdrifters.org/posthuanxin/emolt_nicks.dat","emolt_nicks.dat")
#urllib.urlretrieve ("https://emolt.org/emolt_nicks.dat","emolt_nicks.dat")# this option wasn't working ... I was getting a "socket error: SSL: CERTIFICATE_VERIFY_FAILED"
os.system('cat rock_emolt2.dat >> /net/pubweb_html/drifter/emolt.dat')
#os.system('cat emolt_nicks.dat >> /net/pubweb_html/drifter/emolt.dat')
pipe2 = subprocess.Popen(['/home/jmanning/anaconda2/bin/python','/home/jmanning/py/getlastfix.py'])
pipe3 = subprocess.Popen(['/home/jmanning/anaconda2/bin/python','/home/jmanning/py/qaqc_emolt.py'])
# the following line creates the "emolt.xml" that is read by drifter/fishtemps.html googlemap
#pipe4 = subprocess.Popen(['/home/jmanning/anaconda2/bin/python','/net/home3/ocn/jmanning/py/ap2s2xml.py',noext[:-4]]) # commented this line 4/10/19 since apparently not needed 
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
