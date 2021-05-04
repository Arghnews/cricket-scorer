from smbus2 import SMBus
#  from collections import namedtuple
from recordclass import recordclass

AddrState = recordclass("AddrState", [
    "val",
    "cached_reads",
    "cached_writes",
    "fake"
    ])
AddrState.__new__.__defaults__ = (None, 0, 0, False)

# Convert int or (int, int) to hex printout for logging
def hex_key_to_str(item):
    def is_convertible_to_hex(v):
        try:
            _ = hex(v)
            return True
        except TypeError:
            return False
    def is_iterable(v):
        try:
            _ = (x for x in v)
            return True
        except TypeError:
            return False

    if is_convertible_to_hex(item):
        return str(hex(item))
    elif is_iterable(item) and all(is_convertible_to_hex(v) for v in item):
        return ", ".join(str(hex(v)) for v in item)
    else:
        return str(item)

class BusWrapper:
    def __init__(self, bus_address, log, *, caching = True,
            num_cached_reads_before_update = 20,
            num_cached_writes_before_update = 10):

        #{addr: (val, cached_reads, cached_writes, enabled)}

        self.bus = SMBus(1)
        self.log = log

        self.addr_states = {}
        self.caching = caching
        self.num_cached_reads_before_update = num_cached_reads_before_update
        self.num_cached_writes_before_update = num_cached_writes_before_update

    def write_byte(self, addr, val, force = False):
        write_func = lambda: self.bus.write_byte(addr, val)
        return self._do_write_byte(addr, val, force, write_func)

    def write_i2c_block_data(self, addr, offset, data, force = False):
        key = (addr, offset)
        write_func = lambda: self.bus.write_i2c_block_data(addr, offset, data)
        return self._do_write_byte(key, data, force, write_func)

    def _do_write_byte(self, addr, val, force, write_func):

        addr_state = self.addr_states.setdefault(addr, AddrState())

        if addr_state.fake:
            self.log.debug("Returning faked value for write:", addr_state.val)
            addr_state.val = val
            return True

        # Conditions where we actually do the write
        if val is None or val != addr_state.val or not self.caching or force \
                or addr_state.cached_writes >= \
                self.num_cached_writes_before_update:
            success = False

            try:
                write_func()
                success = True
            except OSError as e:
                self.log.error("Bus write error. Bus:", self.bus, "addr:",
                        hex_key_to_str(addr), "writing raw data:",
                        hex_key_to_str(val), ", error:", str(e))
                success = False

            # Reset both cached read and write counters
            addr_state.cached_reads = 0
            addr_state.cached_writes = 0

            # If an error occured, set the addr_state.val to None to force a
            # read/write next time
            addr_state.val = val if success else None
            return success

        # If we get here, we are writing the cached value and haven't exceeded
        # the number of cached writes, so increment the cache counter and return
        # True
        addr_state.cached_writes += 1
        self.log.debug("Write cached for ", hex_key_to_str(addr), val)
        return True

    def read_byte_else(self, addr, *, default, force = False):
        addr_state = self.addr_states.setdefault(addr, AddrState())

        if addr_state.fake:
            return default if addr_state.val is None else addr_state.val

        # Conditions where we actually do the read
        if addr_state.val is None or not self.caching or force or \
                addr_state.cached_reads >= self.num_cached_reads_before_update:

            success = False
            try:
                val = self.bus.read_byte(addr)
                success = True
            except OSError as e:
                self.log.error("Error reading byte. Bus:", self.bus, "addr:",
                        hex_key_to_str(addr), ", error:", str(e))
                success = False

            addr_state.cached_reads = 0

            # If an error occured, set the addr_state.val to None to force a
            # read/write next time
            addr_state.val = val if success else None

            return val if success else default

        # If we get here, use the cached value
        addr_state.cached_reads += 1
        return addr_state.val

    def set_faking_of_addr(self, addr, state):
        pass

