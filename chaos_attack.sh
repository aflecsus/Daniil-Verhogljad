#!/bin/bash
# Chaos Monkey - käivita HOSTI pealt (docker exec), mitte konteineri sees.
echo "[!] Käivitub Chaos Monkey küberrünnak seadmepargile..."

# Intsident 1: IoT kaamerasse lisatakse salajane root-õigustega tagaukse konto
docker exec iot-cam-1 sh -c "echo 'shadow_admin:x:0:0:root:/root:/bin/bash' >> /etc/passwd"

# Intsident 2: Rakendusserveris (srv-app-01) käivitatakse mälus peidetud krüptokaevur (kustutatud binaariga)
docker exec -d srv-app-01 sh -c "cp /bin/sleep /tmp/xmr_miner && /tmp/xmr_miner 7200 & sleep 1 && rm -f /tmp/xmr_miner"

# Intsident 3: Kioskis avatakse kahtlane tagaukse port 4444
docker exec -d kiosk-lobby sh -c "python3 -m http.server 4444 >/dev/null 2>&1 &"

# Intsident 4: Raamatupidaja arvutit tabab 'lunavara' - kõik finantsfailid kustutatakse!
docker exec ws-fin-01 sh -c "rm -rf /home/raamatupidaja/Raamatupidamine_2026/*"

echo "[+] Rünnak lõppenud! Administraatoril on aega 10 minutit intsidentide tuvastamiseks ja taastamiseks!"
