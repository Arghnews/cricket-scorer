from smbus2 import SMBus

# Copied from
# https://kernel.googlesource.com/pub/scm/utils/i2c-tools/i2c-tools/+/v3.1.2/tools/i2cdetect.c
def i2c_detect(bus):
    i2c_device_addrs = set()
    for i in range(0, 128, 16):
        vals = []
        for j in range(0, 16):
            res = True
            try:
                k = i + j
                if (k >= 0x30 and k <= 0x37) or (k >= 0x50 and k <= 0x5f):
                    bus.read_byte(i + j)
                else:
                    bus.write_byte(i + j, 0)
            except Exception as e:
                res = False
            if res:
                i2c_device_addrs.add(i + j)
                #  vals.append("{}: {:3}".format(j, i + j))
            #  else:
                #  vals.append("{}: ---".format(j))
    return i2c_device_addrs

class TinyBusWrapper(SMBus):
    def __init__(self, i2c_addr, addrs, log):
        super(TinyBusWrapper, self).__init__(i2c_addr)

        self.faked = {}

        addrs = set(addrs)
        for _ in range(4):
            addrs_found = i2c_detect(self)
            if addrs_found.issuperset(addrs):
                return
            log.warning("Could not find i2c addresses",
                    ", ".join(str(hex(a)) for a in addrs - addrs_found),
                    "trying again")
            time.sleep(5)

        # If we get here then we assume the addresses are missing permanently
        missing_addrs = addrs - addrs_found
        for addr in missing_addrs:
            log.critical("Could not find expected i2c device on address:",
                    hex(addr), "using fake i2c instead")
            self.faked[addr] = 0x00

    def write_byte(self, addr, data, *args):
        if addr in self.faked:
            self.faked[addr] = data
            return
        return super().write_byte(addr, data, *args)

    def read_byte(self, addr, *args):
        if addr in self.faked:
            return self.faked[addr]
        return super().read_byte(addr, *args)
        #  return self.faked.get(addr, super().read_byte(addr, *args))
