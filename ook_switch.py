#!/usr/bin/env python3

import argparse
import logging
import time
from rfm69.rfm69 import Rfm69
import RPi.GPIO as GPIO

class OutPin:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)

    def set(self, value):
        GPIO.output(self.pin, value)

class LED(OutPin):
    """gpiozero-like representation of LEDs"""

    def on(self):
        self.set(0)

    def off(self):
        self.set(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="RFM69 OOK switch control")
    parser.add_argument("--spibus", default=0, type=int, help="SPI bus number")
    parser.add_argument("--spidev", default=0, type=int, help="SPI device number")
    parser.add_argument("--debug", default=False, action="store_true",
                        help="Enable debug printouts")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel('DEBUG')

    GPIO.setmode(GPIO.BCM)
    resetpin = None
    rxled = LED(2)
    txled = LED(3)
    commled = LED(27)

    tx_data = bytearray([0x00, 0xff])

    try:
        with Rfm69(args.spibus, args.spidev,
                resetpin=resetpin, rxled=rxled, txled=txled, commled=commled) as chip:
            chip.init_ook()
            chip.dump_regs()
            chip.rx_mode()
            for _ in range(10):
                print("RSSI:", chip.get_rssi())
                time.sleep(0.5)
            chip.send_data(tx_data)
    finally:
        GPIO.cleanup()
