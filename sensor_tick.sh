#!/bin/sh
# Tehaseanduri simulaator: temperatuurinäit /var/log/sensor.log faili
S=$(date +%s)
echo "$(date '+%F %T') sensor=iot-sensor-1 temperature=$((20 + S % 9)).$((S % 10))C" >> /var/log/sensor.log
