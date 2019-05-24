#!/usr/bin/env micropython
#!/usr/bin/env python3

import sys
import array

def f(*, mux, chan, **kwargs):
    print(mux)
    print(chan)
    print(kwargs)

def main(argv):
    try:
        i = 9
        1 / 0
    except Exception:
        pass
    finally:
        i += 1
        print(i)

    f(mux = 1, chan = 2, a = 3, b = 4)

    # mm = [0, 1, 2]
    mm = [0, 1, 2]
    cc = [3, 4, 5]
    mux_channels = [(m, bytes([c]))
            for m in mm
            for c in cc]
    # print(mux_channels)
    # for m, c in mux_channels:
    #     print(type(m), type(c))
    for b in bytes([1,2,3]):
        print(b)
    # mc = zip(mm, cc)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
