from __future__ import division
import datetime
import array
import interp
from math import ceil, cos, sin, atan2, acos, sqrt, degrees, pi, log


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


def temp_to_si(temp_raw, coefficients):
    """
    Convert raw temperature values (unsigned int16) into degrees C.

    Keyword arguments:
    coefficients -- the calibration coefficients (host storage)
    """

    h = coefficients
    temp = (temp_raw * h['TMR']) / (65535-temp_raw)  # Convert to resistance values
    temp = 1 / (h['TMA'] + h['TMB'] * log(temp) + h['TMC'] * (log(temp)) ** 3) - 273.15
    return temp


def accel_to_si(accel_raw, coefficients):
    """
    Convert raw acceleration values (signed int16) into g.

    Arguments:
    accel_raw -- a tuple of format (Ax, Ay, Az)
    coefficients -- the calibration coefficients (host storage)
    """
    hs = coefficients

    # If it's empty, return it empty.
    if not any(accel_raw):
        return accel_raw[:]

    if 'RVN' in hs and hs['RVN'] == 2:
        accel = [float(val)/1024 for val in accel_raw]

        gain = [[hs['AXX'], hs['AXY'], hs['AXZ']],
                [hs['AYX'], hs['AYY'], hs['AYZ']],
                [hs['AZX'], hs['AZY'], hs['AZZ']]]
        offset = [hs['AXV'], hs['AYV'], hs['AZV']]
        cubic = [hs['AXC'], hs['AYC'], hs['AZC']]

        # accel = gain * accel + offset + cubic * accel ** 3
        accel[:] = [sum([gain[row][col]*accel[col] for col in range(3)]) + offset[row] + cubic[row] *
                    accel[row]**3 for row in range(3)]

    else:
        accel = [float(val) for val in accel_raw]

        gain = [hs['AXB'], hs['AYB'], hs['AZB']]
        offset = [hs['AXA'], hs['AYA'], hs['AZA']]

        accel[:] = [-accel[i]/gain[i] - offset[i] for i in range(3)]

    return accel


def mag_to_si(mag_raw, coefficients):
    """
    Convert raw magnetometer values (signed int16) into mG.

    Keyword arguments:
    coefficients -- host calibration coefficients (host storage)
    """

    hs = coefficients

    # If it's empty, return it empty.
    if not any(mag_raw):
        return mag_raw[:]

    # mag = [[float(sum(a)/len(a)) for a in zip(*mag_raw)]]  # Calculate the mean down the columns
    mag = [float(val) for val in mag_raw]

    if 'RVN' in hs and hs['RVN'] == 2:
        hi = [hs['MXV'], hs['MYV'], hs['MZV']]
        si = [[hs['MXX'], hs['MXY'], hs['MXZ']],
              [hs['MYX'], hs['MYY'], hs['MYZ']],
              [hs['MZX'], hs['MZY'], hs['MZZ']]]
        # mag = si * (mag + hi)
        # add hi to mag

        # mag[:] = [sum(row[i] * (mag[i] + hi[i]) for i in range(3)) for row in si]

        # TODO make sure the following two lines are working
        mag[:] = [mag[i] + hi[i] for i in range(3)]
        mag[:] = [sum([mag[i] * si_row[i] for i in range(3)]) for si_row in si]
    else:
        offset = [hs['MXA'], hs['MYA'], hs['MZA']]
        scale = [hs['MXS'], hs['MYS'], hs['MZS']]
        # TODO make sure this is working with triplet values; check status of the list of lists thing
        mag[:] = [(mag[i] + offset[i]) * scale[i] for i in range(3)]

    return mag


def flow(accel, mag, flow_profile):
    """
    Convert acceleration and magnetometer values into flow (m/s)

    Keyword arguments:
    flow_profile -- a tuple of two lists relating tilt angle to flow speed. Load from file using load_flow_profile()
    """

    """
    roll        = atan2d(ay,az);
    pitch       = atan2d(-ax,ay.*sind(roll)+az.*cosd(roll));
    by          = mz.*sind(roll)-my.*cosd(roll);
    bx          = mx.*cosd(pitch)+my.*sind(pitch).*sind(roll)+mz.*sind(pitch).*cosd(roll);
    yaw         = atan2d(by,bx);
    """
    roll = atan2(accel[1], accel[2])
    pitch = atan2(-accel[0], accel[1] * sin(roll) + accel[2] * cos(roll))
    by = mag[2] * sin(roll) - mag[1] * cos(roll)
    bx = mag[0] * cos(pitch) + mag[1] * sin(pitch) * sin(roll) + mag[2] * sin(pitch) * cos(roll)
    yaw = atan2(by, bx)

    """
    x           = -cosd(roll).*sind(pitch);
    y           = sind(roll);
    z           = cosd(roll).*cosd(pitch);
    tilt        = acosd(az./sqrt(ax.^2+ay.^2+az.^2));
    isUsd       = tilt > 90; %upside down
    tilt(isUsd) = 180 - tilt(isUsd);
    """

    x = -cos(roll) * sin(pitch)
    y = sin(roll)

    tilt = acos(accel[2] / sqrt(accel[0]**2 + accel[1]**2 + accel[2]**2))
    tilt = pi - tilt if tilt > pi/2 else tilt
    tilt = degrees(tilt)

    point = atan2(y, x) + yaw
    point %= 2 * pi
    point_e = sin(point)
    point_n = cos(point)

    flow = interp.interp1(flow_profile[0], flow_profile[1], tilt)
    flow_n = flow * point_n
    flow_e = flow * point_e

    return flow_n, flow_e


def load_flow_profile(file_path):
    """
    Return a tuple containing two lists relating tilt angle to flow speed.

    The file must be formatted correctly. This function doesn't do any error checking (yet).
    """
    with open(file_path, 'r') as f:
        angle, flow = [], []
        header = True
        for line in f:
            if 'CAL' in line:
                header = False
                continue
            if header:
                continue
            a, f = [float(x) for x in line.split(',')]
            angle.append(a)
            flow.append(f)
    return angle, flow


class Reader(object):
    """
    Base class for OrientReader and TemperatureReader

    n_intervals, duration, and interval must be implemented in subclass.
    Check that the arguments passed are valid, and calculates the start
    and end indices for the intervals to read.

    Keyword arguments:
    start_time -- datetime object specifying where to start parsing the file. Parsing will begin at
        the first interval with a time greater than or equal to start_time. Data will not interpolate to start time
        if it does not fall on an interval.
    end_time -- datetime object specifying where to end parsing. end_time is exclusive, meaning that if an interval
        has the same time, it will not be parsed.
    avg_interval -- the time in seconds to average over. avg_interval must be a multiple of TRI.
    """

    def __init__(self, file_obj, start_time=None, end_time=None, avg_interval=None):
        self.f = load_file(file_obj)
        self.coefficients = self.f.host_storage
        self.header = self.f.header

        parse_start_time = start_time if start_time else datetime.datetime(1970, 1, 1)
        parse_end_time = end_time if end_time else datetime.datetime(2038, 1, 1)
        avg_interval = avg_interval if avg_interval else 0

        assert type(parse_start_time) == datetime.datetime, 'start_time must be a datetime object'
        assert type(parse_end_time) == datetime.datetime, 'end_time must be a datetime object'

        file_start_time = self.f.page_start_times[0]
        last_interval_time = file_start_time + self.duration()

        assert parse_start_time < last_interval_time, 'start_time is after file end time'
        assert parse_end_time > parse_start_time, 'end_time must be greater than start_time'
        assert parse_end_time > file_start_time, 'end_time is before file start time'

        if avg_interval:
            assert avg_interval % self.interval() == 0, 'avg_interval must be a multiple interval'

        if parse_start_time < file_start_time:
            self.first_interval = 0
        else:
            self.first_interval = int(ceil((parse_start_time - file_start_time).total_seconds() / self.interval()))

        if parse_end_time >= last_interval_time:
            self.last_interval = self.n_intervals()
        else:
            # Exclusive end point
            self.last_interval = int(ceil((parse_end_time - file_start_time).total_seconds() / self.interval()))

        if avg_interval:
            assert (self.last_interval - self.first_interval) >= (avg_interval // self.interval()), \
                'time range resulted in no data'
        else:
            assert self.last_interval > self.first_interval, 'time range resulted in no data'

        self.avg_interval = avg_interval
        self.current_interval = self.first_interval


    def n_intervals(self):
        raise NotImplementedError

    def duration(self):
        raise NotImplementedError

    def interval(self):
        raise NotImplementedError


class TemperatureReader(Reader):
    """
    Create a generator to return temperature samples from file_obj.

    Keyword arguments:
    see Reader base class for a description of the keyword arguments
    """

    def __init__(self, file_obj, start_time=None, end_time=None, avg_interval=None):
        super(TemperatureReader, self).__init__(file_obj, start_time, end_time, avg_interval)

    def interval(self):
        return self.f.header['TRI']

    def duration(self):
        return datetime.timedelta(seconds=(self.f.n_temperature_intervals + 1) * self.f.header['TRI'])

    def n_intervals(self):
        return self.f.n_temperature_intervals

    def __iter__(self):
        if self.avg_interval:
            samples_per_avg_interval = self.avg_interval // self.f.header['TRI']
            for i in range(self.first_interval, self.last_interval-samples_per_avg_interval, samples_per_avg_interval):
                temperature = []
                time = self.f.page_start_times[0] + datetime.timedelta(seconds=i*self.f.header['TRI'])
                for j in range(samples_per_avg_interval):
                    temperature.append(self.f.read_temperature(i+j))
                temp_avg = sum(temperature) / samples_per_avg_interval
                yield time, temp_to_si(temp_avg, self.coefficients)

        else:
            for i in range(self.first_interval, self.last_interval):
                time = self.f.page_start_times[0] + datetime.timedelta(seconds=i*self.f.header['TRI'])
                temperature = self.f.read_temperature(i)
                yield time, temp_to_si(temperature, self.coefficients)  # convert to temperature


class OrientReader(Reader):
    """
    Return an iterator that produces calibrated acceleration and magnetometer values.

    Keyword arguments:
    see Reader base class for a description of the keyword arguments
    """

    def __init__(self, file_obj, start_time=None, end_time=None, avg_interval=None):
        super(OrientReader, self).__init__(file_obj, start_time, end_time, avg_interval)
        self.cache = []

    def interval(self):
        return self.f.header['ORI']

    def duration(self):
        return datetime.timedelta(seconds=(self.f.n_orient_intervals + 1) * self.f.header['ORI'])

    def n_intervals(self):
        return self.f.n_orient_intervals

    def __iter__(self):
        return self

    def next(self):
        # TODO what if one or both channels disabled?
        if self.avg_interval:
            # t is the start time of the interval block
            t = self.f.page_start_times[0] + datetime.timedelta(seconds=self.current_interval*self.f.header['ORI'])
            a_avg, m_avg = [], []
            samples_per_avg_interval = (self.avg_interval // self.f.header['ORI']) * self.f.header['BMN']
            while len(a_avg) < samples_per_avg_interval:
                if self.current_interval == self.last_interval:
                    raise StopIteration
                a, m = self.f.read_orient(self.current_interval)
                self.current_interval += 1
                a_avg.extend(a)
                m_avg.extend(m)

            accel = tuple([float(sum(col)/len(col)) for col in zip(*a_avg)])
            mag = tuple([float(sum(col)/len(col)) for col in zip(*m_avg)])

            return t, accel_to_si(accel, self.coefficients), mag_to_si(mag, self.coefficients)

        else:
            if len(self.cache) == 0:
                if self.current_interval == self.last_interval:
                    raise StopIteration
                start_time = self.f.page_start_times[0] + datetime.timedelta(seconds=self.current_interval*self.f.header['ORI'])
                t = [start_time + datetime.timedelta(seconds=1/self.f.header['BMR']) * x for x in range(self.f.header['BMN'])]
                a, m = self.f.read_orient(self.current_interval)
                self.current_interval += 1
                self.cache = zip(t, a, m)

            time, accel, mag = self.cache.pop(0)
            return time, accel_to_si(accel, self.coefficients), mag_to_si(mag, self.coefficients)

    def __len__(self):
        if self.avg_interval:
            return (self.last_interval - self.first_interval) // self.avg_interval // self.f.header['ORI']
        else:
            return (self.last_interval - self.first_interval) * self.f.header['BMN']


class OdlFile(object):
    """
    This must be sub-classed.
    Base class for interacting with a Lowell Instruments LID file.
    """

    def __init__(self, file_obj):
        self._file = file_obj
        self.file_size = self._file_size()
        self.header = self._header()
        self.host_storage = self._host_storage()
        self.mini_header_length = self._mini_header_length()
        self.n_pages = self._n_pages()
        self.page_start_times = self._page_start_times()
        self.data_start = self._data_start()
        self.page_size = self._page_size()
        self.temperature_index, self.orient_index = self._build_sequence()
        self.major_interval_seconds = max(self.header['TRI'], self.header['ORI'])
        self.maj_interval_bytes = self._maj_interval_bytes()
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
        orient_bytes_per_sample = 0
        orient_bytes_per_sample += 6 if h['ACL'] else 0
        orient_bytes_per_sample += 6 if h['MGN'] else 0
        temp_start = []
        orient_start = []

        if h['ORI'] and h['TRI']:
            temp_start.append(0)
            if h['TRI'] > h['ORI']:
                for i in range(h['TRI'] // h['ORI']):
                    orient_start.append(h['BMN'] * orient_bytes_per_sample * i + 2)
            else:
                orient_start.append(2)
                for i in range(1, h['ORI'] // h['TRI']):
                    temp_start.append(h['BMN'] * orient_bytes_per_sample + i * 2)

        elif h['ORI']:
            orient_start.append(0)

        elif h['TRI']:
            temp_start.append(0)

        return temp_start, orient_start

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

        type_int = ['BMN', 'BMR', 'DPL', 'STS', 'ORI', 'TRI']
        type_bool = ['ACL', 'LED', 'MGN', 'TMP']
        self._file.seek(0, 0)
        this_line = self._file.readline()

        if this_line[:3] != 'HDS':
            raise LidError('HDS tag missing in main header.')

        header = {}
        # TODO add logic to avoid having to read the whole file should the HDE tag not appear
        this_line = self._file.readline()
        while not this_line.startswith('HDE'):
            tag = this_line[:3]
            if tag == 'LIS':  # Lis files have the logger info written in the header. This ignores it
                while not this_line.endswith('LIE\r\n'):
                    this_line = self._file.readline()
                this_line = self._file.readline()
                continue
            if tag == 'MHS' or tag == 'MHE':
                this_line = self._file.readline()
                continue
            value = this_line[4:]
            value = value.translate(None, '\r\n')
            if tag in type_int:
                value = int(value)
            elif tag in type_bool:
                value = bool(int(value))

            header[tag] = value
            this_line = self._file.readline()

        if self.__class__ == LisFile:
            # .lis files are averaged on board over the ori, essentially making the BMN 1.
            # If this 'hack' doesn't go here, the maj_int size is calculated incorrectly and the problem trickles down
            header['BMN'] = 1

        return header

    def _host_storage(self):
        """
        The host storage (calibration) coefficients with the coefficient tags as keys.
        """

        host_storage = {}
        file_pos = self._file.tell()  # Keep track of the file position
        self._file.seek(0)
        this_line = self._file.readline()
        while not this_line.startswith('HDE'):
            this_line = self._file.readline()
        hs_str = self._file.read(380)

        tag, _, hs_str = self._parse_tag(hs_str)
        if tag != 'HSS':
            raise LidError('HSS tag missing in main header.')

        while True:  # Read until the HSE tag is reached
            tag, value, hs_str = self._parse_tag(hs_str)
            if tag == 'HSE':
                break
            elif tag == 'RVN':  # RVN is the only int value. The rest are floats
                value = int(value)
            else:
                value = float(value)
            host_storage[tag] = value

        return host_storage


    def _parse_tag(self, hs_str):
        """
        Internal method for parsing a string of TLV values

        Parse the tag and value from a string and return the tag, value, and remainder.
        The hs_str has the following format: Three letter tag, 1 hex digit value length, value (of length "length byte")
        For example: AXX7-0.9987  --  tag = AXX, value length = 7, value = -0.9987
        This method only works for a host storage string. It doesn't work for the main header tags.
        """

        tag = hs_str[:3]
        if tag == 'HSS' or tag == 'HSE':
            return tag, None, hs_str[3:]
        else:
            if hs_str[3] not in '0123456789abcdefABCDEF':
                print 'ORD ', ord(hs_str[3])
                raise TypeError('Length character must be hexadecimal character.')
            length = int(hs_str[3], 16)
            value = hs_str[4:4+length]
            return tag, value, hs_str[4+length:]

    def _maj_interval_bytes(self):
        """
        Number of bytes in a major interval.

        A major interval is represents max(TRI, ORI) seconds of data.
        """

        h = self.header
        orient_bytes = 0
        orient_bytes += 6 if h['ACL'] else 0
        orient_bytes += 6 if h['MGN'] else 0

        if h['ORI'] and h['TRI']:
            if h['TRI'] > h['ORI']:
                n_bytes = h['TRI'] // h['ORI'] * h['BMN'] * orient_bytes + 2
            else:
                n_bytes = h['ORI'] // h['TRI'] * 2 + h['BMN'] * orient_bytes

        elif h['ORI']:
            n_bytes = h['BMN'] * orient_bytes

        elif h['TRI']:
            n_bytes = 2

        return n_bytes


    def _n_orient_intervals_per_page(self):
        """
        Number of orient intervals in a data page.

        An orient interval represents ORI seconds of data (BMN samples)
        """

        return self.n_maj_intervals_per_page * self.major_interval_seconds // self.header['ORI']


    def _n_temperature_intervals_per_page(self):
        """
        Number of temperature intervals in a data page.
        :return: int
        """
        # In the case of a lis file, n_maj_intervals_per_page is huge infinite, causing a huge return number
        return self.n_maj_intervals_per_page * self.major_interval_seconds // self.header['TRI']


    def read_temperature(self, n):
        """
        Return the nth raw temperature value
        """

        if self._file.closed:
            raise RuntimeError('File must be open to read data')

        # The page and the sample number within the page
        page_n, sample_n = divmod(n, self.n_temperature_intervals_per_page)

        # The major interval and sample within major interval
        maj_int_n, sample_n = divmod(sample_n, len(self.temperature_index))

        # Jump to the correct file position
        self._file.seek(self.data_start + page_n * self.page_size + self.mini_header_length + maj_int_n *
                        self.maj_interval_bytes + self.temperature_index[sample_n])

        temp = array.array('H')  # temperature is uint16
        temp.fromfile(self._file, 1)

        return temp[0]

    def _n_orient_intervals(self):
        """
        Number of orient intervals in the file
        """

        h = self.header  # alias to a shorter variable names

        last_page_bytes = self.file_size - (self.n_pages-1)*self.page_size - self.mini_header_length - self.data_start
        n_maj_int, rem = divmod(last_page_bytes, self.maj_interval_bytes)
        try:
            sub = [i for i, val in enumerate(self.orient_index) if val < rem][-1]
        except IndexError:
            sub = 0
        n_intervals = (self.n_pages-1)*self.n_orient_intervals_per_page + n_maj_int*len(self.orient_index)+sub

        return n_intervals

    def _n_temperature_intervals(self):
        """
        Number of temperature intervals in the file
        """

        h = self.header  # alias to a shorter variable names

        last_page_bytes = self.file_size - (self.n_pages-1)*self.page_size - self.mini_header_length - self.data_start
        n_maj_int, rem = divmod(last_page_bytes, self.maj_interval_bytes)
        try:
            sub = [i for i, val in enumerate(self.temperature_index) if val < rem][-1]
        except IndexError:
            sub = 0
        n_intervals = (self.n_pages-1)*self.n_temperature_intervals_per_page + n_maj_int*len(self.temperature_index)+sub

        return n_intervals

    def read_orient(self, n):
        """
        Read the nth orient interval.

        If BMN > 1 it will return a list of samples of length BMN.
        """

        if self._file.closed:
            raise RuntimeError('File must be open to read data')

        h = self.header  # alias to a shorter variable names

        # The page and the sample number within the page
        page_n, sample_n = divmod(n, self.n_orient_intervals_per_page)

        # The major interval and sample within major interval
        maj_int_n, sample_n = divmod(sample_n, len(self.orient_index))

        orient_samples = 0
        orient_samples += 3 if h['ACL'] else 0
        orient_samples += 3 if h['MGN'] else 0

        self._file.seek(self.data_start + page_n * self.page_size + self.mini_header_length + maj_int_n *
                        self.maj_interval_bytes + self.orient_index[sample_n])
        orient_raw = array.array('h')
        orient_raw.fromfile(self._file, orient_samples * h['BMN'])

        # Reshape the list into orient_samples columns
        orient_raw = zip(*[iter(orient_raw)] * orient_samples)

        # Separate out the accel and mag values
        if h['ACL'] and h['MGN']:
            accel = [row[0:3] for row in orient_raw]
            mag = [row[3:6] for row in orient_raw]

        elif h['ACL']:
            accel = [row[0:3] for row in orient_raw]
            mag = [[] for row in orient_raw]

        elif h['MGN']:
            accel = [[] for row in orient_raw]
            mag = [row[0:3] for row in orient_raw]

        elif not h['MGN'] and not h['ACL']:
            accel = [[] for row in orient_raw]
            mag = [[] for row in orient_raw]

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
        this_line = self._file.readline()
        if not this_line.startswith('MHS'):
            raise LidError('MHS tag missing on first data page.')

        while not this_line.startswith('MHE'):
            this_line = self._file.readline()

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
            this_line = self._file.readline()
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
            this_line = self._file.readline()
            if not this_line:  # tried reading for a non-existent page
                raise LidError('Page {} does not exist.'.format(page_n))
            if not this_line.startswith('MHS'):
                raise LidError('MHS tag missing on page {}.'.format(page_n))

            while True:  # Read until the CLK tag is reached
                this_line = self._file.readline()
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

