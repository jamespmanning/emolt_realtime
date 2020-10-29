#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 18 12:41:35 2018
@author: leizhao

funtion, contact the raw_data_download.py,classify_by_boat.py
check_reformat_data.py and match_tele_raw.py
finally: output the plot and statistics every week

Mar 3,2020 Mingchao
    1.append emolt_no_telemetry every week
    2.the telemetry data have wrong lat and lon,but raw data have right lat and lon,we will compare them and put right raw data in emolt_no_telemetry
Apr 24,2020 Mingchao
    1.Add emolt_no_telemetry.drop_duplicates(subset=['vessel','lat','lon'], keep='first') to filter the same data in emolt_no_telemetry,save the first one.
    2.Combine emolt_QCed with emolt_no_telemetry
May 01,2020 Mingchao
    upload emolt_no_telemetry.csv,emolt_QCed_df and statisrics.csv to student drifter
May 07,2020 Mingchao
    simplify this code and add a function get a dataframe include only good data of emolt_QCed.csv and emolt_no_telemetry.csv together
Sep 02,2020 JiM
    modified the "weekly_times" function to speed things up


"""

import ftplib
import os
import pandas as pd
import warnings
from pandas.core.common import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
import numpy as np
from datetime import datetime,timedelta
import raw_tele_modules as rdm
import netCDF4

def dd2dm(lat,lon):
    """
    convert lat, lon from decimal degrees to degrees,minutes
    """
    lat_d=int(abs(lat))                #calculate latitude degrees
    lat_m=(abs(lat) - lat_d) * 60. #calculate latitude minutes
    lon_d=int(abs(lon))
    lon_m=(abs(lon) - lon_d) * 60.
    la=lat_d*100.+lat_m
    lo=lon_d*100.+lon_m
    return la,lo

def gps_compare_JiM(lat,lon,harbor_range): #check to see if the boat is in the harbor derived from Huanxin's "wifipc.py" functions   
    # function returns yes if this position is with "harbor_range" miles of a dock
    #file='/home/jmanning/py/harborlist.txt'
    file='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\parameter\\harborlist.txt'
    df=pd.read_csv(file,sep=',')
    [la,lo]=dd2dm(lat,lon) # converted decimal degrees to degrees minutes
    indice_lat=[i for i ,v in enumerate(abs(np.array(df['lat'])-la)<harbor_range) if v]
    indice_lon=[i for i ,v in enumerate(abs(np.array(df['lon'])-lo)<harbor_range) if v]
    harbor_point_list=[i for i, j in zip(indice_lat,indice_lon) if i==j]
    if len(harbor_point_list)>0:
       near_harbor='yes'
    else:
       near_harbor='no'
    return near_harbor #yeas or no

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

def get_depth(nc,lon,lat,loni,lati,mindist_allowed):
    # routine to get depth (meters) using vol1 from NGDC
    #url='https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol1.nc'
    #nc=netCDF4.Dataset(url).variables 
    #lon=nc['x'][:]
    #lat=nc['y'][:]
    xi,yi,min_dist=nearlonlat_zl(lon,lat,loni,lati) 
    if min_dist>mindist_allowed:
      depth=np.nan
    else:
      depth=nc['z'][yi,xi].data
    return float(depth)#,min_dist

def dfgood(emolt_QCed_path, depth_ok, min_miles_from_dock, temp_ok, fraction_depth_error, mindist_allowed, emolt_no_telemetry):
    '''get a dataframe include only good data of emolt_QCed.csv and emolt_no_telemetry.csv together'''
    emolt_QCed=pd.read_csv(emolt_QCed_path,index_col=0)
    emolt_QCed_df=emolt_QCed[emolt_QCed['flag']==0]
    emolt_QCed_df.index=range(len(emolt_QCed_df))
    emolt_no_telemetry.index=range(len(emolt_no_telemetry))
    flag=[]
    url='https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol1.nc'
    try:
        nc=netCDF4.Dataset(url).variables 
        lon=nc['x'][:]
        lat=nc['y'][:]
        emolt_no_telemetry['datet']=pd.to_datetime(emolt_no_telemetry['datet'])
        for k in range(len(emolt_no_telemetry)):
            depth_ngdc=get_depth(nc,lon,lat,emolt_no_telemetry['lon'][k],emolt_no_telemetry['lat'][k],mindist_allowed)
            if gps_compare_JiM(emolt_no_telemetry['lat'][k],emolt_no_telemetry['lon'][k],min_miles_from_dock)=='yes': # this means it is near a dock
                flag.append(1)
            elif (float(emolt_no_telemetry['mean_temp'][k])<temp_ok[0]) or (float(emolt_no_telemetry['mean_temp'][k])>temp_ok[1]):
            #elif (emolt_no_telemetry['mean_temp'][k]<temp_ok[0]) or (emolt_no_telemetry['mean_temp'][k]>temp_ok[1]):
                flag.append(2)
            elif (emolt_no_telemetry['depth'][k]<depth_ok[0]) or (emolt_no_telemetry['depth'][k]>depth_ok[1]):
                flag.append(3)
            elif abs(emolt_no_telemetry['depth'][k]-depth_ngdc)/depth_ngdc>fraction_depth_error:
                flag.append(4)
            else:
                flag.append(0)# good data
    except:#can not connect 'https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol1.nc'
        emolt_no_telemetry['datet']=pd.to_datetime(emolt_no_telemetry['datet'])
        for k in range(len(emolt_no_telemetry)):
            if gps_compare_JiM(emolt_no_telemetry['lat'][k],emolt_no_telemetry['lon'][k],min_miles_from_dock)=='yes': # this means it is near a dock
                flag.append(1)
            elif (float(emolt_no_telemetry['mean_temp'][k])<temp_ok[0]) or (float(emolt_no_telemetry['mean_temp'][k])>temp_ok[1]):
            #elif (emolt_no_telemetry['mean_temp'][k]<temp_ok[0]) or (emolt_no_telemetry['mean_temp'][k]>temp_ok[1]):
                flag.append(2)
            elif (emolt_no_telemetry['depth'][k]<depth_ok[0]) or (emolt_no_telemetry['depth'][k]>depth_ok[1]):
                flag.append(3)
            else:
                flag.append(0)# good data
    emolt_no_telemetry['flag']=flag
    df = emolt_QCed_df.append(emolt_no_telemetry)
    dfnew=df[['vessel','datet','lat','lon','depth','depth_range','hours','mean_temp','std_temp','flag']]    ##dfnew.to_csv('/net/pubweb_html/drifter/emolt_QCed.csv')
    dfgood = dfnew[dfnew['flag']==0] # restrict to good data only
    dfgood['datet'] = pd.to_datetime(dfgood['datet'])
    dfgood = dfgood.sort_values(by=['datet'])
    dfgood.index = range(len(dfgood))
    return dfgood

def upload_weely(Host, UserName, Pswd,remot_dir, local_folder):
    '''upload weekly result to student drifter'''
    ftp = ftplib.FTP(Host)
    ftp.login(UserName, Pswd)
    ftp.cwd(remot_dir)
    local_list = os.listdir(local_folder)
    for i in range(len(local_list)):
        command = 'STOR '+local_list[i]
        sendFILEName = local_folder+local_list[i]
        ftp.storbinary(command, open(sendFILEName,'rb'))
        print('upload '+local_list[i])
    ftp.quit()
    
def get_emolt_no_telemetry(path, emolt_raw_path, emolt_QCed_df_save):
    '''compare emolt.dat and emolt_raw,get emolt_no_telemetry'''
    tele_df=rdm.read_telemetry(path)#get emolt.dat
    tele_df=tele_df[0:-2]
    emolt_raw_df=pd.read_csv(emolt_raw_path,index_col=0)#get emolt_raw.csv
    #create a DataFrame for store emolt_no_telemetry
    emolt_no_telemetry_DF=pd.DataFrame(data=None,columns=['vessel','datet','lat','lon','depth','depth_range','hours','mean_temp','std_temp'])
    #compare with emolt_raw.csv and emolt.dat to get emolt_no_telemetry.csv
    emolt_no_telemetry_result=rdm.emolt_no_telemetry_df(tele_df=tele_df,emolt_raw_df=emolt_raw_df,emolt_no_telemetry_df=emolt_no_telemetry_DF)
    #according to columns,drop_duplicates
    emolt_no_telemetry_result=emolt_no_telemetry_result.drop_duplicates(['vessel','lat','lon'])
    #get the rest of emolt_raw_df,it's emolt_no_telemetry
    emolt_no_telemetry_result=rdm.subtract(df1=emolt_raw_df,df2=emolt_no_telemetry_result,columns=['vessel','datet','lat','lon','depth','depth_range','hours','mean_temp','std_temp'])
    emolt_no_telemetry_result['std_temp'] = emolt_no_telemetry_result['std_temp'].map(lambda x: '{0:.2f}'.format(float(x)/100))
    emolt_no_telemetry_result['mean_temp'] = emolt_no_telemetry_result['mean_temp'].map(lambda x: '{0:.2f}'.format(float(x)/100))
    #save emolt_no_telemetry.csv
    if not os.path.exists(emolt_QCed_df_save):
        os.makedirs(emolt_QCed_df_save)
    #append every week
    emolt_no_telemetry=pd.read_csv(os.path.join(emolt_QCed_df_save,'emolt_no_telemetry.csv'),index_col=0)
    emolt_no_telemetry=emolt_no_telemetry.append(emolt_no_telemetry_result)
    emolt_no_telemetry=emolt_no_telemetry.drop_duplicates(subset=['vessel','lat','lon'], keep='first')
    emolt_no_telemetry=emolt_no_telemetry.sort_values(by=['datet'])
    emolt_no_telemetry.index=range(len(emolt_no_telemetry))
    return emolt_no_telemetry
def main():
    ############################################## Hardcodes ###############################
    Host = '66.114.154.52'
    UserName = 'huanxin'
    Pswd = '123321'
    remot_dir = '/mingchao_weekly'
    local_folder = 'E:\\Mingchao\\result\\mingchao_weekly\\'
    min_miles_from_dock=2 # minimum miles from a dock position to be considered ok (this is not actual miles but minutes of degrees)
    temp_ok=[0,30]    # acceptable range of mean temps
    depth_ok=[10,500] # acceptable range of mean depths (meters)
    fraction_depth_error=0.15 # acceptable difference of observed bottom vs NGDC
    mindist_allowed=0.4 # minimum distance from nearest NGDC depth in km 
    realpath=os.path.dirname(os.path.abspath(__file__))
    #realpath='E:/programe/raw_data_match/py'
    #parameterpath=realpath.replace('py','parameter')
    output_path=realpath.replace('py','result')  #use to save the data 
    picture_save=output_path+'\\stats\\' #use to save the picture
    # emolt='https://www.nefsc.noaa.gov/drifter/emolt.dat' #this is download from https://www.nefsc.noaa.gov/drifter/emolt.dat, 
    # emolt = 'https://apps-nefsc.fisheries.noaa.gov/drifter/emolt.dat'
    emolt = 'https://nefsc.noaa.gov/drifter/emolt_ap3.dat'
    #telemetry_status=os.path.join(parameterpath,'telemetry_status.csv')
    #telemetry_status='/home/jmanning/Mingchao/parameter/telemetry_status.csv'
    telemetry_status='C:\\Weekly_Project\\Weekly_Project\\programe\\aqmain\\parameter\\telemetry_status.csv'
    emolt_raw_save='C:\\Weekly_Project\\Weekly_Project\\Mingchao\\result'#output emolt_raw.csv
    emolt_raw_path='C:\\Weekly_Project\\Weekly_Project\\Mingchao\\result\\emolt_raw.csv'#input emolt_raw.csv 
    #path='https://apps-nefsc.fisheries.noaa.gov/drifter/emolt.dat'#input emolt.dat
    path='https://nefsc.noaa.gov/drifter/emolt.dat' # JiM switch back to this when the apps version was empty on 24 Sep 2020
    lack_data_path='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\result\\lack_data.txt'
    # emolt_QCed_path = 'https://www.nefsc.noaa.gov/drifter/emolt_QCed.csv'
    emolt_QCed_path = 'https://apps-nefsc.fisheries.noaa.gov/drifter/emolt_QCed.csv'
    emolt_QCed_df_save = 'C:\\Weekly_Project\\Weekly_Project\\Mingchao\\result\\mingchao_weekly'
    # below hardcodes is the informations to upload local data to student drifter. 
#    subdir=['stats']    
#    mremote='/Raw_Data'
#    remote_subdir=['stats']
    end_time=datetime.now()-timedelta(days=1)#input local time,in match_tele_raw will change to UTCtime
    start_time=end_time-timedelta(weeks=1)
    ############################################## Main #####################################
    if not os.path.exists(picture_save):
        os.makedirs(picture_save)
    print('match telemetered and raw data!')
    #match the telementry data with raw data, calculate the numbers of successful matched and the differnces of two data. finally , use the picture to show the result.
    dict=rdm.match_tele_raw(os.path.join(output_path,'checked'),path_save=os.path.join(picture_save,'statistics'),telemetry_path=emolt,telemetry_status=telemetry_status,\
                            emolt_raw_save=emolt_raw_save,start_time=start_time,end_time=end_time,dpi=500,lack_data=lack_data_path,emolt_QCed_df_save=emolt_QCed_df_save)
    print('finished match_tele_raw')
    emolt_no_telemetry_df=get_emolt_no_telemetry(path, emolt_raw_path, emolt_QCed_df_save)
    print('finished get_emolt_no_telemetry')
    emolt_no_telemetry_df.to_csv(os.path.join(emolt_QCed_df_save,'emolt_no_telemetry.csv'))
    df_good=dfgood(emolt_QCed_path, depth_ok, min_miles_from_dock, temp_ok, fraction_depth_error, mindist_allowed, emolt_no_telemetry=emolt_no_telemetry_df)
    print('finished dfgood')
#    df_good.to_csv(os.path.join(emolt_QCed_df_save,'emolt_QCed_no_telemetry.csv'))
    df_good.to_csv(os.path.join(emolt_QCed_df_save,'emolt_QCed_telemetry_and_wified.csv'))
    #tele_dict=dict['tele_dict']
    #raw_dict=dict['raw_dict']
    #record_file_df=dict['record_file_df']
    #index=tele_dict.keys()
    print('match telemetered and raw data finished!')
    #print("start draw map")
    #upload_weely(Host, UserName, Pswd,remot_dir, local_folder)
    
'''
    raw_d=pd.DataFrame(data=None,columns=['time','filename','mean_temp','mean_depth','mean_lat','mean_lon'])
    tele_d=pd.DataFrame(data=None,columns=['time','mean_temp','mean_depth','mean_lat','mean_lon'])
    for i in index:
        for j in range(len(record_file_df)): #find the location of data of this boat in record file
            if i.lower()==record_file_df['Boat'][j].lower():
                break
        if len(raw_dict[i])==0 and len(tele_dict[i])==0:
            continue
        else:
            raw_d=raw_d.append(raw_dict[i])
            tele_d=tele_d.append(tele_dict[i])
            rdm.draw_map(raw_dict[i],tele_dict[i],i,start_time,end_time,picture_save,dpi=300)
            rdm.draw_time_series_plot(raw_dict[i],tele_dict[i],i,start_time,end_time,picture_save,record_file_df.iloc[j],dpi=300)
    raw_d.index=range(len(raw_d))
    tele_d.index=range(len(tele_d))
    rdm.draw_map(raw_d,tele_d,'all_map',start_time,end_time,picture_save,dpi=300)

    for i in range(len(subdir)):
        local_dir=os.path.join(output_path,subdir[i])
        remote_dir=os.path.join(mremote,remote_subdir[i])
        #up.sd2drf(local_dir,remote_dir,keepfolder=True)  # need to keep subdirectry
        up.sd2drf(local_dir, remote_dir.replace('\\', '/'), keepfolder=True)
'''
if __name__=='__main__':
    main()