#!/bin/bash

if [ $(id -u) -ne "0" ]; then
  echo "Must run as root!"
  exit 1
fi

echo "Installing x708 power management service"
cp rpi-x708pwm.py /usr/bin/rpi-x708pwm.py
chmod +x /usr/bin/rpi-x708pwm.py

cp system-update /usr/lib/systemd/systemd-shutdown/x708-shutdown.sh
chmod u+x /usr/lib/systemd/systemd-shutdown/x708-shutdown.sh

echo "Installing x708 fan control service"
cp rpi-x708fan.py /usr/bin/rpi-x708fan.py
chmod +x /usr/bin/rpi-x708fan.py


echo "Installing x708 utility scripts"
cp utils/rpi-x708bat.py /usr/bin/rpi-x708bat 
cp utils/rpi-x708pld.py /usr/bin/rpi-x708pld 
cp utils/rpi-x708softd.sh /usr/bin/rpi-x708softd

chmod +x /usr/bin/rpi-x708bat
chmod +x /usr/bin/rpi-x708pld
chmod +x /usr/bin/rpi-x708softd

echo "Installing x708 management services"
cp systemd-service/* /usr/lib/systemd/system
systemctl daemon-reload
systemctl enable rpi-x708fan.service rpi-x708pwm.service
systemctl start rpi-x708fan.service rpi-x708pwm.service
