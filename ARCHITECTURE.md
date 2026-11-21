# ARCHITECTURE - CyberFleet 2026

## 1. IP-plaan ja tsoonid
| Konteiner | OS | mgmt_net 172.30.10.0/24 | corp_net 172.30.20.0/24 | dmz_iot 172.30.30.0/24 | Roll |
|---|---|---|---|---|---|
| hq-controller | Ubuntu 24.04 | .10 | .10 | .10 | Ansible, Osquery, Nginx :8080, cron |
| backup-vault | Debian 12 | .11 | - | - | krüpteeritud varukoopiad |
| ws-dev-01 | Ubuntu 24.04 | - | .11 | - | arendaja |
| ws-fin-01 | Ubuntu 24.04 | - | .12 | - | raamatupidaja |
| srv-app-01 | Rocky 9 | - | .13 | - | siseveeb (dnf/rpm) |
| kiosk-lobby | Debian 12 | - | - | .11 | kliendikiosk (rbash) |
| iot-sensor-1 | Alpine 3.20 | - | - | .12 | sensor.log iga minut |
| iot-cam-1 | Debian 12 slim | - | - | .13 | IP-kaamera (nõrk algseis) |

## 2. Zero Trust segmenteerimine
Ainult hq-controller on kõigis kolmes võrgus. dmz_iot sõlmed (kiosk, sensor, cam) ei näe ws-fin-01 ega backup-vault'i.
Varukoopiad liiguvad sõlm -> hq-controller -> backup-vault (corp/dmz sõlmedel pole teed vaulti).

## 3. Halduskiht
- Paroolivaba SSH: Ed25519 võti genereeritakse hq-controlleris, levitatakse playbookiga 00.
- Inventar hosts.ini: [workstations] [servers] [kiosks] [iot] [vault] + tsoonigrupid.
- Telemeetria: `fleet_collect` (Osquery SQL: users, listening_ports, deb/rpm_packages, hash, processes).
- Armatuurlaud värskeneb cron'iga (05 iga 2 min, 02 iga 10 min).

## 4. Turvameetmed
- sshd: PasswordAuthentication no, PermitRootLogin prohibit-password, MaxAuthTries 3, bänner.
- Kiosk: rbash, kirjutuskaitstud PATH, sudo eemaldatud; IoT/kiosk: telnet/netcat/kompilaatorid eemaldatud.
- Drift control: 04 käib cron'iga iga 10 min, taastab sshd seaded ja failiõigused.
- FIM: SHA-256 baseline (/etc/passwd, shadow, sshd_config, sudoers).
- HIDS: `processes WHERE on_disk = 0`, UID=0 kontod, volitamata pordid (policy.json).
- Varundus: AES-256-CBC (OpenSSL, PBKDF2 200 000 iter.) + SHA-256, 5 koopiat sõlme kohta.

## 5. Piirangud
Konteinerid jagavad hosti tuuma. Kiosk piirab väljuvat liiklust iptables'iga (lubatud ainult hq-controller 172.30.30.10); IoT-sõlmed toetuvad Dockeri tsoonide isolatsioonile.
