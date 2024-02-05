#!/usr/bin/env python3
# -*- coding: utf-8 -*-


''' 
Modified to remove ncurses and logging functionality.



Raspberry Pi x708 Power Management Control

Copyright (C) 2020 Fernando Vano Garcia

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

                                Fernando Vano Garcia <fernando@fervagar.com>
'''

from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime
from sys import stderr
import subprocess
import gpiozero
import struct
import smbus
import time
import sys
import os

# --------------------------------------- #
# -- Constants -- #

# Using BCM numbering for GPIO :: https://pinout.xyz/pinout
_GPIO_PIN_PWR_BUTTON = 5    # Physical/Board pin 29
_GPIO_PIN_AC_LOST = 6       # Physical/Board pin 31
_GPIO_PIN_PWR_TRIGGER = 12  # Physical/Board pin 32

I2C_BATTERY_ADDR = 0x36

# --------------------------------------- #
# -- Lambdas & Types -- #

pos_int = lambda x: int(x) if is_positive_int(x) else raise_ex(
    ArgumentTypeError("'%s' is not a positive int value" % str(x))
)
pos_float = lambda x: float(x) if is_positive_float(x) else raise_ex(
    ArgumentTypeError("'%s' is not a positive float value" % str(x))
)

# --------------------------------------- #

def error(*msg):
    print(*msg, file=stderr)
    # stderr.flush()


def is_positive_int(n):
    try:
        i = int(n)
        return (i > 0)
    except ValueError:
        return False


def is_positive_float(n):
    try:
        f = float(n)
        return (f > 0)
    except ValueError:
        return False


def raise_ex(e):
    raise e

# --------------------------------------- #

def read_voltage(bus):
    read = bus.read_word_data(I2C_BATTERY_ADDR, 2)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    voltage = swapped * 1.25 /1000/16
    return voltage


def read_capacity(bus):
    read = bus.read_word_data(I2C_BATTERY_ADDR, 4)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    capacity = swapped/256
    return capacity


def battery_monitor(update_interval, min_voltage, flag_watch, gpio_ac):
    # 0 = /dev/i2c-0 (port I2C0),
    # 1 = /dev/i2c-1 (port I2C1)
    bus = smbus.SMBus(1)

    try:
        while True:
            volt = read_voltage(bus)

            # --- Monitor voltage --- #
            if not flag_watch and (volt < min_voltage) and gpio_ac.value:
                msg = "[!] Battery voltage below threshold (%.1fV)." % min_voltage
                msg += " Emergency poweroff."
                #print(msg)
                subprocess.call(['/usr/bin/wall', msg])
                do_shutdown()

            time.sleep(update_interval / 1000)

    except KeyboardInterrupt:
        return 0

# --------------------------------------- #


def do_shutdown():
    exit(subprocess.call(['/usr/sbin/poweroff']))


def do_reboot():
    exit(subprocess.call(['/usr/sbin/reboot']))


# --------------------------------------- #
# --- Power Button Callbacks --- #

def pwr_btn_released_callback(pwr_button):
    if not pwr_button.is_held:
        do_reboot()


def pwr_btn_held_callback(pwr_button):
    do_shutdown()


# --------------------------------------- #
# --- Power Loss Detection Callbacks --- #

def ac_power_connected_callback(pld_gpio):
    #print("AC power restored.")
    pass

def ac_power_lost_callback(pld_gpio):
    #print("AC power lost. Running on batteries.")
    pass

# --------------------------------------- #


def main():
    parser = ArgumentParser(description="RPI x708 Power Management Control")
    parser.add_argument("-n", "--interval", type = pos_float, metavar = "seconds", required = False,
                        dest = 'interval', default = 2.0, help = "Specify update interval.")
    parser.add_argument("--min-voltage", type = pos_float, metavar = "volts", required = False,
                        dest = 'min_voltage', default = 3.5,
                        help = "Specify minimum battery voltage (auto-shutdown).")
    parser.add_argument("-w", "--watch", dest="flag_watch", action="store_true",
                        help = "Watch only, without GPIO actuators.")

    parser.set_defaults(flag_watch = False)
    args = vars(parser.parse_args())

    if os.geteuid() != 0:
        error("[!] Error: Root privileges are needed to run this script.")
        return -1

    update_interval = args['interval'] * 1000
    min_voltage = args['min_voltage']
    flag_watch = args['flag_watch']

    if not flag_watch:
        # --- Power Loss Detection --- #
        pld_gpio = gpiozero.DigitalInputDevice(_GPIO_PIN_AC_LOST)

        pld_gpio.when_activated = ac_power_lost_callback
        pld_gpio.when_deactivated = ac_power_connected_callback

        # --- Physical Power Button --- #
        pwr_trigger = gpiozero.DigitalOutputDevice(_GPIO_PIN_PWR_TRIGGER)
        pwr_button = gpiozero.Button(_GPIO_PIN_PWR_BUTTON,
                                     pull_up = False, hold_time = 2)

        pwr_trigger.on()
        if pwr_button.value:
            error("[!] Error: PWR_BUTTON is pulled high. Aborting...")
            return -1

        pwr_button.when_released = pwr_btn_released_callback
        pwr_button.when_held = pwr_btn_held_callback

    # --- Battery Monitor --- #
    if not flag_watch and min_voltage < 3:
        print("[!] WARNING: min_voltage below 3V")
    return battery_monitor(int(update_interval), min_voltage, flag_watch, pld_gpio)

# --------------------------------------- #


if __name__ == '__main__':
    sys.exit(main())


# --------------------------------------- #
