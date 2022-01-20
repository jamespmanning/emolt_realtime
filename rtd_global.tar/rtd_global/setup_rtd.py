parameters = {'path': '/home/pi/rtd_global/',
              'sensor_type': ['Moana'],
              'time_diff_nke': 0,
              'vessel_name': 'Default_setup',
              'gear_type': 'Fixed',
              'tem_unit': 'Fahrenheit',
              'depth_unit': 'Fathoms',
              'moana_SN': '0057',
              'local_time': -5}

#14                       logger time range(minutes), set it to 5 , during the test. Set it to the shortest haul time. $
#6                        Fathom, Set to 0 for test, set to 15 after the test
#yes                      Set to 'yes', if there is a transmitter, otherwise, set to 'no'
#00:1e:c0:4d:bf:d1        Put logger Mac address in ,
#mobile                   boat type , mobile or fixed
#5                        Vessel Number
#Lisa_Ann_III             Vessel Name,
#no                       record tilt data?

metadata = {'time_range': 1,'Fathom': .1, 'transmitter': 'yes',
            'mac_addr': '00:1e:c0:4d:c4:f2', 'gear_type': 'fixed',
            'vessel_num': 5, 'vessel_name': 'Default_setup',
            'tilt': 'no'}

############################################################################
########################### OPTIONS ########################################
############################################################################

# path: use always '/home/pi/rtd_global/'
# sensor_type: 'Bluetooth'/'WiFi'/'both'
# time_diff_nke: if you have NKE sensor, difference between the sensor timestamp and UTC
# vessel_name: provided by BDC
# Lowell_SN: write the Lowell sensor MAC address
# gear_type: 'Mobile'/'Fixed'
# tem_unit: temperature unit to plot
# depth_unit: depth unit to plot
# local_time: local time to plot
