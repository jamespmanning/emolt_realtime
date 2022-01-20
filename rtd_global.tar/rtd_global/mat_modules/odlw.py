import bluepy.btle as btle
import time
import re
import xmodem
import logging
import sys
from math import ceil


class Delegate(btle.DefaultDelegate):
    """
    Bluepy calls the handleNotification method of the delegate object when a notification is received.

    Delegate also acts as a buffer to store received data until it is read by the user. Data come across the MLDP
    connection in packets, not complete lines. handleNotification assembles packets into complete lines based on the
    CR character and appends them to the FIFO read_buffer.
    """

    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        self.buffer = ''
        self.read_buffer = []
        self.xmodem_mode = False
        self.rx_observers = []

    def handleNotification(self, cHandle, data):
        """
        Receive notification from the subscribed BLE characteristic.
        cHandle is the handle of the characteristic
        data is the data package
        """

        # print('Incoming: {}'.format(data))
        for observer in self.rx_observers:  # send the data to any registered observers
            observer(data)

        self.buffer += data

        if not self.xmodem_mode:
            self.buffer = self.buffer.replace(chr(10), '')  # Get rid of LFs
            while chr(13) in self.buffer:
                if self.buffer.startswith(chr(13)):  # Make sure it doesn't start with CR
                    self.buffer = self.buffer[1:]
                    continue

                pos = self.buffer.find(chr(13))
                in_str = self.buffer[:pos]
                self.buffer = self.buffer[pos+1:]
                if in_str:
                    # print('Adding to buffer: {}'.format(in_str))
                    self.read_buffer.append(in_str)  # if a complete string was received, add it to read_buffer

    @property
    def in_waiting(self):
        """
        Return True if the read buffer contains a complete line, or if xmodem mode is active
        """

        return True if self.xmodem_mode or self.read_buffer else False

    def read_line(self):
        """
        Read next line in the FIFO read buffer.

        If a read attempt is made on an empty buffer, an IndexError is raised.
        """

        if not self.read_buffer:
            raise IndexError('Read buffer is empty')

        return self.read_buffer.pop(0)

    def read_chars(self, num_chars):
        """
        Return num_chars characters from the read buffer. If there are insufficient characters, an exception is raised
        """

        if num_chars > len(self.buffer):
            raise RuntimeError('Insufficient characters in buffer')

        self.buffer, return_string = self.buffer[num_chars:], self.buffer[:num_chars]
        return return_string


class Odlw:
    """
    Odlw is the low level representation of the MAT-1W current meter.

    The user must supply an open BLE connection in the __init__. It is recommend that the "with" keyword be used
    to open the connection as this will ensure it is closed correctly on exit.

    For example:
    with bluepy.btle.Peripheral(mac_address) as p:
    """

    def __init__(self, peripheral):
        """
        peripheral is an open btle.Peripheral object
        """
        self.peripheral = peripheral
        self.delegate = Delegate()
        self.peripheral.setDelegate(self.delegate)

        # Service For Microchip MLDP
        self.mldp_service = self.peripheral.getServiceByUUID('00035b03-58e6-07dd-021a-08123a000300')

        # Characteristic For MLDP Data
        self.mldp_data = self.mldp_service.getCharacteristics('00035b03-58e6-07dd-021a-08123a000301')[0]

        # Handle for the MLDP Client Characteristic Configuration descriptor
        cccd = self.mldp_data.valHandle + 1
        self.peripheral.writeCharacteristic(cccd, '\x01\x00')  # Enable notification

        self.tx_observers = []
        self.rx_observers = []
        self.delegate.rx_observers.append(self.rx_notify)  # Register a listener in the delegate class that will call
                                                           # notify rx_notify when a data packet is received.

        # Setup xmodem and error logging
        self.modem = xmodem.XMODEM(self.getc, self.putc)


    def register_rx_observer(self, h):
        """
        Register an rx listener.

        When a data packet is received, it will be passed to registered listeners.
        """

        self.rx_observers.append(h)

    def register_tx_observer(self, h):
        """
        Register a tx listener.

        When data is transmitted, it will be passed to registered listeners.
        """

        self.tx_observers.append(h)

    def rx_notify(self, data):
        """
        This method was registered as an rx listener for the delegate in the __init__.

        Whenever the delegate receives a data packet, it will be passed to this method. If any listeners are registered
        they will receive the data.
        """

        for observer in self.rx_observers:
            observer(data)  # since the

    def command(self, tag, data=None):
        """
        Send a command to the MAT-1W.


        """

        return_val = None
        data = '' if data is None else data
        length = '%02x' % len(data)

        if tag == 'sleep' or tag == 'RFN':
            out_str = tag
        else:
            out_str = tag + ' ' + length + data

        last_tx = time.time()
        self.write(out_str + chr(13))

        # RST, BSL and sleep don't return tags
        if tag == 'RST' or tag == 'sleep' or tag == 'BSL':
            tag_waiting = ''
        else:
            tag_waiting = tag

        while tag_waiting:
            if not self.peripheral.waitForNotifications(5):
                raise OdlwException('Logger timeout while waiting for: ' + tag_waiting)

            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                if inline.startswith(tag_waiting):
                    tag_waiting = ''
                    return_val = inline
                elif inline.startswith('ERR'):
                    raise OdlwException('MAT-1W returned ERR')
                elif inline.startswith('INV'):
                    raise OdlwException('MAT-1W reported invalid command')

        return return_val

    def control_command(self, data):
        """
        Control commands are used to set configuration values on the RN4020 module.

        See RN4020 documentation for command listing.
        """
        out_str = 'BTC 00' + data + chr(13)
        self.write(out_str)

        last_rx = time.time()
        return_val = ''
        while time.time() - last_rx < 2:
            if self.peripheral.waitForNotifications(0.5):
                last_rx = time.time()
            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                return_val += inline
        return return_val

    def write(self, data, response=False):
        """
        Write data 1 byte at a time over mldp and update listeners of transmission.
        """

        # print('Writing: {}'.format(data))
        for c in data:
            self.mldp_data.write(c, withResponse=response)

        for observer in self.tx_observers:
            observer(data)

    def list_files(self):
        """
        Return a list of the files on the the MAT-1W current meter.

        Each list item contains a tuple with the name and file size (name, size).
        """

        files = []

        self.delegate.buffer = ''
        self.delegate.read_buffer = []

        tx_time = time.time()

        # Call write() directly because DIR doesn't respond in the standard way ie. no DIR 00 response
        # causing command() to return a timeout exception
        self.write('DIR 00' + chr(13))

        last_rx = time.time()
        while True:
            self.peripheral.waitForNotifications(0.01)
            if self.delegate.in_waiting:
                last_rx = time.time()
                file_str = self.delegate.read_line()
                if file_str == chr(4):
                    break
                re_obj = re.search('([\x20-\x7E]+)\t+(\d*)', file_str)  # Find all printable characters
                try:
                    file_name = re_obj.group(1)
                    file_size = int(re_obj.group(2))
                except (AttributeError, IndexError):
                    raise OdlwException('DIR returned an invalid filename.')

                files.append((file_name, file_size))
            if time.time() - last_rx > 2:  # There was a timeout. Don't return anything
                raise OdlwException('Timeout while getting file list.')

        return files

    def getc(self, size, timeout=2):
        """
        A method used by the XModem module for receiving "size" characters.
        """

        start_time = time.time()

        while True:
            self.peripheral.waitForNotifications(0.005)
            in_char = self.delegate.read_chars(size) if len(self.delegate.buffer) >= size else None
            if in_char:
                sys.stdout.write('.')
                return in_char
            if time.time() - start_time > timeout:
                return None

    def putc(self, data, timeout=0):
        """
        A method used by the XModem module for transmitting control characters.
        """

        self.write(data)

    def get_file(self, filename, size, outstream):
        """
        Download "file" from the MAT-1W current meter.

        Positional Arguments:
        filename -- file name on MAT-1W to download
        size -- the number of bytes in the file (obtained by the "get_files" method
        outstream -- a handle to a file open for writing
        """

        self.command('GET', filename)

        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.delegate.xmodem_mode = True

        start_time = time.time()

        try:
            self.modem.recv(outstream)  # Pass control over to the xmodem module
        except:
            raise XModemException('File transfer error')

        outstream.seek(0, 2)
        if outstream.tell() < size:
            raise XModemException('File too small. Transmission was incomplete.')

        outstream.truncate(size)  # Cut the file to the size (removing trailing 0x1A padding characters)
        self.delegate.buffer = ''
        self.delegate.xmodem_mode = False

        print('\nFile downlaoded successfully')
        return True

    def disconnect(self):
        """
        Close the BLE connection
        """

        self.peripheral.disconnect()

class OdlwException(Exception):
    pass

class XModemException(Exception):
    pass
