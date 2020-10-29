#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 14:32:42 2019
Original Author Lei Zhao
Feb 28,2020 Mingchao
    input local time,then change the time style in functions of raw_tele_modules for filtering the data
APR 29,2020 Mingchao
    add TimeoutError, in case upload data to student drifter have issue
May 6,2020 Mingchao
    change the function of up.sd2drf for being suitable with Windows

"""
import pandas as pd
import numpy as np
import glob
import sys
import raw_tele_modules as rdm
from datetime import datetime,timedelta
import os
#import upload_modules as up
import ftpdownload
import ftplib
import zlconversions as zl
import warnings
from pandas.core.common import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

def directory_exists(dir,ftp):
    filelist = []
    ftp.retrlines('LIST',filelist.append)
    for f in filelist:
        if f.split()[-1] == dir and f.upper().startswith('D'):
            return True
    return False

def chdir(dir,ftp): 
    '''Change directories - create if it doesn't exist'''
    if directory_exists(dir,ftp) is False: # (or negate, whatever you prefer for readability)
        ftp.mkd(dir)
        print(dir)
    ftp.cwd(dir)
def ftp_upload(localfile, remotefile,ftp):
  fp = open(localfile, 'rb')
  ftp.storbinary('STOR %s' % os.path.basename(localfile), fp, 1024)
  fp.close()
  print ("after upload " + localfile + " to " + remotefile)
  
def mkds(dir,ftp):
    dir_list=dir.split('/')
    for i in range(len(dir_list)):
        if len(dir_list[i])==0:
            continue
        else:
            chdir(dir_list[i],ftp)        
def list_ftp_allfiles(rootdir,ftp):
    """get all files' path and name in rootdirectory"""
    ftp.cwd('/')
    ftp.cwd(rootdir)
    list = ftp.nlst()
    _files = []
    for i in range(len(list)):
        try:
            #path=os.path.join(rootdir,list[i])
            path=rootdir+'/'+list[i]
            _files.extend(list_ftp_allfiles(path,ftp))
        except ftplib.error_perm:
            #path=os.path.join(rootdir,list[i])
            path=rootdir+'/'+list[i]
            _files.append(path)
    return _files

def sd2drf(local_dir,remote_dir,filetype='png',keepfolder=False):
    '''function: Upload all files under one folder (including all files under subfolders) to the specified folder 
    input:
        local_dir: local directory
        remote_dir: remote directory,the folder in the student drifters'''
    
    #if local_dir[0]!='/':
        #local_dir='/'+local_dir
#    if remote_dir[0]!='/':
#        remote_dir='/'+remote_dir
    cdflist=zl.list_all_files(local_dir)
    files=[]
    if filetype=='**':
        files=cdflist
    else:    
        for file in cdflist:
            if file.split('.')[1] in filetype:
                files.append(file)
    ftp=ftplib.FTP('66.114.154.52','huanxin','123321')
    drifterlist=list_ftp_allfiles(remote_dir,ftp)
    drflist=[]
    if keepfolder:#keep subdirectory
        for i in range(len(drifterlist)):
            #drflist.append(drifterlist[i].replace(remote_dir,local_dir))
            drflist.append(drifterlist[i].replace(remote_dir,local_dir).replace('/','\\'))
        upflist=list(set(files)-set(drflist))
        print(len(upflist))
        ftp.quit()
        if len(upflist)==0:
            return 0
        for file in upflist:
            ftp=ftplib.FTP('66.114.154.52','huanxin','123321')
            fpath,fname=os.path.split(file)
            #remote_dir_file=file.replace(local_dir,remote_dir)
            #dir=fpath.replace(local_dir,remote_dir).replace('//','/')
            remote_dir_file=file.replace(local_dir,remote_dir).replace('\\','/')
            dir=fpath.replace(local_dir,remote_dir).replace('\\','/')
            mkds(dir,ftp)
            ftp_upload(file,remote_dir_file,ftp)
            ftp.quit() 
    else:  #just upload files,cancel subfolder
        for file in drifterlist:
            fpath,fname=os.path.split(file)
            drflist.append(fname)
     
        upflist=[]
        for file in files:
            fpath,fname=os.path.split(file)
            if fname not in drflist:
                upflist.append(file)      
        print('the number of upload files:'+str(len(upflist)))
        ftp.quit()
        if len(upflist)==0:
            return 0
        for file in upflist:
            ftp=ftplib.FTP('66.114.154.52','huanxin','123321')
            fpath,fname=os.path.split(file)
            remote_dir_file=file.replace(fpath,remote_dir)
            dir=remote_dir   
            mkds(dir,ftp)
            ftp_upload(file,remote_dir_file,ftp)
            ftp.quit()  
def week_start_end(dtime,interval=0):
    '''input a time, 
    if the interval is 0, return this week monday 0:00:00 and next week monday 0:00:00
    if the interval is 1,return  last week monday 0:00:00 and this week monday 0:00:00'''
    delta=dtime-datetime(2003,1,1,0,0)-timedelta(weeks=interval)
    count=int(delta/timedelta(weeks=1))
    start_time=datetime(2003,1,1,0,0)+timedelta(weeks=count)
    end_time=datetime(2003,1,1,0,0)+timedelta(weeks=count+1)   
    return start_time,end_time 
def classify_by_boat(indir,outdir,pstatus):
    """
    indir: input directory, that is the path of read data
    outdir: output directory, that is that path of save data
    pstatus: telemetry_status file
    function:
        accroding the lowell_sn and time to find the file belong to which veseel, and the same vessel produces files put in the same folder.
    notice:this code is suitable for matching data after 2000
    """
    if not os.path.exists(outdir):
        os.makedirs(outdir)
#    if os.listdir(output_dir):
#        print ('please input a empty directory!')
#        sys.exit()
    #read the file of the telementry_status
    df=rdm.read_telemetrystatus(pstatus)
    #fix the format of time about logger_change
    for i in df.index:
        if df['logger_change'].isnull()[i]:
            continue
        else:
            date_logger_change=df['logger_change'][i].split(',')   #get the time data of the logger_change
            for j in range(0,len(date_logger_change)):
                if len(date_logger_change[j])>4:     #keep the date have the month and year such as 1/17
                    date_logger_change[j]=zl.transform_date(date_logger_change[j]) #use the transform_date(date) to fix the date
            df['logger_change'][i]=date_logger_change
    #get the path and name of the files
    file_lists=glob.glob(os.path.join(indir,'*.csv'))
    #classify the file        
    for file in file_lists:
        #time conversion, GMT time to local time
        #time_str=file.split('/')[len(file.split('/'))-1:][0].split('.')[0].split('_')[2]+' '+file.split('/')[len(file.split('/'))-1:][0].split('.')[0].split('_')[3]
        time_str=file.split('\\')[len(file.split('\\'))-1:][0].split('.')[0].split('_')[2]+' '+file.split('\\')[len(file.split('\\'))-1:][0].split('.')[0].split('_')[3]
        time_local=zl.gmt_to_eastern(time_str[0:4]+'-'+time_str[4:6]+'-'+time_str[6:8]+' '+time_str[9:11]+':'+time_str[11:13]+':'+time_str[13:15]).strftime("%Y%m%d")
        #match the SN and date
        for i in range(len(df)):
            if df['Lowell-SN'].isnull()[i] or df['logger_change'].isnull()[i]:  #we will enter the next line if SN or date is not exist 
                continue
            else:
                for j in range(len(df['Lowell-SN'][i].split(','))):   
                    #fname_len_SN=len(file.split('/')[len(file.split('/'))-1:][0].split('_')[1]) #the length of SN in the file name
                    fname_len_SN=len(file.split('\\')[len(file.split('\\'))-1:][0].split('_')[1])
                    len_SN=len(df['Lowell-SN'][i].split(',')[j]) #the length of SN in the culumn of the Lowell-SN inthe file of the telemetry_status.csv
                    if df['Lowell-SN'][i].split(',')[j][len_SN-fname_len_SN:]==file.split('\\')[len(file.split('\\'))-1:][0].split('_')[1]:
                    #if df['Lowell-SN'][i].split(',')[j][len_SN-fname_len_SN:]==file.split('/')[len(file.split('/'))-1:][0].split('_')[1]:
                        fpath,fname=os.path.split(file)    #seperate the path and name of the file
                        #dstfile=(fpath).replace(indir,outdir+'/'+df['Boat'][i]+'/'+fname.split('_')[2][:6]+'/'+fname) #produce the path+filename of the destination
                        dstfile=(fpath).replace(indir,outdir+'\\'+df['Boat'][i]+'\\'+fname.split('_')[2][:6]+'\\'+fname)
                        #dstfile=dstfile.replace('//','/').replace(' ','_')
                        dstfile=dstfile.replace('//','\\').replace(' ','_')
                        
                        try:#copy the file to the destination folder
                            if j<len(df['logger_change'][i])-1:
                                if df['logger_change'][i][j]<=time_local<=df['logger_change'][i][j+1]:
                                    zl.copyfile(file,dstfile)  
                            else:
                                if df['logger_change'][i][j]<=time_local:
                                    zl.copyfile(file,dstfile) 
                        except KeyboardInterrupt:
                            sys.exit()
                        except:
                            print('NOTE: '+fname+' does not have all the info it needs like date of last change.')
                            print("Please check telemetry status for this probe.")

def check_reformat_data(indir,outdir,startt,endt,pstatus,lack_data,rdnf,LSN2='7a',similarity=0.7,mindepth=10,min_minutes=timedelta(minutes=10),percentage_acceptable=0.25):
    """
    input:
        indir:input directory
        LSN2: the first two letters in lowell_sn, for example:Lowell_SN is '7a4c', the LSN2 is '7a', the default value of LSN2 is '7a' 
        rdnf: In this file include the VP_NUM HULL_NUM and VESSEL_NAME 
        check:vessel name,vessel number,serial number, lat,lon
        add VP_NUM
    function:
        fix the format of value, below is the right format
        the header like this:
            Probe Type	Lowell
            Serial Number	c572
            Vessel Number	28
            VP_NUM	310473
            Vessel Name	Dawn_T
            Date Format	YYYY-MM-DD
            Time Format	HH24:MI:SS
            Temperature	C
            Depth	m
        the value like this:
            HEADING	Datet(GMT)	Lat	Lon	Temperature(C)	Depth(m)
            DATA 	2019-03-30 10:37:00	4002.1266	7006.9986 7.71	 0.79
            DATA 	2019-03-30 10:38:30	4002.1289	7006.9934 7.76	 24.2
            DATA 	2019-03-30 10:40:00	4002.1277	7006.9933 7.79	 1.20
        the depth must make sure have some value bigger than mindepth(this is a parameter, the default value is 10)
        if all of depth value is bigger than mindepth, output the logger have some issue
    """
    #Read telemetry status file and raw data name file
    telemetrystatus_df=rdm.read_telemetrystatus(pstatus)
    raw_data_name_df=pd.read_csv(rdnf,sep='\t') 
    #produce a dataframe that use to calculate the number of files
    total_df=pd.concat([telemetrystatus_df.loc[:,['Boat']][:],pd.DataFrame(data=[['Total']],columns=['Boat'])],ignore_index=True)
    total_df.insert(1,'file_total',0)
    total_df['Boat']=total_df['Boat'].map(lambda x: x.replace(' ','_'))
    #get all the files under the input folder and screen out the file of '.csv',and put the path+name in the allfile_lists
    allfile_lists=zl.list_all_files(indir)
    file_lists=[]
    for file in allfile_lists:
        fpath,fname=os.path.split(file)  #get the file's path and name
        time_str=fname.split('.')[0].split('_')[2]+' '+fname.split('.')[0].split('_')[3]
        time_gmt=datetime.strptime(time_str,"%Y%m%d %H%M%S")
        #time_local=zl.utc2local(time_gmt)#UTC time to local time
        if file[len(file)-4:]=='.csv':
            if startt<=time_gmt<=endt:
                file_lists.append(file)
    #start check the data and save in the output_dir
    for file in file_lists:
        fpath,fname=os.path.split(file)  #get the file's path and name
        #fix the file name
        #fname=file.split('/')[len(file.split('/'))-1]
        fname=file.split('\\')[len(file.split('\\'))-1]
        if len(fname.split('_')[1])==2:# if the serieal number is only 2 digits make it 4
            new_fname=fname[:3]+LSN2+fname[3:]
        else:
            new_fname=fname
        #read header and data
        try:
            df_head=zl.nrows_len_to(file,2,name=['key','value'])
            df=zl.skip_len_to(file,2) #data
        except KeyboardInterrupt:
            sys.exit()
        except:
            print("worthless file:"+file)
            continue
        #vessel_name=fpath.split('/')[-2:-1][0] #get the vessel name
        vessel_name=fpath.split('\\')[-2:-1][0]
        #check the format of the data
        if len(df.iloc[0])==5: # some files absent the "DATA" in the first column
            df.insert(0,'HEADING','DATA')
        df.columns = ['HEADING','Datet(GMT)','Lat','Lon','Temperature(C)','Depth(m)']  #rename the name of conlum of data
        df['Depth(m)'] = df['Depth(m)'].map(lambda x: '{0:.2f}'.format(float(x)))  #keep two decimal fraction
        #Jim&Mingchao 10,Mar,2020 filter the values that constant in >5 records
        dfs = df['Depth(m)'].map(lambda x: float(x))#change type of str to float
        diffs = np.diff(dfs)
        u,c = np.unique(diffs,return_counts=True)
        if len(c[np.where(u==0)]) > len(df)*percentage_acceptable: #JiM added the len() around the first part Sep 2020 & corrected spelling
            #print('pressure problem:'+file)
            print('NOTE: pressure problem in '+fname+' from '+vessel_name)# JiM cleaned up these messages Sep 2020
            rdm.Write_Text(lack_data,file,reason='pressure problem')
            continue
        #Jim&Mingchao 10,Mar,2020 filter the values not enough min minutes
        dts=pd.to_datetime(df['Datet(GMT)'])
        total_diffs=dts[len(dts)-1]-dts[0]
        if total_diffs < min_minutes:
            #print('bad data! time not more than 10 minutes:'+file)
            print('NOTE: Haul less than 10 minutes for '+fname+' from '+vessel_name)# JiM cleaned up these messages Sep 2020)
            rdm.Write_Text(lack_data,file,reason='bad data! time not more than 10 minutes')#record the name of file exists problem
            continue
        datacheck,count=1,0
        for i in range(len(df)):  #the value of count is 0 if the data is test data
            count=count+(float(df['Depth(m)'][i])>mindepth)# keep track of # of depths>mindepth
            if count>5:
                if count==i+1:
                    print('please change the file:'+file+' make sure the logger is work well!' )
                    datacheck=0
                break
        if datacheck==0:
            print(vessel_name+':logger have issue:'+file)
            rdm.Write_Text(lack_data,file,reason='logger have issue')#record the name of file exists problem
            continue
        if count==0: #if the file is test file,print it
            print ("test file:"+file)
            rdm.Write_Text(lack_data,file,reason="test file")
            continue
        try:
            df['Temperature(C)'] = df['Temperature(C)'].map(lambda x: '{0:.2f}'.format(float(x))) #keep two decimal fraction
        #keep the lat and lon data format is right,such as 00000.0000w to 0000.0000
            df['Lon'] = df['Lon'].map(lambda x: '{0:.4f}'.format(float(rdm.format_lat_lon(x))))
            df['Lat'] = df['Lat'].map(lambda x: '{0:.4f}'.format(float(rdm.format_lat_lon(x))))#keep four decimal fraction
        except:
            rdm.Write_Text(lack_data,file,reason='data is not enough')
            continue
        #Check if the header file contains all the information, and if it is wrong, fix it.
        for j in range(len(df_head)):#check and fix the vessel number 
            if df_head['key'][j].lower()=='Vessel Number'.lower():
                for i in range(len(telemetrystatus_df)):
                    if telemetrystatus_df['Boat'][i].lower()==vessel_name.lower():
                        df_head['value'][j]=str(telemetrystatus_df['Vessel#'][i])
                        break
                break
        header_file_fixed_key=['Date Format','Time Format','Temperature','Depth'] 
        header_file_fixed_value=['YYYY-MM-DD','HH24:MI:SS','C','m']
        EXIST,loc=0,0
        for fixed_t in header_file_fixed_key:
            for k in range(len(df_head['key'])):
                if fixed_t.lower()==df_head['key'][k].lower():
                    break
                else:
                    EXIST=1
                    count=k+1
            if EXIST==1:
                df_head=pd.concat([df_head[:count],pd.DataFrame(data=[[fixed_t,header_file_fixed_value[loc]]],columns=['key','value'])],ignore_index=True)
            loc+=1 
        for i in range(len(total_df)):#caculate the number of every vessel and boat files
            if total_df['Boat'][i].lower()==vessel_name.lower():
                total_df['file_total'][i]=total_df['file_total'][i]+1
        #if the vessel name and serial number are exist, find the location of them 
        vessel_name_EXIST,S_number_EXIST=0,0
        for k in df_head.index:           
            if df_head['key'][k].lower()=='Vessel Name'.lower():
                vessel_name_EXIST=1
                df_head['value'][k]=vessel_name
            if df_head['key'][k].lower()=='Serial Number'.lower():
                df_head['value'][k]=df_head['value'][k].replace(':','')
                S_number_EXIST=1
        #check and fix the vessel name and serial number 
        if S_number_EXIST==0:
            df_head=pd.concat([df_head[:1],pd.DataFrame(data=[['Serial Number',new_fname.split('_')[1]]],columns=['key','value']),df_head[1:]],ignore_index=True)
        if vessel_name_EXIST==0:#
            df_head=pd.concat([df_head[:2],pd.DataFrame(data=[['Vessel Name',vessel_name]],columns=['key','value']),df_head[2:]],ignore_index=True)
        for i in df_head.index:
            if df_head['key'][i].lower()=='Vessel Number'.lower():
                loc_vp_header=i+1
                break
        for i in raw_data_name_df.index:
            ratio=zl.str_similarity_ratio(vessel_name.lower(),raw_data_name_df['VESSEL_NAME'][i].lower())
            ratio_best=0
            if ratio>similarity:
                if ratio>ratio_best:
                    ratio_best=ratio
                    loc_vp_file=i
        df_head=pd.concat([df_head[:loc_vp_header],pd.DataFrame(data=[['VP_NUM',raw_data_name_df['VP_NUM'][loc_vp_file]]],\
                           columns=['key','value']),df_head[loc_vp_header:]],ignore_index=True)
        #creat the path and name of the new_file and the temperature file  
        output_path=fpath.replace(indir,outdir)
        if not os.path.exists(output_path):   #check the path of the save file is exist,make it if not
            os.makedirs(output_path)
        #df_head.to_csv(output_path+'/'+new_fname,index=0,header=0)
        df_head.to_csv(output_path+'\\'+new_fname,index=0,header=0)
        df.to_csv(output_path+'\\df_tem.csv',index=0)  #produce the temperature file  
        #add the two file in one file and delet the temperature file
        #os.system('cat '+output_path+'\\df_tem.csv'+' >> '+output_path+'\\'+new_fname)
        os.system('type '+output_path+'\\df_tem.csv'+' >> '+output_path+'\\'+new_fname)
        os.remove(output_path+'\\df_tem.csv')
#    #caculate the total of all files and print save as a file.
    try:
        for i in range(len(total_df)-1):
            total_df['file_total'][len(total_df)-1]=total_df['file_total'][len(total_df)-1]+total_df['file_total'][i]
        total_df.to_csv(outdir+'\\items_number.txt',index=0)
    except KeyboardInterrupt:
        sys.exit()
    except:
        print("no valuable file!")
                            
def main():
    # realpath=os.path.dirname(os.path.abspath(__file__))
    realpath='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\py'
    parameterpath=realpath.replace('py','parameter')
    #HARDCODING
    raw_data_name_file=os.path.join(parameterpath,'raw_data_name.txt')  #this data conclude the VP_NUM HULL_NUM VESSEL_NAME
    #raw_data_name_file='E:/programe/raw_data_match/parameter/raw_data_name.txt'
    output_path=realpath.replace('py','result')  #use to save the data 
    #telemetry_status=os.path.join(parameterpath,'telemetry_status.csv')
    telemetry_status='C:\\Weekly_Project\\Weekly_Project\\programe\\aqmain\\parameter\\telemetry_status.csv'
    lack_data_path=os.path.join(output_path, 'lack_data.txt')
    #lack_data_path='E:/programe/raw_data_match/result/lack_data.txt'#store the name of file that lacked data after 'classfy finished'
    # below hardcodes is the informations to upload local data to student drifter. 
    subdir=['Matdata','checked']
    mremote='/Raw_Data'
    #mremote='\Raw_Data'
    remote_subdir=['Matdata','checked']
    ###########################
    end_time=datetime.utcnow()
    #start_time,end_time=week_start_end(end_time,interval=1)
    start_time=end_time-timedelta(weeks=2)
    #download raw data from website
    files=ftpdownload.download(localpath='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\result\\Matdata', ftppath='/Matdata')
    #classify the file by every boats
    #rdm.classify_by_boat(indir='E:\\programe\\raw_data_match\\result\\Matdata',outdir='E:\\programe\\raw_data_match\\result\\classified',pstatus=telemetry_status)
    classify_by_boat(indir='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\result\\Matdata',outdir=r'C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\result\\classified',pstatus=telemetry_status)
    print('classfy finished!')
    #check the reformat of every file:include header,heading,lat,lon,depth,temperature.
    check_reformat_data(indir='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\result\\classified',outdir='C:\\Weekly_Project\\Weekly_Project\\programe\\raw_data_match\\result\\checked',startt=start_time,\
                        endt=end_time,pstatus=telemetry_status,rdnf=raw_data_name_file,lack_data=lack_data_path)
    print('check format finished!')
    for i in range(len(subdir)):
        local_dir=os.path.join(output_path,subdir[i])
        #remote_dir=os.path.join(mremote,remote_subdir[i])
        remote_dir=os.path.join(mremote,remote_subdir[i]).replace('\\', '/')
        #up.sd2drf(local_dir,remote_dir,filetype='csv',keepfolder=True)
        try:
            sd2drf(local_dir, remote_dir, filetype='csv', keepfolder=True)
        except TimeoutError:
            print('Timeout Error')
if __name__=='__main__':
    main()