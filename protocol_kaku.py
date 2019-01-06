#
# Protocol implementation of the 433 MHz OOK protocol known as
#  - KaKu
#  - self-learning Nexa (Arctech?) remote
#
# 1. Application protocol: Each message sent over the radio is a 32
# bit word, sent MSB first. The bit definitions are, from MSB to LSB:
#
#   26 bits: group address (unique for each remote control)
#    1 bit: group flag (for addressing all switches of this group)
#    1 bit: action on/off flag
#    4 bits: switch id within this group (button number on remote)
#    (4 bits optional: dimmer level)
#
# An example from my Nexa remote, decoded, same order as on oscilloscope:
#
#  0 0 0 1 1 0 0 0 0 1 1 1 1 1 1 0 0 0 0 0 1 0 0 0 1 0 0 1 0 0 1 0
# 0x     1       8       7       e       0       8       9       2
#  \_________________________________________________/ \/\/\_____/
#                     group address                   gr on switch
#
# 2. Manchester encoding: The bits are manchester encoded when sent
# over the air, so one application bit is sent as two bits (symbols)
# over the air. An application layer 0 bit is sent on the radio as a
# 0 symbol and a 1 symbol. A 1 is sent as 1-0. (Or the other way
# around, depending on how you define the radio layer symbols).
#
# Dimming: An absolute dimming level can be appended to the message.
# The on/off bit then takes on a third value is then sent as 00 in
# the manchester coded representation.
#
# The message begins with a START symbol and ends with a STOP symbol.
#
# 3. Symbols on the radio layer: The radio uses on off keying (OOK),
# where the carrier is sent for a high level and no carrier is sent
# for a low level. The symbols are defined thus:
#
#        |----|
# START  |    |
#        |    |_________________________________________________
#          1T                          10T
#
#        |----|
#   0    |    |
#        |    |_____
#          1T   1T
#
#        |----|
#   1    |    |
#        |    |_________________________
#          1T             5T
#
#        |----|
# STOP   |    |
#        |    |____________________
#          1T           4T
#
# The time unit T is about 260us. A 0 takes 0.52ms and 1 takes 1.56ms
# to send, so an application layer message takes about 71ms to send
# in its entirety.
#
# The first bits (00011000) of the example message look like this on
# the modulation input of the radio transmitter (I represents
# carrier, _ represents no carrier):
# I__________I_I_____I_I_____I_I_____I_____I_I_____I_I_I_____I_I_____I_I_____...
#
# start      0 1     0 1     0 1     1     0 1     0 0 1     0 1     0 1     ...
#

import logging

class KakuProtocol:
    BIT_TIME = 260e-6

    @staticmethod
    def encode_bytestream(bits):
        return bytearray(0)
    
    @staticmethod
    def bits(d, width):
        out = "{0:0{width}b}".format(d, width=width)
        assert(len(out) == width)
        return list(map(int, out))

    @staticmethod
    def bitlist_to_bytearray(bits):
        """Return a left-aligned byte representation of the bits, zero-padded"""
        out = bytearray()
        n = 0
        for i, b in enumerate(bits):
            n = (n << 1) | b
            if i % 8 == 7:
                out.append(n)
                n = 0
        i += 1
        if i % 8:
            out.append(n << (8 - (i % 8)))
        return out

    @staticmethod
    def symbol(bit):
        return {
            0: [ 1, 0, 1, 0, 0, 0, 0, 0 ],
            1: [ 1, 0, 0, 0, 0, 0, 1, 0 ],
            "start": [ 1 ] + [ 0 ] * 10,
            "stop": [ 1 ] + [ 0 ] * 10
        }[bit]

    @classmethod
    def encode_message(cls, group_address, group_flag, on, switch_id, dim=None):
        log = logging.getLogger("proto")
        log.debug("Encoding group=%06x switch=%d on=%d" % (group_address, switch_id, int(on)))
        bits = cls.symbol("start")
        for b in cls.bits(group_address, 26):
            bits += cls.symbol(b)
        bits += cls.symbol(int(group_flag == True))
        bits += cls.symbol(int(on == True))
        for b in cls.bits(switch_id, 4):
            bits += cls.symbol(b)
        bits += cls.symbol("stop")
        return cls.bitlist_to_bytearray(bits)

if __name__ == "__main__":
    tx_data = KakuProtocol.encode_message(0xaaaaaa, False, True, 1)
    print(tx_data.hex())
