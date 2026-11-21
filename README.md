# CyberFleet 2026 - NordicTech OÜ klientseadmete park

Docker Compose + Ansible + Osquery: 8 konteinerit, 4 OS-i (Ubuntu 24.04, Debian 12, Rocky 9, Alpine 3.20),
3 isoleeritud võrku, elav CMDB/turvaarmatuurlaud, enesetervendus, krüpteeritud varundus ja avariitaaste.

## Quickstart

```bash
make up          # ehitab ja käivitab 8 konteinerit
make deploy      # 00 bootstrap -> 01 -> 02 -> 03 -> 04 -> 06 -> 05 (baseline)
make test        # 1. nädala kontroll: IoT ei pääse kontorivõrku
# armatuurlaud: http://localhost:8080
make attack      # Chaos Monkey (õpetaja / paarilise käivitada)
make recover     # 07_incident_response.yml (tapmine + puhastus + taastamine vaultist)
make down        # kõik maha (kustutab ka võtmed ja varukoopiad)
```

Käsitsi: `docker exec hq-controller ansible-playbook playbooks/0X_....yml`

## Kiosk-profiili proovimine
`docker exec -it -u kiosk kiosk-lobby /bin/rbash --login` (cd, PATH muutmine ja `/` käsud on keelatud)

## Playbookid
| Fail | Eesmärk |
|---|---|
| 00_bootstrap.yml | Ed25519 avaliku võtme levitamine (ainus parooliga samm) |
| 01_deploy_agents.yml | Osquery (deb/rpm) + kollektor kõigile, Alpine'is /proc-telemeetria |
| 02_generate_cmdb.yml | Nginx :8080 + HTML CMDB |
| 03_profiles.yml | dev / fin / kiosk profiilid, srv-app-01 dnf |
| 04_hardening.yml | SSH, bänner, tööriistad, cron enesetervendus |
| 05_security_audit.yml | FIM, kustutatud binaarid, UID=0, pordid. `-e init_baseline=true` loob baseline'i |
| 06_fleet_backup.yml | tar -> AES-256 -> SHA-256 -> backup-vault |
| 07_incident_response.yml | tapmine, kontode eemaldus, taastamine vaultist |

## Märkused
- Esmane root-parool on `cyberfleet` (ainult bootstrapiks; pärast 04 on paroolilogin keelatud).
- Baseline luuakse ALLES pärast 04, muidu märgib FIM karastamise enda muudatused häireks.
- Võrgud on mitte-`internal`, et apt/dnf töötaks; segmenteerimine põhineb Dockeri eraldi bridge'idel.
- Osquery versiooni saab muuta muutujaga `osquery_version` (01_deploy_agents.yml).
