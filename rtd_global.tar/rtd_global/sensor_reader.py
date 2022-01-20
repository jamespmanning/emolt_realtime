import sys

sys.path.insert(1, '/home/pi/rtd_global/mat_modules')
import odlw_facade
import odlw
import bluepy.btle as btle
import time
from datetime import datetime
import os
import logging
from li_parse import parse_li
import setup_rtd

logger_timerange_lim = int(int(setup_rtd.metadata['time_range'] / 1.5))
logger_pressure_lim = int(setup_rtd.metadata['Fathom']) * 1.8288  # convert from fathom to meter
transmit = setup_rtd.metadata['transmitter']
MAC_FILTER = setup_rtd.metadata['mac_addr']
boat_type = setup_rtd.metadata['gear_type']
vessel_num = str(setup_rtd.metadata['vessel_num'])
vessel_name = setup_rtd.metadata['vessel_name']
tilt = setup_rtd.metadata['tilt']

header_file = open('/home/pi/Desktop/header.csv', 'w')
header_file.writelines('Probe Type,Lowell\nSerial Number,' + MAC_FILTER[0][
                                                             -5:] + '\nVessel Number,' + vessel_num + '\nVessel Name,' + vessel_name + '\nDate Format,YYYY-MM-DD\nTime Format,HH24:MI:SS\nTemperature,C\nDepth,m\n')  # create header with logger number
header_file.close()

print(MAC_FILTER)

logging.basicConfig()  # enable more verbose logging of errors to console
if not os.path.exists('towifi'):
    os.makedirs('towifi')
#################################### Time Sleep List#############################
CONNECTION_INTERVAL = 1000  # Minimum number of seconds between reconnects
# Set to minutes for lab testing. Set to hours/days for field deployment.

CONNECTION_INTERVAL_After_success_data_transfer = 1500
interval_before_program_run = 400
scan_interval = 6
habor_time_sleep_mobile = 2500
habor_time_sleep_fixed = 600
gps_reading_interval = 90
interval_between_failed = 1500
TIME_IN_WATER = 6  # hours in the water for the sensor to trigger the lowell reader code

##################################################################################

LOGGING = False  # Enable log file for debugging Bluetooth COM errors. Deletes old log and creates new ble_log.txt for each connection.
#########################################################################################################################################

# scanner = btle.Scanner()  # defaut scan func

# A dictionary mapping mac address to last communication time. This should ultimately be moved
# to a file or database. This is a lightweight example.
last_connection = {}
index_times = 0

#########################################################################################
############################### MOANA variables #########################################
#########################################################################################

# the name that the scan searches for
scanName = "ZT-MOANA"

# binary offload enable
binary_offload = 1

vsp_service_uuid = btle.UUID('569a1101-b87f-490c-92cb-11ba5ea5167c')
tx_char_uuid = btle.UUID('569a2001-b87f-490c-92cb-11ba5ea5167c')
rx_char_uuid = btle.UUID('569a2000-b87f-490c-92cb-11ba5ea5167c')

# path to save the moana csv files to
filePath = "/home/pi/rtd_global/logs/raw/Moana/"

if os.path.exists(filePath) == 0:
    print("[SYS] Creating Output File path")
    os.makedirs(filePath)


class bleDevice:
    def __init__(self, addr, rssi, name):
        self.addr = addr
        self.rssi = rssi
        self.name = name


moana = bleDevice("", "", "")


def serialRx(data):
    # print("recived %s"  % (data))
    for c in data:
        BLEReciveChar(c)


def serialTx(data):
    tx.write(data)

    # sends packet to Moana sensor with the correct length at the beginning of the packet


def BLEPacketSend(packet):
    payload = "*"
    # the lenght of the packet it represented by ascii chars strating with 'A'
    # the lenght of the packet is evrthing in it minus the '*' sync char at the start
    # so seing there is 1 lenth char added on to the lenth of packet that is why the + 1 is there
    payload += chr(len(packet) + ord('A'))
    payload += packet
    payload += "\r\n"
    BLESend(payload)
    # print("PI > MOANA %s" % payload)


def BLESend(payload):
    # transmit str over ble serial connection to the connected device
    serialTx(payload)


def strToInt(string):
    # convert a string to an integer
    value = 0
    i = 0
    for c in string:
        value |= ord(c) << i
        i += 8

    return value


def BLERecive(line):
    # get recived charicters from connected BLE device per line
    # line = '*Xa{"authenticated":true}' # just an example of a line that will come through the uart
    # print("MOANA > PI %s" % line)
    if 'bleState' not in BLERecive.__dict__:
        BLERecive.bleState = 1
        # 0 - idle
        # 1 - connecting
        # 2 - time sync
        # 3 - file info
        # 4 - file data
        # 5 - clear data
        BLERecive.fp = 0

    # print(" bleState %d" % BLERecive.bleState)
    if BLERecive.bleState == 5:  # clear data
        BLEPacketSend(".")  # disconnect message
        print("[BLE] Requested bluetooth disconnect")

        if binary_offload:  # post process file
            print("[PP] Post process binary file")
            BLERecive.fp = open(BLERecive.fp.name, "r")
            filebuff = BLERecive.fp.read()
            BLERecive.fp.close()
            firstRecordTimestamp = 0
            i = 0
            for c in filebuff:  # loop till we find the end of the header
                if ord(c) == 3:  # etx char which siginifies the end of the text header
                    break
                i += 1

            BLERecive.fp = open(BLERecive.fp.name, "w")
            BLERecive.fp.write(filebuff[0:i])  # write header back

            firstRecordTimestamp = strToInt(filebuff[i + 1:i + 5])  # get the first record timestamp
            i += 5  # 5 to remove the etx char and timestamp
            for line in (filebuff[j:j + 6] for j in
                         range(i, len(filebuff), 6)):  # loop throught the binary data and decode it
                firstRecordTimestamp += strToInt(line[0:2])
                dt = datetime.utcfromtimestamp(firstRecordTimestamp)
                outputLine = dt.strftime("%Y-%m-%d,%H:%M:%S,")

                outputLine += str("%0.1f," % (strToInt(line[2:4]) / 10.00 - 10))  # depth
                outputLine += str("%0.3f\n" % (strToInt(line[4:6]) / 1000.00 - 10))  # temp

                BLERecive.fp.write(outputLine)

            BLERecive.fp.close()
            print("[PP] Post process done")

        BLERecive.bleState = 0

    elif BLERecive.bleState == 4:  # file Data
        if "*0005D" in line:
            # no more data to process
            BLERecive.fp.close()
            print("[BLE] file downloaded  :  " + BLERecive.fp.name)
            BLEPacketSend("C")  # clear data
            BLERecive.bleState = 5
        else:
            BLERecive.fp.write(line[7:])  # write data to file, removing the length and packet sync char

            if binary_offload:
                BLEPacketSend("B")  # request more binary data
                print("[BLE] Requested binary data packet")
            else:
                BLEPacketSend("R")  # request more data
                print("[BLE] Requested text data packet")

    elif BLERecive.bleState == 3:  # file info
        if "FileName" in line:
            elements = line.split('"')
            fileName = elements[3]
            # print("found file %s" % fileName)
            # file name shold be somthing like "MOANA_2423_31.csv"
            BLERecive.fp = open(filePath + fileName, 'w')

            if binary_offload == 1:
                BLEPacketSend("B")  # request data from file in binary
                print("[BLE] Requested binary data packet")
            else:
                BLEPacketSend("R")  # request data from file
                print("[BLE] Requested text data packet")
            BLERecive.bleState = 4
        else:
            print("[BLE] error getting file info")
            BLERecive.bleState = 0

    elif BLERecive.bleState == 2:  # time sync
        if 't' in line:
            BLEPacketSend("F")  # file info
            print("[BLE] Requested file info packet")
            BLERecive.bleState = 3
        else:
            print("[BLE] time sync error")
            BLERecive.bleState = 0

    elif BLERecive.bleState == 1:  # connecting
        if 'a{"Authenticated":true}' in line:
            ts = int(time.time())  # current unix epoch
            BLEPacketSend("T" + str(ts))  # time sync
            print("[BLE] Sent time sync packet")
            BLERecive.bleState = 2
        else:
            print("[BLE] authentication error")
            BLERecive.bleState = 0


# recives a char from the moana over ble
# call when reciving chars from uart
def BLEReciveChar(c):
    if 'packetState' not in BLEReciveChar.__dict__:
        BLEReciveChar.packetState = 0  # 0 - idle  1 - lenth  2 - body
        BLEReciveChar.length = 0
        BLEReciveChar.lineBuffer = ""
        BLEReciveChar.sentLen = 0
        BLEReciveChar.lenBuff = ""
        # print("init")

    # print("%d %d %s %d %s %c" % (BLEReciveChar.packetState, BLEReciveChar.length, BLEReciveChar.lineBuffer, BLEReciveChar.sentLen, BLEReciveChar.lenBuff, c))
    if BLEReciveChar.packetState == 2:  # body
        if BLEReciveChar.length > BLEReciveChar.sentLen:
            BLEReciveChar.lineBuffer += c  # add the last char
            BLERecive(BLEReciveChar.lineBuffer)  # process line
            BLEReciveChar.lineBuffer = ""  # clear buffer
            BLEReciveChar.length = 0
            BLEReciveChar.packetState = 0

    elif BLEReciveChar.packetState == 1:  # length
        # print(ord(c), ord('A'), ord('Z'))
        if ord(c) >= ord('A') and ord(c) <= ord(
                'Z'):  # short packet format where length is 1 upper case ASCII char starting with 'A'
            BLEReciveChar.sentLen = ord(c) - ord('A')
            BLEReciveChar.packetState = 2
            # print("Short packet len %d" % BLEReciveChar.sentLen)
        else:  # long packet format where the length is represented as 4 lower case hex numbers
            BLEReciveChar.lenBuff += c
            if len(BLEReciveChar.lenBuff) >= 4:  # got the 4 hex chars
                BLEReciveChar.sentLen = int(BLEReciveChar.lenBuff, 16)  # length is in hex format
                # print("long packet len %d" % BLEReciveChar.sentLen)
                BLEReciveChar.lenBuff = ""
                BLEReciveChar.packetState = 2

    if BLEReciveChar.packetState == 0:
        if c == '*':
            BLEReciveChar.packetState = 1

    if BLEReciveChar.packetState != 0:
        if c != 0:
            BLEReciveChar.lineBuffer += c  # build up buffer
        BLEReciveChar.length += 1


class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        serialRx(data)


time_gap = 0
last_scan = datetime.now()
sensor_in = False
while True:
    try:
        scanner = btle.Scanner()
        scan_list = scanner.scan(scan_interval)  # Scan for 6 seconds

        # search for any devices matching the scanName varible
        for dev in scan_list:
            # print(dev.addr)
            for (adtype, desc, value) in dev.getScanData():
                if "name" in desc.lower():
                    if scanName in value:
                        print("[BLE] Device %s (%s), RSSI=%d dB Name %s" % (dev.addr, dev.addrType, dev.rssi, value))
                        moana.addr = dev.addr
                        moana.rssi = dev.rssi
                        moana.name = value

        if moana.addr != "":
            g = open('/home/pi/rtd_global/status.txt',
                     'w')  # necessary file to set if there is any moana file being downloaded
            g.write('0')
            g.close()
            p = btle.Peripheral(moana.addr, btle.ADDR_TYPE_RANDOM)
            p.setDelegate(MyDelegate())

            vspService = p.getServiceByUUID(vsp_service_uuid)

            # print("Connected to  %s %s, RSSI=%d dB" % (moana.name, moana.addr, moana.rssi))

            try:
                tx = vspService.getCharacteristics(tx_char_uuid)[0]
                rx = vspService.getCharacteristics(rx_char_uuid)[0]
                # subscribe to notifications
                p.writeCharacteristic(rx.valHandle + 1, b'\x01\x00', withResponse=True)
                serialTx("*EA123")
                BLERecive.bleState = 1

                while 1:
                    p.waitForNotifications(2)
                    time.sleep(0.1)
            finally:
                p.disconnect()
                moana.addr = ""

        else:  # condition to download other sensor data different to Moana sensors
            g = open('/home/pi/rtd_global/status.txt', 'w')
            g.write('0')
            g.close()

            scan_list = [device for device in scan_list if device.addr in MAC_FILTER]

            # code to run the lowell code just when the mac address has not been found by the RPi for more than TIME_IN_WATER
            if len(scan_list) == 0:
                time_gap = (datetime.now() - last_scan).total_seconds() / 3600
            else:
                last_scan = datetime.now()
                time_gap = 0

            if time_gap > TIME_IN_WATER:
                sensor_in = True

            if sensor_in:
                # Prefer new connections, then the oldest connection, same code as previous eMOLT code but simplified
                oldest_connection = time.time()
                mac = None
                for dev in scan_list:
                    if dev.addr not in last_connection:
                        mac = dev.addr
                        break
                    if last_connection[dev.addr] < oldest_connection and \
                            time.time() - last_connection[dev.addr] > CONNECTION_INTERVAL:
                        mac, oldest_connection = dev.addr, last_connection[dev.addr]

                if not mac:
                    continue

                print('')
                print('*************New Connection*************')
                print(time.strftime("%c"))
                print('Connecting to {}'.format(mac))

                sensor_in = False

                try:
                    p = btle.Peripheral(mac)  # create a peripheral object. This opens a BLE connection.
                except btle.BTLEException:  # There was a problem opening the BLE connection.
                    print('Failed to connect to ' + mac)
                    continue

                if LOGGING:  # Debug Code.Creating a log file that saves ALL coms for the current connection. Sometimes helpful for troubleshooting.
                    file_h = open('ble_log.txt', 'w')  # This is bad form but temporary
                    log_obj = odlw_facade.BLELogger(file_h)

                with p:
                    try:  # all commands need to be in the try loop. This will catch dropped connections and com errors
                        connection = odlw_facade.OdlwFacade(p)  # create a facade for easy access to the ODLW

                        if LOGGING:
                            connection.enable_logging(log_obj)

                        time.sleep(1)  # add a short delay for unknown, but required reason

                        # Stop the logger from collecting data to improve reliability of comms and allow data transfer
                        print('Stopping deployment: ' + connection.stop_deployment())
                        time.sleep(2)  # delay 2 seconds to allow files to close on SD card

                        # Increase the BLE connection speed
                        print('Increasing BLE speed.')
                        connection.control_command('T,0006,0000,0064')  # set latency and timeouts in RN4020 to minimums
                        time.sleep(2)  # Delay 2 seconds to allow MLDP status string to clear

                        # Make sure the clock is within range, otherwise sync it
                        try:
                            odlw_time = connection.get_time()
                        except ValueError:
                            print('ODL-1W returned an invalid time. Clock not checked.')
                        else:
                            # Is the clock more than a day off?
                            if abs((datetime.utcnow() - odlw_time).total_seconds()) > 100:
                                print('did  Syncing time.')
                                connection.sync_time()

                        # Filler commands to test querying
                        # for i in range(1):
                        #     print('Time: ' + str(connection.get_time()))
                        #     print('Status: ' + connection.get_status())
                        #     print('Firmware: ' + connection.get_firmware_version())
                        #     print('Serial Number: ' + connection.get_serial_number())

                        # Download any .lis files that aren't found locally
                        folder = mac.replace(':',
                                             '-').lower()  # create a subfolder with the ODL-1W's unique mac address

                        if not os.path.exists(folder):
                            os.makedirs(folder)
                        serial_num = folder[-5:].replace('-', '')
                        print(serial_num)
                        print('Requesting file list')
                        files = connection.list_files()  # get a list of files on the ODLW
                        files.reverse()
                        print(
                            files)  # Note: ODL-W has a very limited file system. Microprocessor will become RAM bound if files are over 55-65.
                        # The exact number depends on file name length and ???. TBD: add a check for files numbers above 55.

                        dateti = datetime.now()
                        second, minute, hour, day, month, year = str(dateti.second), str(dateti.minute), str(
                            dateti.hour), str(dateti.day), str(dateti.month), str(dateti.year)
                        if len(second) == 1:
                            second = '0' + second
                        if len(minute) == 1:
                            minute = '0' + minute
                        if len(hour) == 1:
                            hour = '0' + hour
                        if len(day) == 1:
                            day = '0' + day
                        if len(month) == 1:
                            month = '0' + month

                        for name, size in files:
                            name_file = 'li_' + ''.join(MAC_FILTER.split(':')[
                                                        -2:]) + '_' + year + month + day + '_' + hour + minute + second + '.lid'  # creates the filename following eMOLT requirements
                            if not name.endswith('.lid'):
                                continue
                            # Check if the file exists and get it's size

                            file_path = os.path.join(folder, name_file)
                            local_size = None
                            print(file_path)
                            if os.path.isfile(file_path):
                                local_size = os.path.getsize(file_path)
                            if not local_size or local_size != size:
                                with open('/home/pi/rtd_global/' + file_path, 'wb') as outstream:
                                    print('Downloading ' + name)
                                    start_time = time.time()
                                    connection.get_file(name, size, outstream)
                                    end_time = time.time()
                                    print(
                                        'Download of {} complete - {:0.2f} bytes/sec.'.format(name, size / (
                                                end_time - start_time)))
                                parse_li('/home/pi/rtd_global/' + file_path)
                                time.sleep(1)

                                os.system('sudo mv /home/pi/rtd_global/' + folder + '/' + name_file[
                                                                                          :-3] + 'csv /home/pi/rtd_global/logs/raw/Lowell/')

                                print('Deleting {}'.format(name))
                                connection.delete_file(name)

                            else:
                                print('Deleting {}'.format(name))
                                connection.delete_file(name)
                        print('Restarting Logger: ')
                        connection.start_deployment()
                        time.sleep(2)  # 2 second delay to write header of new data file
                        # last_connection[mac] = time.time()  # keep track of the time of the last communication
                        print('Disconnecting')
                        g = open('/home/pi/rtd_global/status.txt', 'w')  # necessary for moana sensor download
                        g.write('1')
                        g.close()
                        # time.sleep(1800)


                    except odlw_facade.Retries as error:  # this exception originates in odlw_facade
                        print(str(error))
                    except btle.BTLEException:  # only log time if the try block was successful
                        print('Connection lost.')
                    except odlw.XModemException as error:
                        print(str(error))

    except btle.BTLEDisconnectError:
        print("[BLE] disconnected")
        g = open('/home/pi/rtd_global/status.txt', 'w')
        g.write('1')
        g.close()
        time.sleep(10)
