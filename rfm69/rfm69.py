from .rfm69_registers import *
import spidev
import logging
import contextlib
import time

class Rfm69:
    def __init__(self, bus=0, device=0, resetpin=None, rxled=None, txled=None, commled=None):
        self.bus = bus
        self.device = device
        self.log = logging.getLogger("rfm69")
        self.resetpin = resetpin
        self.rxled = rxled
        self.txled = txled
        self.commled = commled
        self.inited = False

    def open(self):
        self.spi = spidev.SpiDev()
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = 8000000

    def close(self):
        if self.inited:
            self.write_reg(REG_OP_MODE, REG_OP_MODE_MODE_SLEEP)
        self.spi.close()
        self.spi = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    @contextlib.contextmanager
    def lit(led):
        if led is not None: led.on()
        yield led
        if led is not None: led.off()

    def read_reg(self, addr):
        x = self.spi.xfer([addr & 0x7f, 0xff])
        return x[1]

    def read_regs(self, addr, count):
        x = self.spi.xfer([addr & 0x7f, *(0xff,)*count])
        return x[1:]

    def write_reg(self, addr, *values):
        x = [(addr & 0x7f) | 0x80, *values]
        self.spi.xfer(x)

    def write_fifo(self, data):
        self.write_reg(REG_FIFO, *data)

    def pinreset(self):
        if self.resetpin is None:
            return
        self.resetpin.set(1)
        time.sleep(0.01)
        self.resetpin.set(0)
        time.sleep(0.05)

    @staticmethod
    def calc_frf(f):
        """Calculate FRF register settings for carrier in Hz"""
        fstep = 32e6 / 2**19
        return f // fstep

    @staticmethod
    def calc_bitrate(br_hz):
        """Calculate register setting for bitrate in Hz"""
        return 32e6 // br_hz

    def init_ook(self, carrier_freq=433.92e6, bitrate=4000, payload_len=64):
        assert(payload_len < 256)
        self.log.info("Initing RFM69 in OOK mode")
        self.pinreset()
        with self.lit(self.commled):
            r = self.read_reg(REG_VERSION)
        self.log.info("Version register: %x" % r)
        if r != 0x24:
            self.log.error("Found bad chip version %x" % r)
            raise RuntimeError("Bad chip version")

        reg_frf = self.calc_frf(carrier_freq)
        reg_br = self.calc_bitrate(bitrate)

        regs = [
            (REG_OP_MODE, REG_OP_MODE_MODE_STANDBY),
            (REG_DATA_MODUL, 0x08), # Packet OOK, unfiltered
            (REG_BITRATE_MSB, (reg_br >> 8) & 0xff),
            (REG_BITRATE_LSB, reg_br & 0xff),
            (REG_FRF_MSB, (reg_frf >> 16) & 0xff),
            (REG_FRF_MID, (reg_frf >> 8) & 0xff),
            (REG_FRF_LSB, reg_frf & 0xff),
            (REG_PREAMBLE_MSB, 0),
            (REG_PREAMBLE_LSB, 0), # No preamble
            (REG_SYNC_CONFIG, 0x00), # No sync word
            (REG_PACKET_CONFIG_1, 0x00), # Packets are fixed length, no CRC or whitening
            (REG_PAYLOAD_LENGTH, payload_len)
            ]

        with self.lit(self.commled):
            for addr, value in regs:
                self.write_reg(addr, value)
                readback = self.read_reg(addr)
                if readback != value:
                    self.log.error("Readback mismatch %x %x != %x" % (addr, readback, value))
                    raise RuntimeError("Readback mismatch")

        self.inited = True

    def go_to_mode(self, mode):
        self.write_reg(REG_OP_MODE, mode)
        # FIXME: Is this right/necessary?
        for _ in range(1000):
            if self.read_reg(REG_IRQ_FLAGS_1) & REG_IRQ_FLAGS_1_MODE_READY:
                return
        raise RuntimeError("Stuck opmode")

    def rx_mode(self):
        with self.lit(self.commled):
            self.go_to_mode(REG_OP_MODE_MODE_RX)

    def send_data(self, data):
        with self.lit(self.txled):
            # Go to standby while filling FIFO
            self.go_to_mode(REG_OP_MODE_MODE_STANDBY)
            assert(len(data) <= 66)
            self.write_fifo(data)
            self.go_to_mode(REG_OP_MODE_MODE_TX)

            for polls in range(1000):
                flags = self.read_reg(REG_IRQ_FLAGS_2)
                if flags & REG_IRQ_FLAGS_2_PACKET_SENT:
                    break
            else:
                self.go_to_mode(REG_OP_MODE_MODE_STANDBY)
                raise RuntimeError("Stuck TX")

            self.log.info("TX'ed in %d polls" % polls)
            self.log.info("We're now in mode %02x" % self.read_reg(REG_OP_MODE))
            self.go_to_mode(REG_OP_MODE_MODE_STANDBY)

    def get_rssi(self):
        with self.lit(self.commled):
            data = self.read_regs(REG_RSSI_CONFIG, 2)
            if data[0] & 0x01:
                return (-data[1])//2
            else:
                return 0

    def dump_regs(self):
        self.log.info("Registers:")
        line = ""
        for i in range(0x80):
            if i % 8 == 0:
                line = "  %#04x: " % i
            if i == 0: # Avoid reading FIFO
                r = 0
            else:
                r = self.read_reg(i)
            line += "%02x " % r
            if i % 8 == 7:
                self.log.info(line)
