#!/bin/sh
# Ühine sõlme käivitaja: SSH deemon (PID 1) + valikuline crond / nõrk konfiguratsioon
set -e
mkdir -p /run/sshd
ssh-keygen -A >/dev/null 2>&1

if [ "$START_CROND" = "1" ] && command -v crond >/dev/null 2>&1; then
  crond -b -l 8
fi

if [ "$WEAK_CONFIG" = "1" ]; then
  # IP-kaamera: teadlikult nõrk algseis, mida karastamine peab parandama
  id admin >/dev/null 2>&1 || { useradd -m -s /bin/bash admin 2>/dev/null || adduser -D admin; }
  echo 'admin:admin' | chpasswd
  sed -i 's/^PermitEmptyPasswords.*/PermitEmptyPasswords yes/' /etc/ssh/sshd_config
  echo 'X11Forwarding yes' >> /etc/ssh/sshd_config
fi

exec /usr/sbin/sshd -D -e
