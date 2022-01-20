"""
There have been several different iterations of calibration coefficients since the introduction of the MAT logger.
This module is responsible for managing how the various versions are interpreted and applied to raw data.

I'm not not worried about code duplication between subclasses. If a new rev is added, create a new subclass
"""

from __future__ import division
import struct
import math
import numpy as np

# TODO all the calculations need to be moved into numpy.
# TODO The various matrices need to be cached so they aren't built every read!


def create_converter(hs_string):
    """
    Factory function to return correct host storage class. hs_string is the host storage string from either the lid/lis
    file, or the RHS command.
    """

    if not hs_string:
        raise RuntimeError('hs_string is empty')

    if 'RVN' not in hs_string:  # Rev 1 host storage didn't mandate the RVN tag. If RVN is not present, assume Rev 1
        return V1Converter(hs_string)
    else:  # subsequent revs use a RVN tag.
        if 'RVN11' in hs_string:  # Just because it wasn't mandated doesn't mean it wasn't sometimes present
            return V1Converter(hs_string)
        elif 'RVN12' in hs_string:
            return V2Converter(hs_string)
        elif 'RVN13' in hs_string:
            return V3Converter(hs_string)
        else:
            raise RuntimeError('Unrecognized hs_string')


class Converter(object):
    """
    Base class. At this point, the only thing in common between Converter sub classes is the temperature conversion
    """

    def __init__(self):
        """ If no values are passed in, then hs_dict will contain default values """
        self.hs_dict = self._default_hs()  # load the default host storage values defined in baseclass...
        self.is_default_hs = True

    def temp_to_si(self, temp_raw):
        """
        Convert raw temperature values (unsigned int16) into degrees C.

        Keyword arguments:
        coefficients -- the calibration coefficients (host storage)
        """

        # This statement avoids a divide by zero error if the temperature sensor erroneously returns a zero
        temp_raw = 1 if temp_raw == 0 else temp_raw

        h = self.hs_dict  # alias for cleaner math below

        temp = (temp_raw * h['TMR']) / (65535 - temp_raw)  # Convert to resistance values
        temp = 1 / (h['TMA'] + h['TMB'] * math.log(temp) + h['TMC'] * (math.log(temp)) ** 3) - 273.15
        return temp

    def _default_hs(self):
        raise NotImplementedError


class V1Converter(Converter):
    def __init__(self, hs_string):
        super(V1Converter, self).__init__()
        tag = hs_string[0:3]
        if tag != 'HSS':  # This allows a logger with blank host storage to operate with V1 default host storage
            return
        hs_string = hs_string[3:]
        tag = hs_string[0:3]
        while tag != 'HSE':
            data_length = int(hs_string[3], 16)
            value = float(hs_string[4:4 + data_length])
            self.hs_dict[tag] = value
            hs_string = hs_string[4 + data_length:]
            tag = hs_string[0:3]

        if not self.hs_dict == self._default_hs():
            self.is_default_hs = False

    def accel_to_si(self, accel_raw):
        """
        Convert raw acceleration values (signed int16) into g.

        Arguments:
        accel_raw -- a tuple of format (Ax, Ay, Az)
        """

        hs = self.hs_dict
        accel = [float(val) / 1024 for val in accel_raw]

        gain = [hs['AXB'], hs['AYB'], hs['AZB']]
        offset = [hs['AXA'], hs['AYA'], hs['AZA']]

        # accel[:] = [-accel[i] / gain[i] - offset[i] for i in range(3)] why the [:]? commenting out for now
        accel = [-accel[i] / gain[i] - offset[i] for i in range(3)]
        return accel

    def mag_to_si(self, mag_raw):
        hs = self.hs_dict
        mag = [float(val) for val in mag_raw]
        offset = [hs['MXA'], hs['MYA'], hs['MZA']]
        scale = [hs['MXS'], hs['MYS'], hs['MZS']]
        mag[:] = [(mag[i] + offset[i]) * scale[i] for i in range(3)]
        return mag

    def format_for_write(self):
        """
        This generator function formats the host storage dict for writing to the logger.
        """

        yield 'RVN11'  # Prior to V3, RVN didn't need to be first, but what the heck...
        for key in self.hs_dict:
            if key == 'RVN':
                continue  # RVN was already written above
            value = self.hs_dict[key][:15]  # truncate to 15 characters (or less)
            length_hex = '%x' % len(value)  # hex length as an ascii character
            yield key + length_hex + value

    def _default_hs(self):
        return {'AXB': 1, 'AYB': 1, 'AZB': 1, 'AXA': 0, 'AYA': 0, 'AZA': 0,
                'MXS': 1, 'MYS': 1, 'MZS': 1, 'MXA': 0, 'MYA': 0, 'MZA': 0,
                'TMO': 0, 'TMR': 10000,
                'TMA': 0.0011238100354, 'TMB': 0.0002349457073, 'TMC': 0.0000000848361}


class V2Converter(Converter):
    def __init__(self, hs_string):
        super(V2Converter, self).__init__()
        tag = hs_string[0:3]
        assert tag == 'HSS', 'HS string must begin with HSS'
        hs_string = hs_string[3:]
        tag = hs_string[0:3]
        while tag != 'HSE':
            data_length = int(hs_string[3], 16)
            value = float(hs_string[4:4 + data_length])
            self.hs_dict[tag] = value
            hs_string = hs_string[4 + data_length:]
            tag = hs_string[0:3]

        if not self.hs_dict == self._default_hs():
            self.is_default_hs = False

    def accel_to_si(self, accel_raw):
        """
        Convert raw acceleration values (signed int16) into g.

        Arguments:
        accel_raw -- a tuple of format (Ax, Ay, Az)
        """
        hs = self.hs_dict
        accel = [float(val) / 1024 for val in accel_raw]

        gain = [[hs['AXX'], hs['AXY'], hs['AXZ']],
                [hs['AYX'], hs['AYY'], hs['AYZ']],
                [hs['AZX'], hs['AZY'], hs['AZZ']]]
        offset = [hs['AXV'], hs['AYV'], hs['AZV']]
        cubic = [hs['AXC'], hs['AYC'], hs['AZC']]

        # accel = gain * accel + offset + cubic * accel ** 3
        accel[:] = [sum([gain[row][col] * accel[col] for col in range(3)]) + offset[row] + cubic[row] *
                    accel[row] ** 3 for row in range(3)]
        return accel

    def mag_to_si(self, mag_raw):
        """
        Convert raw magnetometer values (signed int16) into mG.

        Arguments:
        mag_raw -- a tuple of format (Mx, My, Mz)
        """

        hs = self.hs_dict
        mag = [float(val) for val in mag_raw]
        hi = [hs['MXV'], hs['MYV'], hs['MZV']]
        si = [[hs['MXX'], hs['MXY'], hs['MXZ']],
              [hs['MYX'], hs['MYY'], hs['MYZ']],
              [hs['MZX'], hs['MZY'], hs['MZZ']]]

        # TODO make sure the following two lines are working
        mag[:] = [mag[i] + hi[i] for i in range(3)]
        mag[:] = [sum([mag[i] * si_row[i] for i in range(3)]) for si_row in si]
        return mag

    def pressure_to_psi(self, pressure_raw):
        """
        Convert raw pressure values (signed int16) into psi.

        PRA is the offset, PRB is the slope.
        pressure = PRB * pressure_raw + PRA

        Arguments:
        pressure_raw -- the raw pressure value from the pressure sensor
        """

        hs = self.hs_dict
        return hs['PRB'] * pressure_raw + hs['PRA']

    def _default_hs(self):
        return {'AXX': 1, 'AXY': 0, 'AXZ': 0, 'AXC': 0, 'AXV': 0, 'AYX': 0, 'AYY': 1, 'AYZ': 0, 'AYC': 0,
                'AYV': 0, 'AZX': 0, 'AZY': 0, 'AZZ': 1, 'AZC': 0, 'AZV': 0, 'RVN': 2, 'TMO': 0, 'TMR': 10000,
                'TMA': 0.0011238100354, 'TMB': 0.0002349457073, 'TMC': 0.0000000848361,
                'MXX': 1, 'MXY': 0, 'MXZ': 0, 'MXV': 0, 'MYX': 0, 'MYY': 1, 'MYZ': 0, 'MYV': 0,
                'MZX': 0, 'MZY': 0, 'MZZ': 1, 'MZV': 0, 'PRA': 0, 'PRB': 1}


class V3Converter(Converter):
    # TODO do NOT store values in binary. Use ascii85 to encode 4 byte singles into 5 bytes of printable characters.
    def __init__(self, hs_string):
        super(V3Converter, self).__init__()
        assert hs_string.startswith('HSSRVN13'), 'V3 host storage sting must begin with HSSRVN13'
        hs_string = hs_string[8:]
        tag = hs_string[0:3]
        while tag != 'HSE':
            value_str = hs_string[3:7]
            value = struct.unpack('<f', value_str)[0]
            self.hs_dict[tag] = value
            hs_string = hs_string[7:]
            tag = hs_string[0:3]

        if not self.hs_dict == self._default_hs():
            self.is_default_hs = False

        hs = self.hs_dict  # alias to shorter name

        self.accel_xaxis = np.array([[hs['AXX'], hs['AXY'], hs['AXZ']],
                                     [hs['AYX'], hs['AYY'], hs['AYZ']],
                                     [hs['AZX'], hs['AZY'], hs['AZZ']]])
        self.accel_offset = np.array([hs['AXV'], hs['AYV'], hs['AZV']])
        self.accel_cubic = np.array([[hs['AXC'], 0, 0],
                                     [0, hs['AYC'], 0],
                                     [0, 0, hs['AZC']]])

        self.mag_hard_iron = np.array([hs['MXV'], hs['MYV'], hs['MZV']])
        self.mag_soft_iron = np.array([[hs['MXX'], hs['MXY'], hs['MXZ']],
                                      [hs['MYX'], hs['MYY'], hs['MYZ']],
                                      [hs['MZX'], hs['MZY'], hs['MZZ']]])

        # Cross Axis Misalignment Correction Transformation Matrix for magnetometers
        self.mag_xaxis = np.array([[hs['GXX'], hs['GXY'], hs['GXZ']],
                                   [hs['GYX'], hs['GYY'], hs['GYZ']],
                                   [hs['GZX'], hs['GZY'], hs['GZZ']]])

    def accel_to_si(self, accel_raw):
        """
        Convert raw acceleration values (signed int16) into g.

        Arguments:
        accel_raw -- a tuple of format (Ax, Ay, Az)
        """
        accel_raw = np.array(accel_raw) / 1024
        accel = self.accel_xaxis.dot(accel_raw) + self.accel_offset + self.accel_cubic.dot(accel_raw**3)

        # accel = gain * accel + offset + cubic * accel ** 3
        # accel[:] = [sum([gain[row][col] * accel[col] for col in range(3)]) + offset[row] + cubic[row] *
        #             accel[row] ** 3 for row in range(3)]
        return accel

    def mag_to_si(self, mag_raw):
        """
        Convert raw magnetometer values (signed int16) into mG.

        Arguments:
        mag_raw -- accel_raw -- a tuple of format (Mx, My, Mz)
        """
        mag = self.mag_soft_iron.dot((mag_raw + self.mag_hard_iron).transpose()).transpose()
        mag = mag.dot(self.mag_xaxis)
        return mag

    def _default_hs(self):
        return {'AXX': 1, 'AXY': 0, 'AXZ': 0, 'AXC': 0, 'AXV': 0, 'AYX': 0, 'AYY': 1, 'AYZ': 0, 'AYC': 0,
                'AYV': 0, 'AZX': 0, 'AZY': 0, 'AZZ': 1, 'AZC': 0, 'AZV': 0, 'RVN': 2, 'TMO': 0, 'TMR': 10000,
                'TMA': 0.0011238100354, 'TMB': 0.0002349457073, 'TMC': 0.0000000848361,
                'MXX': 1, 'MXY': 0, 'MXZ': 0, 'MXV': 0, 'MYX': 0, 'MYY': 1, 'MYZ': 0, 'MYV': 0,
                'MZX': 0, 'MZY': 0, 'MZZ': 1, 'MZV': 0, 'GXX': 1, 'GXY': 0, 'GXZ': 0, 'GYX': 0,
                'GYY': 1, 'GYZ': 0, 'GZX': 0, 'GZY': 0, 'GZZ': 1, 'TAX': 1, 'TAY': 1, 'TAZ': 1,
                'TMX': 1, 'TMY': 1, 'TMZ': 1}
