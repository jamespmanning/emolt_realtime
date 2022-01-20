import odlw
import time
import datetime


class OdlwFacade:
    """
    This class is a facade for odlw.py

    It isolates the user from the low-level business.
    """

    RETRIES = 3  # Number of times to retry a failed communication attempt
    RETRY_DELAY = 3  # Number of seconds to delay between communication retries

    def __init__(self, peripheral):
        """ Pass in an open Bluepy peripheral object """
        self.connection = odlw.Odlw(peripheral)
        self.file_h = None

    def _command(self, tag, data=None):
        """
        It is not recommended the user call this method directly. Use the builtin command methods.

        For example, instead of _command('GTM') use get_time()
        """
        if tag == dir:
            raise RuntimeError('DIR not supported by _command() method. Use list_files()')

        for retry in range(self.RETRIES):
            try:
                return self.connection.command(tag, data)
            except odlw.OdlwException as error:
                print str(error)
            except odlw.XModemException as error:
                print str(error)

            # don't catch BTLEException and allow to propagate. Don't want to retry if the connection is lost

            time.sleep(self.RETRY_DELAY)  # wait RETRY_DELAY seconds before trying again

        raise Retries('MAT-1W communication failed on {} consecutive attempts.'.format(self.RETRIES))

    def control_command(self, data):
        return self.connection.control_command(data)

    def list_files(self):
        """
        List the files on MAT-1W

        File names and sizes are returned as a list of tuples. [(name, size), (name, size), (name, size)]
        """
        for retry in range(self.RETRIES):
            try:
                return self.connection.list_files()
            except odlw.OdlwException as error:
                print str(error)
            time.sleep(self.RETRY_DELAY)  # wait RETRY_DELAY seconds before trying again

        raise Retries('list_files failed on {} consecutive attempts.'.format(self.RETRIES))

    def get_file(self, name, size, out_stream):
        """
        Download a file from the MAT-1W

        Arguments:
            name -- name of the file to download
            size -- size of the file in bytes. Size is available from the list_files() method
            out_stream -- a handle to a file open for writing binary. eg. open(example.lid, 'wb')
        """
        self.connection.get_file(name, size, out_stream)

    def delete_file(self, name):
        """Delete a file from the MAT-1W"""
        self._command('DEL', name)

    def start_deployment(self):
        """Start a new deployment."""
        return self._command('RUN')

    def stop_deployment(self):
        """Stop the current deployment"""
        return self._command('STP')

    def get_status(self):
        """Requests the logging status bits to determine the logging state."""
        return self._command('STS')

    def get_time(self):
        """
        Get the time from the MAT-1W RTC. Returns a datetime object.

        If the time string is of invalid format, a ValueError will be raised.
        """
        odlw_time = datetime.datetime.strptime(self._command('GTM')[6:], '%Y/%m/%d %H:%M:%S')
        return odlw_time

    def get_serial_number(self):
        """Get the MAT-1W serial number"""
        return self._command('GSN')

    def get_firmware_version(self):
        """Get the MAT-1W firmware version"""
        return self._command('GFV')

    def sync_time(self):
        """Sync the time on the logger to match the computer time"""
        self.set_time(datetime.datetime.now())

    def set_time(self, time):
        """Set the time on the logger. time must be a datetime object"""
        time_str = time.strftime('%Y/%m/%d %H:%M:%S')
        self._command('STM', time_str)

    def disconnect(self):
        """Disconnect from the MAT-1W"""
        self.connection.disconnect()

    def enable_logging(self, log_obj):
        self.connection.register_rx_observer(log_obj.rx)
        self.connection.register_tx_observer(log_obj.tx)


class BLELogger:
    def __init__(self, file_h):
        self.file_h = file_h
        self.file_h.write('Logging started\r\n')

    def tx(self, data):
        self.file_h.write('{} >>>: '.format(datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]))
        self._write(data)

    def rx(self, data):
        self.file_h.write('{} <<<: '.format(datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]))
        self._write(data)

    def _write(self, data):
        for c in data:
            if 32 <= ord(c) <= 125:
                self.file_h.write('{} '.format(c))
            else:
                self.file_h.write('[{}] '.format(ord(c)))
        self.file_h.write('\r\n')
        self.file_h.flush()

class Retries(Exception):
    pass

