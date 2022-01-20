"""
This module allows for low-level reading of binary lid/lis files.
Use the converter module to convert raw values to meaningful si values
"""

#TODO add the ability to use a custom host storage file

import datetime
import converter
import numpy as np


def load_file(file_obj):
    """
    Factory to return the appropriate OdlFile subclass

    file_obj -- the handle of an open .lid or .lis file
    """
    try:
        extension = file_obj.name[-4:]
        class_ = {'.lid': LidFile, '.lis': LisFile}.get(extension)
    except KeyError:
        raise Exception('Invalid Filename')
    return class_(file_obj)


class OdlFile(object):
    """
    This must be sub-classed.
    Base class for interacting with a Lowell Instruments LID file.
    """

    def __init__(self, file_obj):
        self._file = file_obj
        self.file_size = self._file_size()
        self.header = self._header()
        self.converter = self._load_converter()
        self.mini_header_length = self._mini_header_length()
        self.n_pages = self._n_pages()
        self.page_start_times = self._page_start_times()
        self.data_start = self._data_start()
        self.page_size = self._page_size()
        self.major_interval_seconds = max(self.header['TRI'], self.header['ORI'])
        self.sequence, self.sequence_time = self._build_sequence()  # time is in 64ths of a second
        # logical index arrays for the various sensors
        self.is_temp = self.sequence == 'T'
        self.is_pres = self.sequence == 'P'
        self.is_light = self.sequence == 'L'
        self.is_accel = self.sequence == 'A'
        self.is_mag = self.sequence == 'M'

        self.maj_interval_bytes = len(self.sequence) * 2
        self.n_maj_intervals_per_page = self._n_maj_intervals_per_page()
        self.n_orient_intervals_per_page = self._n_orient_intervals_per_page()
        self.n_temperature_intervals_per_page = self._n_temperature_intervals_per_page()
        self.n_orient_intervals = self._n_orient_intervals()
        self.n_temperature_intervals = self._n_temperature_intervals()

    def _build_sequence(self):
        """
        Position within major interval where temperature and orient intervals begin.

        """
        h = self.header

        # TODO for now, TRI must be <= ORI
        major_interval_seconds = max(h['TRI'], h['ORI'])

        if h['ORI'] > 0:
            assert h['TRI'] == h['ORI'], 'TRI must equal ORI - at least for now'

        # arrays to store the index values where samples begin
        sequence = []
        sequence_time = []

        accel_remaining = h['BMN'] if h['ACL'] else 0
        mag_remaining = h['BMN'] if h['MGN'] else 0
        pres_remaining = h['PRN']

        # 'n' counts over the major interval by 64ths of seconds
        for n in range(0, major_interval_seconds * 64):
            if h['TMP'] and n % (h['TRI'] * 64) == 0:
                sequence.append('T')
                sequence_time.append(n)

            # if pressure is enabled AND there are still samples in this burst AND the time is right THEN
            if h['PRS'] and pres_remaining and n % (64 / h['PRR']) == 0:
                sequence.append('P')
                pres_remaining -= 1
                sequence_time.append(n)

            if h['PHD'] and n % (h['TRI'] * 64) == 0:
                sequence.append('L')
                sequence_time.append(n)

            if h['ACL'] and accel_remaining and n % (64 / h['BMR']) == 0:
                sequence.extend(['A', 'A', 'A'])
                accel_remaining -= 1
                sequence_time.extend([n, n, n])

            if h['MGN'] and mag_remaining and n % (64 / h['BMR']) == 0:
                sequence.extend(['M', 'M', 'M'])
                mag_remaining -= 1
                sequence_time.extend([n, n, n])

        return np.array(sequence), np.array(sequence_time)



    def _file_size(self):
        """
        Size of the ODL file in bytes
        """

        file_pos = self._file.tell()
        self._file.seek(0, 2)
        file_length = self._file.tell()
        self._file.seek(file_pos)
        return file_length

    def _header(self):
        """
        The main header as a dictionary with tags as keys.
        """

        type_int = ['BMN', 'BMR', 'DPL', 'STS', 'ORI', 'TRI', 'PRR', 'PRN']
        type_bool = ['ACL', 'LED', 'MGN', 'TMP', 'PRS', 'PHD']

        # default values for all keys. Makes old lid files compatible with new tags
        header = {}
        for key in type_int:
            header[key] = 0

        for key in type_bool:
            header[key] = False

        self._file.seek(0, 0)
        this_line = self._file.readline().decode('IBM437')

        if this_line[:3] != 'HDS':
            raise LidError('HDS tag missing in main header.')

        # TODO add logic to avoid having to read the whole file should the HDE tag not appear
        this_line = self._file.readline().decode('IBM437')
        while not this_line.startswith('HDE'):
            tag = this_line[:3]
            if tag == 'LIS':  # Lis files have the logger info written in the header. This ignores it
                while not this_line.endswith('LIE\r\n'):
                    this_line = self._file.readline().decode('IBM437')
                this_line = self._file.readline().decode('IBM437')
                continue
            if tag == 'MHS' or tag == 'MHE':
                this_line = self._file.readline().decode('IBM437')
                continue
            value = this_line[4:]
            value = value.replace('\r', '')
            value = value.replace('\n', '')
            if tag in type_int:
                value = int(value)
            elif tag in type_bool:
                value = bool(int(value))

            header[tag] = value
            this_line = self._file.readline().decode('IBM437')

        if self.__class__ == LisFile:
            # .lis files are averaged on board over the ori, essentially making the BMN 1.
            # If this 'hack' doesn't go here, the maj_int size is calculated incorrectly and the problem trickles down
            header['BMN'] = 1

        return header


    def _load_converter(self):
        """
        Return a converter object that stores the calibration coefficients and converts raw data to SI units
        """

        self._file.seek(0)
        this_line = self._file.readline().decode('IBM437')
        while not this_line.startswith('HDE'):
            this_line = self._file.readline().decode('IBM437')
        hs_str = self._file.read(380).decode('IBM437')
        return converter.create_converter(hs_str)


    def _n_orient_intervals_per_page(self):
        """
        Number of orient intervals in a data page.
        An orient interval represents ORI seconds of data (BMN samples)
        """

        if self.header['ORI']:
            n_orient = self.n_maj_intervals_per_page * self.major_interval_seconds // self.header['ORI']
        else:
            n_orient = 0
        return n_orient


    def _n_temperature_intervals_per_page(self):
        """
        Number of temperature intervals in a data page.
        :return: int
        """
        # In the case of a lis file, n_maj_intervals_per_page is huge infinite, causing a huge return number
        return self.n_maj_intervals_per_page * self.major_interval_seconds // self.header['TRI'] if self.header['TMP'] else 0

    def read_temperature(self, n):
        """
        Return the nth raw temperature value
        """

        if self._file.closed:
            raise RuntimeError('File must be open to read data')

        # The page and the sample number within the page
        page_n, sample_n = divmod(n, self.n_temperature_intervals_per_page)

        # Jump to the correct file position
        self._file.seek(self.data_start + page_n * self.page_size + self.mini_header_length + sample_n *
                        self.maj_interval_bytes)

        # reading the first byte works because temperature is always first
        temp = np.fromfile(self._file, dtype='<u2', count=1)
        return temp

    def read_pressure(self, n):
        """
        Read the nth orient interval.

        If BPN > 1 a list will be returned.
        """

        # The page and the sample number within the page
        page_n, sample_n = divmod(n, self.n_temperature_intervals_per_page)

        # Jump to the correct file position
        self._file.seek(self.data_start + page_n * self.page_size + self.mini_header_length + sample_n *
                        self.maj_interval_bytes)

        # reading the first byte works because temperature is always first
        pressure_raw = np.fromfile(self._file, dtype='<u2', count=len(self.sequence))
        pressure = pressure_raw[self.is_pres]
        return pressure

    def _n_orient_intervals(self):
        """
        Number of orient intervals in the file
        """

        h = self.header  # alias to a shorter variable names

        last_page_bytes = self.file_size - (self.n_pages-1)*self.page_size - self.mini_header_length - self.data_start
        n_maj_int, rem = divmod(last_page_bytes, self.maj_interval_bytes)

        n_intervals = (self.n_pages-1)*self.n_orient_intervals_per_page + n_maj_int

        return n_intervals

    def _n_temperature_intervals(self):
        """
        Number of temperature intervals in the file
        """

        h = self.header  # alias to a shorter variable names

        last_page_bytes = self.file_size - (self.n_pages-1)*self.page_size - self.mini_header_length - self.data_start
        n_maj_int, rem = divmod(last_page_bytes, self.maj_interval_bytes)

        n_intervals = (self.n_pages-1)*self.n_temperature_intervals_per_page + n_maj_int

        return n_intervals

    def read_orient(self, n):
        """
        Read the nth orient interval.

        If BMN > 1 a list of samples of length BMN will be returned.
        """

        if self._file.closed:
            raise RuntimeError('File must be open to read data')

        h = self.header  # alias to a shorter variable names

        # The page and the sample number within the page
        page_n, sample_n = divmod(n, self.n_orient_intervals_per_page)

        self._file.seek(self.data_start + page_n * self.page_size + self.mini_header_length + sample_n *
                        self.maj_interval_bytes)

        maj_interval_raw = np.fromfile(self._file, dtype='<i2', count=len(self.sequence))
        accel = maj_interval_raw[self.is_accel].reshape([-1, 3])
        mag = maj_interval_raw[self.is_mag].reshape([-1, 3])

        return accel, mag

    def _mini_header_length(self):
        """
        Length of the mini header in bytes.
        """
        raise NotImplementedError

    def _n_pages(self):
        raise NotImplementedError

    def _page_start_times(self):
        raise NotImplementedError

    def _n_maj_intervals_per_page(self):
        raise NotImplementedError

    def _data_start(self):
        raise NotImplementedError

    def _page_size(self):
        raise NotImplementedError


class LidFile(OdlFile):
    def __init__(self, file_obj):
        super(LidFile, self).__init__(file_obj)

    def _data_start(self):
        return 32768

    def _page_size(self):
        return 1024**2

    def _mini_header_length(self):
        """
        See base class for documentation
        """

        self._file.seek(32768)  # jump to the start of the first data page
        this_line = self._file.readline().decode('IBM437')
        if not this_line.startswith('MHS'):
            raise LidError('MHS tag missing on first data page.')

        while not this_line.startswith('MHE'):
            this_line = self._file.readline().decode('IBM437')

        end_pos = self._file.tell()

        return end_pos-32768

    def _n_pages(self):
        """
        The number of data pages in the LID file.
        :return: int
        """
        n_pages = 0
        while True:
            self._file.seek(32768+1024**2*n_pages)
            this_line = self._file.readline().decode('IBM437')
            if this_line.startswith('MHS'):
                n_pages += 1
            else:
                break
        return n_pages


    def _page_start_times(self):
        """
        A list containing the start time of each data page.
        :return: list
        """
        page_start_times = []
        delta = datetime.timedelta(seconds=1)
        for page_n in range(self.n_pages):
            self._file.seek(32768+1024**2*page_n)
            this_line = self._file.readline().decode('IBM437')
            if not this_line:  # tried reading for a non-existent page
                raise LidError('Page {} does not exist.'.format(page_n))
            if not this_line.startswith('MHS'):
                raise LidError('MHS tag missing on page {}.'.format(page_n))

            while True:  # Read until the CLK tag is reached
                this_line = self._file.readline().decode('IBM437')
                this_line = this_line.strip()
                tag, value = this_line[:3], this_line[4:]
                if tag == 'HSE':
                    raise LidError('CLK tag missing on page {}.'.format(page_n))
                if tag == 'CLK':
                    if page_n == 0:
                        page_start_times.append(datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S'))
                    else:  # The timestamp on all pages after the first have an extra 1 second (permanent bug)
                        page_start_times.append(datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')-delta)
                    break

        return page_start_times

    def _n_maj_intervals_per_page(self):
        """
        The number of major intervals per page
        """
        if self.n_pages > 1:  # Use the time stamp to avoid the firmware bug that stops writing too early
            seconds_per_page = int((self.page_start_times[1] - self.page_start_times[0]).total_seconds())
            n_maj_intervals_per_page, remainder = divmod(seconds_per_page, self.major_interval_seconds)
            assert remainder == 0, 'Number of major intervals is not a factor of page time.'
        else:
            # If it's less than one page, the number of intervals in irrelevant.
            n_maj_intervals_per_page = 9999999999

        return n_maj_intervals_per_page


class LisFile(OdlFile):
    def __init__(self, file_obj):
        super(LisFile, self).__init__(file_obj)

    def _data_start(self):
        return 1024

    def _page_size(self):
        return 9999999999

    def _mini_header_length(self):
        """
        Length of the mini header in bytes.
        :return: int
        """
        return 0

    def _n_pages(self):
        """
        The number of data pages in the LID file.
        :return: int
        """
        return 1

    def _page_start_times(self):
        """
        A list containing the start time of each data page as a datetime object
        :return: list
        """
        page_start_times = []
        page_start_times.append(datetime.datetime.strptime(self.header['CLK'], '%Y-%m-%d %H:%M:%S'))
        return page_start_times

    def _n_maj_intervals_per_page(self):
        return 9999999999


class LidError(Exception):
    pass

