#!/bin/bash
# 1. nädala kontroll: IoT ei pääse kontorivõrku, hq-controller haldab mõlemat
echo "== IoT -> ws-fin-01 (PEAB EBAÕNNESTUMA) =="
docker exec iot-sensor-1 ping -c 2 -W 2 ws-fin-01 && echo "VIGA: IoT näeb raamatupidajat!" || echo "OK: ligipääs blokeeritud"
echo "== IoT -> backup-vault (PEAB EBAÕNNESTUMA) =="
docker exec iot-sensor-1 ping -c 2 -W 2 backup-vault && echo "VIGA" || echo "OK: ligipääs blokeeritud"
echo "== hq-controller -> ws-fin-01 ja iot-sensor-1 (PEAB ÕNNESTUMA) =="
docker exec hq-controller ping -c 2 ws-fin-01 && docker exec hq-controller ping -c 2 iot-sensor-1 && echo "OK"
echo "== ansible ping =="
docker exec hq-controller ansible all -m ping
