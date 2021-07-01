def write_byte_safe(bus, log, addr, data):
    try:
        bus.write_byte(addr, data)
        return True
    except OSError as e:
        log.error("Bus write error. Bus:", bus, "addr:", hex(addr), "writing raw data:", hex(data),
                  ", error:", str(e))
        return False


def read_byte_else(bus, log, addr, default=0):
    try:
        return bus.read_byte(addr)
    except OSError as e:
        log.error("Error reading byte. Bus:", bus, "addr:", hex(addr), ", error:", str(e))
        return default


# Used in the sanitise_received_score function to correctly turn off leading
# zeroes
_SCOREBOARD_DIGITS_ORDER = [3, 1, 2, 3]


def sanitise_received_score(log, score, expected_length, blank_out_leading_zeroes):
    assert type(score) is bytes
    assert type(expected_length) is int
    assert type(blank_out_leading_zeroes) is bool

    if len(score) != expected_length:
        log.error("Received score of incorrect length:", len(score), "- expected:",
                  expected_length)
        return None

    # Should be size 9 bytes type, little endian, convert to list of ints
    score = list(score)

    # Zero out leading zeroes so the display doesn't have them shining
    if blank_out_leading_zeroes:
        score = _suppress_leading_zeroes(score, *_SCOREBOARD_DIGITS_ORDER)

    if any(True for val in score if val not in INT_TO_DISPLAY):
        log.error("Received score with invalid digit, see full score:", score,
                  "- digits should be one of:", INT_TO_DISPLAY.keys())
        return None

    return score


INT_TO_DISPLAY = {
    0: 0x7e,
    1: 0x30,
    2: 0x6d,
    3: 0x79,
    4: 0x33,
    5: 0x5b,
    6: 0x1f,
    7: 0x70,
    8: 0x7f,
    9: 0x73,
    None: 0x00,
}

display_to_int = {v: k for k, v in INT_TO_DISPLAY.items()}
assert len(INT_TO_DISPLAY) == len(display_to_int)


# Helper function - mutates in place slice of list ba in place transforming
# leading zeroes
def _map_while(ba, i, j, zero, replaced_with):
    for i in range(i, j):
        if ba[i] != zero:
            return
        ba[i] = replaced_with


# Should be called AFTER mapping through code_to_digit
def _suppress_leading_zeroes(vals, *number_lengths):
    leading_zero = 0
    replaced_with = None

    n = 0
    for j in number_lengths:
        _map_while(vals, n, n + j, leading_zero, replaced_with)
        n += j
    return vals
