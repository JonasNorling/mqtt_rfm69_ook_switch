# OOK switch control with RFM69 from a Raspberry Pi

This is an experiment for sending messages to a 433 MHz switch with the KaKu protocol, using a RFM69HCW connected to a Raspberry Pi.


## Dependencies

- apt-get install python3-spidev
- apt-get install python3-rpi.gpio


## Raspberry Pi configuration

Enable the SPI bus driver with `raspi-config` or by adding `dtparam=spi=on` to `/boot/config.txt`. After rebooting, you should have `/dev/spidev0.0`.


## Inspirational links

- http://members.home.nl/hilcoklaassen/
- https://github.com/etrombly/RFM69/blob/master/RFM69.py
