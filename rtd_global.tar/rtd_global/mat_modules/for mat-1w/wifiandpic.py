# routine to process Aquatech 530TD data
# modeled after Yacheng's "emolt_pd.py"
# where it plots the record and generates output file
#
import glob
import ftplib
import shutil
import matplotlib.pyplot as plt
import matplotlib.dates as dates
from pylab import *
import pandas as pd
from pandas import *
import time
import os
import numpy as np
from gps import *
from time import *
import threading
#from datetime import datetime
def parse(datet):
    from datetime import datetime
    dt=datetime.strptime(datet,'%Y-%m-%dT%H:%M:%S.000')
    #print type(dt)
    #dt=datetime.strptime(datet,'%m/%d/%Y %I:%M:%S %p')
    #dt=datetime.strptime(datet,'%H:%M:%S %m/%d/%Y')
    return dt

def parse2(datet):
    from datetime import datetime
    dt=datetime.strptime(datet,'%Y-%m-%dT%H:%M:%S.000')
    #dt=datetime.strptime(datet,'%m/%d/%Y %I:%M:%S %p')
    #dt=datetime.strptime(datet,'%H:%M:%S %m/%d/%Y')
    return dt    

##################################
# HARDCODE input file name and output file name
#fn='/net/data5/jmanning/aquatech/asc/Logger_sn_1724-2_data_20130531_114257_2' # where I have deleted the "units" row to make it easier
#fnout='arm0215'
#sn='1742-2'
#fn='/net/data5/jmanning/aquatech/asc/Logger_sn_1724-4_data_20130329_152208_2' # where I have deleted the "units" row to make it easier
#fnout='ata1515'
#sn='1742-4'
#tit='Marc Palombo on Georges Bank'
#######################################
#fn=event.src_path # where I have deleted the "units" row and fixed date to make it easier
#print fn

######################################
'''
Modify input file below only if you need 
'''
####################################
def create_pic():

      tit='Temperature and Angle'

      if not os.path.exists('/home/pi/Desktop/Pictures'):
        os.makedirs('/home/pi/Desktop/Pictures')


   

      if not os.path.exists('../uploaded_files'):
        os.makedirs('../uploaded_files')
      n=0  
      
      try:
            files=[]
            files.extend(sorted(glob.glob('/home/pi/Desktop/towifi/*T.txt')))
            if not os.path.exists('../uploaded_files/mypicfile.dat'):
                open('../uploaded_files/mypicfile.dat','w').close() 
            #print files  
            with open('../uploaded_files/mypicfile.dat') as f:
                content = f.readlines()   
            upfiles = [line.rstrip('\n') for line in open('../uploaded_files/mypicfile.dat')]
            open('../uploaded_files/mypicfile.dat').close()

            #f=open('../uploaded_files/myfile.dat', 'rw')
            dif_data=list(set(files)-set(upfiles))
            if dif_data==[]:
                print 'no new file was found'
                time.sleep(15)
                pass
            

    ##################################
    ##################################
            dif_data.sort(key=os.path.getmtime)
            fn=dif_data[-1]
            print 'fn: '+fn
            if 3>2:           
            
                fn2=fn.split(')')[0]+')_MA.txt'
                print fn
                print fn2
                if not os.path.exists('/home/pi/Desktop/Pictures/'+fn.split('(')[1].split('_')[0]):
                    os.makedirs('/home/pi/Desktop/Pictures/'+fn.split('(')[1].split('_')[0])
                df=pd.read_csv(fn,sep=',',skiprows=0,parse_dates={'datet':[0]},index_col='datet',date_parser=parse)#creat a new Datetimeindex
                df2=pd.read_csv(fn2,sep=',',skiprows=0,parse_dates={'datet':[0]},index_col='datet',date_parser=parse2)
                df['yd']=df.index.dayofyear+df.index.hour/24.+df.index.minute/60./24.+df.index.second/60/60./24.-1.0 #creates a yrday0 field
                df2['yd']=df2.index.dayofyear+df2.index.hour/24.+df2.index.minute/60./24.+df2.index.second/60/60./24.-1.0
                print len(df2),len(df)
                try: 
                    index_good=np.where(abs(df2['Az (g)'])<2) #Attention : If you want to use the angle, change the number under 1.
                    print index_good[0][3],index_good[0][-3]
                    index_good_start=index_good[0][3]
                    index_good_end=index_good[0][-3]
                    #print 'index_good_start:'+index_good_start+' index_good_end:'+index_good_end
                except:
                    
                    #os.remove(new_file_path+').lid')
                    #os.remove(new_file_path+')_MA.txt')
                    #os.remove(new_file_path+')_T.txt')
                    print "no good data"
                    pass
                #df.rename(index=str,columns={"Temperature (C)":"Temperature"}) #change name
                meantemp=round(np.mean(df['Temperature (C)'][index_good_start:index_good_end]),2)
                fig=plt.figure()
                ax1=fig.add_subplot(211)
                ax2=fig.add_subplot(212)
                #df['depth'].plot()
                ax2.plot(df2.index,df2['Az (g)'],'b',label='Angle')
                #ax2.plot(df2.index[index_good_start:index_good_end],df2['Az (g)'][index_good_start:index_good_end],'red',linewidth=4,label='in the water')
                ax2.legend()
                #df['temp'].plot()

                ax1.plot(df.index,df['Temperature (C)'],'b')
                #ax1.plot(df.index[index_good_start:index_good_end],df['Temperature (C)'][index_good_start:index_good_end],'red',linewidth=4,label='in the water')
                ax1.set_ylabel('Temperature (Celius)')
                ax1.legend(['temp','in the water'])
                #print 2222222222222222222222222222222222222222222
                try:    
                        if max(df.index)-min(df.index)>Timedelta('0 days 04:00:00'):
                            ax1.xaxis.set_major_locator(dates.HourLocator(interval=(max(df.index)-min(df.index)).seconds/3600/6))# for hourly plot
                            ax1.xaxis.set_major_formatter(dates.DateFormatter('%D %H:%M'))
                            ax2.xaxis.set_major_formatter(dates.DateFormatter('%D %H:%M'))
                            
                        else: 
                            ax1.xaxis.set_major_locator(dates.MinuteLocator(interval=(max(df.index)-min(df.index)).seconds/60/6))# for minutely plot
                            ax1.xaxis.set_major_formatter(dates.DateFormatter('%H:%M'))
                            ax2.xaxis.set_major_formatter(dates.DateFormatter('%H:%M'))
                except:
                    print 'too less data'

                ax1.text(0.9, 0.15, 'mean temperature in the water='+str(round(meantemp*1.8+32,1))+'F',
                            verticalalignment='bottom', horizontalalignment='right',
                            transform=ax1.transAxes,
                            color='green', fontsize=15)    
                #ax1.xaxis.set_major_formatter(dates.DateFormatter('%D %H:%M'))
                ax1.set_xlabel('')
                
                #ax1.set_ylim(int(np.nanmin(df['Temperature (C)'].values)),int(np.nanmax(df['Temperature (C)'].values)))
                ax1.set_xticklabels([])
                ax1.grid()
                ax12=ax1.twinx()
                ax12.set_title(tit)
                ax12.set_ylabel('Fahrenheit')
                ax12.set_xlabel('')
                ax12.set_xticklabels([])
                ax12.set_ylim(np.nanmin(df['Temperature (C)'].values)*1.8+32,np.nanmax(df['Temperature (C)'].values)*1.8+32)



                ax2=fig.add_subplot(212)
                #df['depth'].plot()
                ax2.plot(df2.index,df2['Az (g)'].values)
                ax2.invert_yaxis()
                ax2.set_ylabel('Angle')
                #ax2.set_xlabel(df2.index[0])
                ax2.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
                ax2.grid()
                ax2.set_ylim(-1,1)
                ax22=ax2.twinx()
                ax22.set_ylabel('Angle')
                #ax22.set_ylim(np.nanmin(df['depth'].values)/1.8288,np.nanmax(df['depth'].values)/1.8288)
                ax22.set_ylim(1,-1)
                ax22.invert_yaxis()

                #ax2.xaxis.set_minor_locator(dates.HourLocator(interval=0)
                #ax2.xaxis.set_minor_formatter(dates.DateFormatter('%H'))
                #ax2.xaxis.set_major_locator(dates.DayLocator(interval=4))
                #ax2.xaxis.set_major_formatter(dates.DateFormatter('%D %H:%M'))
                plt.gcf().autofmt_xdate()    
                ax2.set_xlabel('Local TIME '+df.index[0].strftime('%m/%d/%Y %H:%M:%S')+' - '+df.index[-1].strftime('%m/%d/%Y %H:%M:%S'))
                
                plt.savefig('/home/pi/Desktop/Pictures/'+fn.split('(')[1].split('_')[0]+'/'+fn.split('(')[0][-2:]+fn.split('(')[1][:-6]+'.png')
                plt.close()
                print 'picture is saved'
            upfiles.extend(dif_data)
            f=open('../uploaded_files/mypicfile.dat','a+')
            [f.writelines(i+'\n') for i in upfiles]
            f.close()
            print ' All Pictures are Generated'
                   
            return 
       
      except:
            print 'something wrong'
            
            return 
            
             
def wifi():
      if not os.path.exists('../uploaded_files'):
        os.makedirs('../uploaded_files')
      if 3>2:
            files=[]
            files.extend(sorted(glob.glob('/home/pi/Desktop/towifi/*')))
            #print files  
            with open('../uploaded_files/myfile.dat') as f:
                content = f.readlines()        
            upfiles = [line.rstrip('\n') for line in open('../uploaded_files/myfile.dat')]
            open('../uploaded_files/myfile.dat').close()

            #f=open('../uploaded_files/myfile.dat', 'rw')
            dif_data=list(set(files)-set(upfiles))
            if dif_data==[]:
                print 'no new file was found'
                time.sleep(15)
                pass
         
            for u in dif_data:
                import time
                #print u
                session = ftplib.FTP('216.9.9.126','huanxin','123321')
                file = open(u,'rb') 
                session.cwd("/Matdata")  
                #session.retrlines('LIST')               # file to send
                session.storbinary("STOR "+u[26:], open(u, 'r'))   # send the file
                #session.close()
                session.quit()# close file and FTP
                time.sleep(1)
                file.close() 
                print u[26:]
                #os.rename('C:/Program Files (x86)/Aquatec/AQUAtalk for AQUAlogger/DATA/'+u[:7]+'/'+u[8:], 'C:/Program Files (x86)/Aquatec/AQUAtalk for AQUAlogger/uploaded_files/'+u[8:])
                print u[26:]+' uploaded'
                #os.rename(u[:7]+'/'+u[8:], "uploaded_files/"+u[8:]) 
                time.sleep(3)                     # close file and FTP
                f=open('../uploaded_files/myfile.dat','a+')
                #print 11111111111111111111111111111
                #print 'u:'+u
                f.writelines(u+'\n')
                f.close()
                
            #upfiles.extend(dif_data)
            #f=open('../uploaded_files/myfile.dat','w')
            #[f.writelines(i+'\n') for i in upfiles]
            #f.close()
            print 'all files are uploaded'
            time.sleep(180)
            return

       
      else:
            #import time
            print 'no wifi'
            #time.sleep(10)
            
            return

def judgement(boat_type,ma_file,t_file):
    valid='no'
    try:
        df=pd.read_csv(t_file,sep=',',skiprows=0,parse_dates={'datet':[0]},index_col='datet',date_parser=parse)#creat a new Datetimeindex
        df2=pd.read_csv(ma_file,sep=',',skiprows=0,parse_dates={'datet':[0]},index_col='datet',date_parser=parse2)
        index_good=np.where(abs(df2['Az (g)'])<0.2)
        index_better=[]
        for e in range(len(index_good[0][:-1])):
                            if index_good[0][e+1]-index_good[0][e]>1:
                                index_better.append(index_good[0][e+1])
        print index_good,index_better
        if index_better==[]:
            index_better=[index_good[0][0]]

        index_good_start=index_better[-1]
        index_good_end=index_good[0][-1]+1
        print 'index_good_start:'+str(index_good_start)+' index_good_end:'+str(index_good_end)
        if boat_type=='lobster':
            if index_good_end-index_good_start<100:  #100 means 200 minutes
                print 'too less data, not in the sea'
                return valid,index_good_start,index_good_end
            else:
                valid='yes'
                return valid,index_good_start,index_good_end,
        else:
            if index_good_end-index_good_start<3:  #12 means 24 minutes
                print 'too less data, not in the sea'
                return valid,index_good_start,index_good_end 
            else:
                valid='yes'
                return valid,index_good_start,index_good_end           


    except:
        print 'data not in the sea'
        return valid,index_good_start,index_good_end

def judgement2(boat_type,ma_file,t_file):
    valid='no'
    try:
        df=pd.read_csv(t_file,sep=',',skiprows=0,parse_dates={'datet':[0]},index_col='datet',date_parser=parse)#creat a new Datetimeindex
        df2=pd.read_csv(ma_file,sep=',',skiprows=0,parse_dates={'datet':[0]},index_col='datet',date_parser=parse2)
        index_good_start=1
        index_good_end=len(df)-1
        if boat_type=='lobster':
            if len(df)<30:  #100 means 200 minutes
                print 'too less data, not in the sea'
                return valid,index_good_start,index_good_end
            else:
                valid='yes'
                return valid,index_good_start,index_good_end
        else:
            if index_good_end-index_good_start<3:  #12 means 24 minutes
                print 'too less data, not in the sea'
                return valid,index_good_start,index_good_end 
            else:
                valid='yes'
                return valid,index_good_start,index_good_end           


    except:
        print 'data not in the sea'
        return valid,index_good_start,index_good_end


 
gpsd = None #seting the global variable
 
os.system('clear') #clear the terminal (optional)
 
class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsd #bring it in scope
    gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsd
    while gpsp.running:
      gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
 






















        
