#!/usr/bin/env python3

import sys
import time

# NOTE: timer starts in expired state - possibly this is not expected
# Granularity is seconds
# See https://docs.micropython.org/en/latest/library/utime.html

def make_countdown_timer(*, seconds):
    if sys.implementation.name == "micropython":
        time_now = lambda: time.ticks_ms()
        gen_next_valid = lambda: time_now() + seconds * 1000
        has_expired = lambda next_valid: \
                time.ticks_diff(next_valid, time_now()) < 0
    else:
        time_now = lambda: int(time.monotonic())
        gen_next_valid = lambda: time_now() + seconds
        has_expired = lambda next_valid: time_now() > next_valid
    return CountdownTimer(gen_next_valid, has_expired)

class CountdownTimer:

    def __init__(self, gen_next_valid, has_expired):
        self._next_valid = None
        self._expired = True

        self._gen_next_valid = gen_next_valid
        self._has_expired = has_expired

    def just_expired(self):
        if self._expired:
            return False
        self._expired = self._has_expired(self._next_valid)
        return self._expired

    def stop(self):
        self._expired = True

    def reset(self):
        self._next_valid = self._gen_next_valid()
        self._expired = False
        return self

def main(argv):
    t = make_countdown_timer(seconds = 5)
    # Yes side effects in asserts are bad but this is a quick test
    assert not t.just_expired()
    assert not t.just_expired()
    t.reset()
    assert not t.just_expired()
    assert not t.just_expired()
    time.sleep(5)
    assert not t.just_expired() # Bit dubious this one
    time.sleep(1)
    assert t.just_expired()
    assert not t.just_expired()
    t.reset()
    assert not t.just_expired()
    assert not t.just_expired()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
