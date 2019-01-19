#!/usr/bin/env python3

import argparse
import logging
import time
from rfm69.rfm69 import Rfm69
import RPi.GPIO as GPIO
from protocol_kaku import KakuProtocol
from mqtt_daemon import MqttDaemon

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

def control_switch(chip, group_address, switch_id, on):
    tx_data = KakuProtocol.encode_message(group_address, False, on, switch_id)
    assert(len(tx_data) == payload_len)
    for _ in range(3):
        chip.send_data(tx_data)
        time.sleep(0.1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="RFM69 OOK switch control")
    parser.add_argument("--spibus", default=0, type=int, help="SPI bus number")
    parser.add_argument("--spidev", default=0, type=int, help="SPI device number")
    parser.add_argument("--address", "-a", type=lambda s: int(s, 0), help="Switch group address")
    parser.add_argument("--switch", "-s", type=int, help="Switch index")
    parser.add_argument("-o", "--on", action="store_true")
    parser.add_argument("-f", "--off", action="store_true")
    parser.add_argument("--debug", default=False, action="store_true",
                        help="Enable debug printouts")

    parser_mqtt = parser.add_argument_group("MQTT")
    parser_mqtt.add_argument("--mqtt", metavar="ADDRESS", help="MQTT broker address")
    parser_mqtt.add_argument("--tls-insecure", action="store_true", default=False,
                        help="Disable hostname verification against cert")
    parser_mqtt.add_argument("--tls-ca", help="CA certificate that has signed the server's certificate")
    parser_mqtt.add_argument("--username", "-u", help="Username")
    parser_mqtt.add_argument("--password", "-p", help="Password")

    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel('DEBUG')

    group = args.address
    switch = args.switch
    tx_data = None
    mqtt = None

    payload_len = 35

    if args.on or args.off:
        if group is None or switch is None:
            parser.error("Missing group address or switch")
        tx_data = KakuProtocol.encode_message(group, False, args.on, switch)
        assert(len(tx_data) == payload_len)
    elif args.mqtt:
        mqtt = MqttDaemon(args.mqtt, tls_insecure=args.tls_insecure,
                ca=args.tls_ca, username=args.username, password=args.password)
    else:
        parser.error("Missing --on or --off")

    GPIO.setmode(GPIO.BCM)
    resetpin = OutPin(22)
    rxled = LED(2)
    txled = LED(3)
    commled = LED(27)

    try:
        with Rfm69(args.spibus, args.spidev,
                resetpin=resetpin, rxled=rxled, txled=txled, commled=commled) as chip:

            chip.init_ook(payload_len=payload_len)
            chip.dump_regs()
            chip.rx_mode()
            for _ in range(0):
                print("RSSI:", chip.get_rssi())
                time.sleep(0.2)

            for _ in range(3):
                if tx_data is not None:
                    chip.send_data(tx_data)
                    time.sleep(0.1)

            if mqtt is not None:
                mqtt.set_message_callback(lambda group_address, switch_id, on:
                        control_switch(chip, group_address, switch_id, on))
                # This call won't return if all is well
                mqtt.run()
    finally:
        GPIO.cleanup()
