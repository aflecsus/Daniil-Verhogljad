# INCIDENT REPORT - Chaos Monkey (täida pärast rünnakut!)

Kuupäev / aeg: ______   Administraator(id): ______

## Ajajoon
| Aeg | Sündmus |
|---|---|
| T+0 | chaos_attack.sh käivitati |
| T+__ | Armatuurlaud näitas esimest häiret |
| T+__ | 07_incident_response.yml käivitati |
| T+__ | Kõik roheline |

## Intsidendid
| # | Sõlm | Intsident | Kuidas tuvastati | Tuvastamise aeg | Kuidas likvideeriti |
|---|---|---|---|---|---|
| 1 | iot-cam-1 | shadow_admin (UID 0) | UID=0 audit + FIM /etc/passwd | | |
| 2 | srv-app-01 | xmr_miner (kustutatud binaar) | processes on_disk=0 | | |
| 3 | kiosk-lobby | port 4444 | listening_ports | | |
| 4 | ws-fin-01 | finantsfailid kustutatud | fin_files = 0 | | taastatud vaultist |

## Taaste
- Kasutatud varukoopia: ______ (SHA-256 kontroll: OK/EI)
- Taastamise aeg: ______ (eesmärk < 5 min)

## Järeldused ja parendused
- Mida ei tuvastatud automaatselt? ______
- Mida muudaksin? ______
