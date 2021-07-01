import sys

from .utility import int_to_bytes
from .sequence_numbers import SequenceNumber


class Packet:

    UNKNOWN_ID = 0

    ID_SIZE = 4
    SEQUENCE_NUMBER_SIZE = 4
    # This tight coupling sucks - maybe some kind of factory to fix, lot of work
    PAYLOAD_SIZE = 9

    # https://stackoverflow.com/a/32720603
    # Micropython class objects do not seem to have this mappingproxy object
    # called "__dict__" for accessing class attributes.
    # Would've used.
    # return sum(v for k, v in cls.__dict__.items() if k.isupper() and k.endswith("_SIZE"))
    @classmethod
    def packet_size(cls):
        return cls.ID_SIZE * 3 + cls.SEQUENCE_NUMBER_SIZE + cls.PAYLOAD_SIZE
        # return sum(getattr(cls, x) for x in dir(cls) if x.isupper()
        #         and x.endswith("_SIZE") and type(getattr(cls, x)) is int)

    @classmethod
    def payload_as_string(cls, payload):
        assert isinstance(payload, bytes)
        return " ".join(str(x) for x in payload)

    def __str__(self):
        # Don't use {:,} for sequence number, it tries to use it as int or some
        # such
        return "{{from: {:,}, to: {:,}, id_change: {:,}, seq_num: {}, data: {}}}".format(
            self.sender, self.receiver, self.id_change, self.sequence_number,
            Packet.payload_as_string(self.payload))

    def __init__(self,
                 *,
                 sender,
                 receiver,
                 id_change=0,
                 sequence_number=SequenceNumber(n=0, bytes_=SEQUENCE_NUMBER_SIZE),
                 payload=bytes(PAYLOAD_SIZE)):

        cls = type(self)
        assert sender < 2**(cls.ID_SIZE * 8)
        assert receiver < 2**(cls.ID_SIZE * 8)
        assert id_change < 2**(cls.ID_SIZE * 8)
        assert type(sequence_number) is SequenceNumber
        assert sequence_number.__int__() < 2**(cls.SEQUENCE_NUMBER_SIZE * 8)
        assert type(payload) is bytes
        assert len(payload) is cls.PAYLOAD_SIZE

        self.sender = sender
        self.receiver = receiver
        self.id_change = id_change
        self.sequence_number = sequence_number
        self.payload = payload

    def __bytes__(self):
        cls = type(self)
        ba = bytearray()
        ba += int_to_bytes(self.sender, cls.ID_SIZE)
        ba += int_to_bytes(self.receiver, cls.ID_SIZE)
        ba += int_to_bytes(self.id_change, cls.ID_SIZE)
        ba += int_to_bytes(self.sequence_number.__int__(), cls.SEQUENCE_NUMBER_SIZE)
        ba += self.payload
        return bytes(ba)

    @classmethod
    def from_bytes(cls, bytes_):
        # print("Received in from_bytes:", bytes_)
        if bytes_ is None:
            return None
        assert len(bytes_) == Packet.packet_size()
        # Holy lack of DRY batman. This is so error prone, I hate it.
        offsets = offset_slices(bytes_, cls.ID_SIZE, cls.ID_SIZE, cls.ID_SIZE,
                                cls.SEQUENCE_NUMBER_SIZE, cls.PAYLOAD_SIZE)
        val = lambda: next(offsets)
        packet = Packet(sender=int.from_bytes(val(), sys.byteorder),
                        receiver=int.from_bytes(val(), sys.byteorder),
                        id_change=int.from_bytes(val(), sys.byteorder),
                        sequence_number=SequenceNumber(int.from_bytes(val(), sys.byteorder),
                                                       bytes_=cls.SEQUENCE_NUMBER_SIZE),
                        payload=val())
        try:
            val()
        except StopIteration:
            pass
        else:
            assert False, "Should've raised StopIteration, byte offsets don't "\
                "consume all of input"
        return packet

    def __eq__(self, other):
        if type(other) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__


def offset_slices(bytes_, *offsets):
    assert sum(offsets) == len(bytes_)
    acc = 0
    for offset in offsets:
        yield bytes_[acc:acc + offset]
        acc += offset


if __name__ == "__main__":
    sys.exit(main(sys.argv))
