from __future__ import division

'''
1-D data interpolation (table lookup).
'''

def check_monotonic(vector):
    prev_val = None
    for a in vector:
        if not prev_val:
            prev_val = a
            continue
        if a <= prev_val:
            raise(Exception, 'List must be monotonically increasing.')
        prev_val = a

def interp1(x, y, xx):
    check_monotonic(x)
    # check_monotonic(y)
    assert len(x) == len(y), 'Lists must be the same length'

    xl = [i for i, val in enumerate(x) if val <= xx][-1]
    xu = [i for i, val in enumerate(x) if val > xx][0]
    # if not any(xl) or not any(xu):
    #     raise(Exception, 'Value not in range')
    x0, y0 = (x[xl], y[xl])
    x1, y1 = (x[xu], y[xu])
    yy = y0 + (y1-y0)*(xx-x0)/(x1-x0)
    return yy
