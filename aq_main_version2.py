#!/usr/bin/env python3

# -*- coding: utf-8 -*-
'''
version2
Routine to map the realtime eMOLT bottom temps using Leaflets
Created on Wed Sep  6 13:37:50 2017
@author: hxu

Modified by Huanxin 9 Oct 2018 to make temperature read degF
Modified by Lei Zhao in June 2019 to add models and climatology
Modified by JiM in Dec 2019 & Jan/Feb 2020 to improve readability for NERACOOS transfer

This program include 4 basic applications
1. Download raw csv files which have been uploaded by 'wifi.py' to studentdrifters.org ("SD" machine)
2. Look for good csv files and makes plot a graph for each good one
3. Create "telemetry.html"
4. Upload this html and the pngs to the new studentdrifters ftp location


Notes:
1. There is a crontab routine run on the SD machine to move html & pngs from ftp to httpdocs
2. Assumes "telemetry_status.csv" and "dictionary.json" are in the "parameter" directory level with this "py" directory

###############################################
NOTICE: The PATHS YOU HAVE TO CHANGE TO MAKE THEM CORRECT
if you want change the path and name, please go to the function of main()
###############################################
'''
import sys
sys.path.append("/home/jmanning/py/aq_main/aqmain_and_raw_check/aqmain/py/")# add path to homegrown modules needed
import ftplib
import os
import datetime
import glob
from folium.plugins import MarkerCluster
import folium
import random
from func_aq import plot_aq
import numpy as np
import json
import pytz
import read_functions as rf
import upload_modules as up
import math
import create_modules_dictionary as cmd
# JiM added the following 3 lines Sep 2020
import warnings
import pandas as pd
from pandas.core.common import SettingWithCopyWarning

warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
def c2f(*c):
    """
    convert Celsius to Fahrenheit
    accepts multiple values
    """
    if not c:
        c = input ('Enter Celsius value:')
        f = 1.8 * c + 32
        return f
    else:
        f = [(i * 1.8 + 32) for i in c]
        return f    

def csv_files(file_list):
    """pick up all .csv files"""
    _files=[]
    for i in range(len(file_list)):
        if file_list[i].split('.')[1]=='csv':
            _files.append(file_list[i])
    return _files

def download_raw_file(localpath,ftppath):
    '''download the raw data from the student drifter'''
    ftp=ftplib.FTP('66.114.154.52','huanxin','123321')
    print ('Logging in.')
    print ('Accessing files')
    allfilelisthis=csv_files(list_all_files(localpath)) #get all filename and file path exist
    list_all_ftpfiles(ftp,rootdir=ftppath,localpath=localpath,local_list=allfilelisthis)  #download the new raw data there is not exist in local directory 
    allfilelistnew=csv_files(list_all_files(localpath))  #get all filename and file path exist after update
    files=list(set(allfilelistnew)-set(allfilelisthis)) #get the list of filename and filepath that updated
    ftp.quit() # This is the “polite” way to close a connection
    print ('New files downloaded')
    return files

###### START FTP SESSION TO THE OLD STUDENTDRIFTERS MACHINE AND DOWNLOAD RAW CSV
def eastern_to_gmt(filename):
    eastern = pytz.timezone('US/Eastern')
    gmt = pytz.timezone('GMT')
    if len(filename.split('_'))<8:
        times=filename.split('_')[-2]+'_'+filename.split('_')[-1][:-4] #filename likes :  'aqu_data/Logger_sn_1724-7_data_20150528_100400.csv'
    else:
        times=filename.split('_')[-3]+'_'+filename.split('_')[-2] #filename likes : 'aqu_data/Logger_sn_1724-71_data_20151117_105550_2.csv'
    date = datetime.datetime.strptime(times, '%Y%m%d_%H%M%S')
    date_eastern=eastern.localize(date)
    gmtdate=date_eastern.astimezone(gmt)
    return gmtdate

def get_moudules_value(filepathname,vessel_name,dtime): 
    '''get modules' value from the dictionary'''
    dic={}
    with open(filepathname,'r') as fp:
        dictionary = json.load(fp)
    try:
        dic['Doppio']=dictionary[vessel_name]['Doppio_T'][str(dtime)]
        dic['GoMOLFs']=dictionary[vessel_name]['GoMOLFs_T'][str(dtime)]
        dic['FVCOM']=dictionary[vessel_name]['FVCOM_T'][str(dtime)]
        dic['CrmClim']=dictionary[vessel_name]['Clim_T'][str(dtime)]
    except:
        try:
            vessel_name=vessel_name.replace('_',' ')
            dic['Doppio']=dictionary[vessel_name]['Doppio_T'][str(dtime)]
            dic['GoMOLFs']=dictionary[vessel_name]['GoMOLFs_T'][str(dtime)]
            dic['FVCOM']=dictionary[vessel_name]['FVCOM_T'][str(dtime)]
            dic['CrmClim']=dictionary[vessel_name]['Clim_T'][str(dtime)]
        except:
            vessel_name=vessel_name.replace(' ','_')
            dic['Doppio']=dictionary[vessel_name]['Doppio_T'][str(dtime)]
            dic['GoMOLFs']=dictionary[vessel_name]['GoMOLFs_T'][str(dtime)]
            dic['FVCOM']=dictionary[vessel_name]['FVCOM_T'][str(dtime)]
            dic['CrmClim']=dictionary[vessel_name]['Clim_T'][str(dtime)]
    return dic

def list_all_files(rootdir):
    """pick up all files' path and name in rootdirectory"""
    _files = []
    list = os.listdir(rootdir) #List all the directories and files under the folder
    for i in range(0,len(list)):
           path = os.path.join(rootdir,list[i])
           if os.path.isdir(path):
              _files.extend(list_all_files(path))
           if os.path.isfile(path):
              _files.append(path)
    return _files

def list_all_ftpfiles(ftp,rootdir,localpath,local_list):
    """get all files' path and name in rootdirectory this is for student drifter"""

    ftp.cwd(rootdir)
    if not os.path.exists(localpath):
        os.makedirs(localpath)
    filelist = ftp.nlst() #List all the directories and files under the folder
    for i in range(0,len(filelist)):
        filepath = os.path.join(localpath,filelist[i])
        if len(filelist[i].split('.'))!=1:
            if filepath in local_list:
                continue
            else:
                file = open(filepath, 'wb')
                ftp.retrbinary('RETR '+ filelist[i], file.write)
                file.close()
        else:
            ftp.cwd('/')
            rootdirnew=os.path.join(rootdir,filelist[i])
            localpathnew=os.path.join(localpath,filelist[i])
            list_all_ftpfiles(ftp=ftp,rootdir=rootdirnew,localpath=localpathnew,local_list=local_list)

def list_replace(nlist,old,new):
    '''replace some string in list'''
    _list=[]
    for i in range(len(nlist)):
        _list.append(nlist[i].replace(old,new))
    return _list

    
def make_html(raw_path,telemetrystatus_file,pic_path,dictionary,htmlpath,df,pdelta=20): 
    """MAKE TELEMETRY.HTML
    raw_path: the path of store raw files
    telemetry_status: the path and filename of the telemetry status
    pic_path: the path that use to store pictures
    dictionary: the path and filename of dictionary(use to store the modules data)
    pdelta: the timedelta of picture file time with emolt data time
    
    """
    df_tele_status=rf.read_telemetrystatus(path_name=telemetrystatus_file)

    #### START BUILDING THE LEAFLET WEBPAGE, READ A FEW INPUT FILES, CREATE FOLIUM.MAP
    including=list(set(df['vessel_n']))    #vessel number eg. 'Vessel_18'
    map_1 = folium.Map(location=[41.572, -69.9072],width='88%', height='75%',left="3%", top="2%",
                   control_scale=True,
                   detect_retina=True,
                   zoom_start=8,
                     tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Ocean_Basemap/MapServer/tile/{z}/{y}/{x}',
                          attr= 'Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri',
	)
#    map_1.add_tile_layer( name='Esri_OceanBasemap',
#                     tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Ocean_Basemap/MapServer/tile/{z}/{y}/{x}',
#                          attr= 'Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri',                          
#                          )
#    map_1.add_tile_layer(                   name='NatGeo_World_Map',
#                   tiles='http://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
#                   attr= 'Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC',)
    colors = [
            'red',
            'blue',
            'gray',
            'darkred',
            'lightred',
            'orange',
            'beige',
            'green',
            'darkgreen',
            'lightgreen',
            'darkblue',
            'lightblue',
            'purple',
            'darkpurple',
            'pink',
            'cadetblue',
            'lightgray',
            'black'
            ]

    for x in range(int(len(df_tele_status)/len(colors))+2):
        colors=colors+colors
        lat_box=[];lon_box=[]
        route=0;lat=0;lon=0;popup=0;html='';lastfix=1;randomlat=1;randomlon=0
        mc = MarkerCluster()  
    # CREATE ICONS ON THE MAP
    for i in range(0,len(including)): # LOOP THROUGH VESSELS note: I am skipping vessel_1 since that was just at the dock test
        print (i,route,popup,lastfix)
        if i!=route and popup!=0 and lastfix==0 and html!='': #since lastfix was set to 1 before loop, the following lines never get issued??????
            iframe = folium.IFrame(html=html, width=700, height=350)
            popup = folium.Popup(iframe, max_width=900)
            folium.Marker([lat+randomlat,lon+randomlon], popup=popup,icon=folium.Icon(color=colors[route],icon='ok-sign')).add_to(map_1)  
        lastfix=1
        for line in range(len(df)): # LOOP THROUGH EACH LINE OF EMOLT.DAT
            if df.iloc[line]['vessel_n']==including[i]:
#                id_idn1=including[i]
                datet=df.iloc[line]['time']            
                if float(str(df.iloc[line]['depth']))>10:
                    html=''
                    meandepth=df.iloc[line]['depth']
                    rangedepth=df.iloc[line]['rangedepth']
                    len_day=df.iloc[line]['timerange']
                    mean_temp=df.iloc[line]['temp']
                    sdevia_temp=df.iloc[line]['stdtemp']
                    lat=df.iloc[line]['lat']  #get the latitude
                    lon=df.iloc[line]['lon']  #get the longitude
                    vessel_number=including[i].split('_')[1]
                    for ves in range(len(df_tele_status)):
                        if str(df_tele_status['Vessel#'].iloc[ves])==str(vessel_number):
                                          vessel_name=df_tele_status['Boat'].iloc[ves]
                    pic_ym=datet.strftime('%Y%m')
                    picturepath=os.path.join(pic_path,vessel_name,pic_ym)
                    try:
                        dic=get_moudules_value(filepathname=dictionary,vessel_name=vessel_name,dtime=datet)
                        doppio_t,gomofs_t,FVCOM_t,clim_t=dic['Doppio'],dic['GoMOLFs'],dic['FVCOM'],dic['CrmClim']
                    except:
                        doppio_t,gomofs_t,FVCOM_t,clim_t=np.nan,np.nan,np.nan,np.nan
                    
                    #set the value that need display, for example temperature of modules, observed and so on. 
                    content=datet.strftime('%d-%b-%Y  %H:%M')+'<br>Observed temperature: ' +str(round(c2f(float(mean_temp))[0],1)).rjust(4)+'&nbsp;F&nbsp;('+str(round(mean_temp,1)).rjust(4)+'&nbsp;C)'
                    if not (math.isnan(doppio_t) and math.isnan(gomofs_t) and math.isnan(FVCOM_t) and math.isnan(clim_t)):
                        content+='<br>Modelled temperatures:'
                    if not math.isnan(doppio_t):
                        content+='<br>&nbsp;&nbsp;DOPPIO:&nbsp;'+str(round(c2f(float(doppio_t))[0],1)).rjust(4)+'&nbsp;F&nbsp;('+str(round(doppio_t,1)).rjust(4)+'&nbsp;C)'
                    if not math.isnan(gomofs_t):
                        content+='<br>&nbsp;&nbsp;GoMOFS:&nbsp;'+str(round(c2f(float(gomofs_t))[0],1)).rjust(4)+'&nbsp;F&nbsp;('+str(round(gomofs_t,1)).rjust(4)+'&nbsp;C)'
                    if not math.isnan(FVCOM_t):
                        content+='<br>&nbsp;&nbsp;FVCOM :&nbsp;'+str(round(c2f(float(FVCOM_t))[0],1)).rjust(4)+'&nbsp;F&nbsp;('+str(round(FVCOM_t,1)).rjust(4)+'&nbsp;C)'
                    if not math.isnan(clim_t):
                        content+='<br>&nbsp;&nbsp;Climatology: '+str(round(c2f(clim_t)[0],1)).rjust(4)+'&nbsp;F&nbsp;('+str(round(clim_t,1)).rjust(4)+'&nbsp;C)<br>'
                    #content+='<br>Sdevia_temp: '+str(round(c2f(float(sdevia_temp))[0],1))+'&nbsp;F&nbsp;('+str(round(sdevia_temp,1)).rjust(4)+'&nbsp;C)'+\ #JiM made change
                    content+='<br>Sdevia_temp: '+str(round(sdevia_temp,1)).rjust(4)+'&nbsp;C'+\
                    '<br>Observed depth: '+str(round(meandepth/1.8288,1)).rjust(10)+'&nbsp;Fth'+\
                            '<br>Rangedepth: '+str(round(float(rangedepth)/1.8288,1))+'&nbsp;Fth'+\
                            '<br>Haul_duration: '+str(round(len_day,1))+'&nbsp;hours'
                    for aqu_file in glob.glob(os.path.join(picturepath,"*.png")):
                        fpath,fname=os.path.split(aqu_file)
                        filename_time=fname.split('.')[0].split('_')[2:4]
                        dt_fnt=datetime.datetime.strptime(filename_time[0]+filename_time[1],'%Y%m%d%H%M%S')
                        if abs(dt_fnt-datet)<=datetime.timedelta(minutes=pdelta):
                            link='"'+'http://studentdrifters.org'+('/'+os.path.join('/lei/all_pic',fname)).replace('//','/')+'"'
                            icon='star'
                            if html=='':
                                html='''
                                    <p>
                                    <meta name="viewport" content="width=device-width">
                                    <body>
                                    <font size="5">
                                    <code>
                                    '''+content+\
                                    '<br>Click <a href='+link+'>here</a> to view the detailed graph.'+\
                                    '<br><font size="4">C:&nbsp;Celsius&nbsp;&nbsp;F:&nbsp;Fahrenheit''''
                                    </code>
                                    </body>
                                    </p>
                                    '''   
                                                      
                    if html=='':
                        html='''
                            <p>
                            <meta name="viewport" content="width=device-width">
                            <body>
                            <font size="5">
                            <code>
                            '''+content+'<br><font size="4">C: Celsius  F: Fahrenheit  Fth:Fathoms''''
                            </code>
                            </body>
                            </p>
                            '''
                        icon='ok-sign'
                    lon_box.append(lon)
                    lat_box.append(lat)
                    iframe = folium.IFrame(html=html, width=700, height=350)
#                    popup = folium.Popup(iframe, max_width=1500)
#                    iframe = folium.IFrame(html=html)
                    popup = folium.Popup(iframe, max_width=45000)
                    randomlat=random.randint(-3000, 3000)/100000.
                    randomlon=random.randint(-2500, 2000)/100000.
                    mk=folium.Marker([lat+randomlat,lon+randomlon], popup=popup,icon=folium.Icon(icon=icon,color=colors[i]))
#                    mk=folium.Marker([lat+randomlat,lon+randomlon],popup=popup,icon=folium.Icon(icon=icon,color=colors[i]))
                    mc.add_child(mk)
                    map_1.add_child(mc)
                    lastfix=0
        route=i
    #folium.LayerControl().add_to(map_1)
    map_1.save(os.path.join(htmlpath,'telemetry.html'))
    with open(os.path.join(htmlpath,'telemetry.html'), 'a') as file:
        file.write('''        <body>
            <div id="header"><br>
                <h1>&nbsp;&nbsp;&nbsp;&nbsp&nbsp;Realtime bottom temperatures from fishing vessels in the past month</h1>  
                <ul>
                <dir><dir>
                <li>Checkmark icons denotes latest reports color-coded by vessel.
                <li>Numbered icons denote multiple reports in that area color-coded by density of reports.
                <li>Starred icons denote actual reports posted within 10 miles of actual position.
                <li>Starred icons denote actual reports there have detailed graph, ok-sign icon denote there have not detailed graph.
                <li>Layer symbol in upper right denotes other basemap options.
                </dir></dir>
                </ul>
            </div>   
        </body>''')
    file.close()

def make_png(files,pic_path,rootdir,telemetry_status_df):
    '''
    files: that a list include the path and filename 
    pic_path: the path that use to store plot picture
    rootdir: the root directory use to store raw files
    make time series plot about depth and temperature in every file
    '''
    if len(files)==0: #if the list of "files" is empty, skip create picture
        return 0
    allfileimg=list_all_files(pic_path)  # use function "list_all_files" to get the list of file's path and name
    telemetry_status_df.index=telemetry_status_df['Boat']
    for m in range(len(files)):        #loop every file, create picture
        
        vessel_name=os.path.dirname(files[m]).split('/')[-2]
        try:
            ForM=telemetry_status_df['Fixed vs. Mobile'][vessel_name]
        except:
            vessel_name=vessel_name.replace('_',' ')
            ForM=telemetry_status_df['Fixed vs. Mobile'][vessel_name]
            
        if ForM=='Fixed':
            percent=0.95
        elif ForM=='Mobile':
            percent=0.85
        else:
            percent=0.85
        imgfile=files[m].replace(rootdir,pic_path)   #create the image file name 
        picture_path,fname=os.path.split(imgfile)   # get the path of imge need to store
        
        pic_name=plot_aq(files[m],picture_path,allfileimg,percent=percent) # plot graph
        if pic_name=='':
            print(pic_name)
            continue

        if pic_name!='few data':  
            continue



def main():
    #####################
    #Automatically set the file path according to the location of the installation package
    #get the path of file
    #set path
    ddir=os.path.dirname(os.path.abspath(__file__))
    dictionarypath=ddir[::-1].replace('py'[::-1],'dictionary'[::-1],1)[::-1]
    parameterpath=ddir[::-1].replace('py'[::-1],'parameter'[::-1],1)[::-1]
    Rawf_path=ddir[::-1].replace('py'[::-1],'aq/download'[::-1],1)[::-1]
    pic_path=ddir[::-1].replace('py'[::-1],'aq/aqu_pic'[::-1],1)[::-1]
    htmlpath=ddir[::-1].replace('py'[::-1],'html'[::-1],1)[::-1]
    #HARDCODES
    telemetrystatus_file=os.path.join(parameterpath,'telemetry_status.csv')
    dictionaryfile=os.path.join(dictionarypath,'dictionary.json') # dictionary with endtime,doppio,gomofs,fvcom where each model has vesselname,lat,lon,time,temp
    ##############################
    files=download_raw_file(ftppath='/Raw_Data/checked',localpath=Rawf_path)# UPDATE THE RAW csv FILE
    starttime=datetime.datetime.now()-datetime.timedelta(days=30)
    endtime=datetime.datetime.now()
    telemetrystatus_df=rf.read_telemetrystatus(path_name=telemetrystatus_file)
    #emolt='http://www.nefsc.noaa.gov/drifter/emolt.dat' # this is the output of combining getap2s.py and getap3.py
    emolt='http://apps-nefsc.fisheries.noaa.gov/drifter/emolt.dat' # this is the output of combining getap2s.py and getap3.py
    print('get emolt df')
    emolt_df=rf.screen_emolt(start_time=starttime,end_time=endtime,path=emolt)#get emolt data 
#    #run function   
    print('make png')
    make_png(files,pic_path=pic_path,rootdir=Rawf_path,telemetry_status_df=telemetrystatus_df)# make time series image
    print('upload png file')
    up.sd2drf(local_dir=pic_path,remote_dir='/lei_aq_main/all_pic',filetype='png')   #upload the picture to the studentdrifter
    print('make html')
#    #create the dictionary
    cmd.update_dictionary(telemetrystatus_file,starttime,endtime,dictionaryfile)   #that is a function use to update the dictionary
    make_html(raw_path=Rawf_path,telemetrystatus_file=telemetrystatus_file,pic_path=pic_path,dictionary=dictionaryfile,df=emolt_df,htmlpath=htmlpath)  #make the html
    print('upload html')
    up.sd2drf_update(local_dir=htmlpath,remote_dir='/lei_aq_main/html')
    ##############################
if __name__=='__main__':
    main()

