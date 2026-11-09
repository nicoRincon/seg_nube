#!/bin/bash
# Goldilocks CTF — reto 4 (Wireshark)
# Envía un "check-in" HTTP con Basic Auth en texto claro cada 30s hacia
# la IP leída de un archivo de configuración (no hardcodeada).
#
# Para cambiar el destino (ej. otra Kali), en cualquier momento:
#   echo "NUEVA_IP" | sudo tee /usr/local/share/goldilocks/kali-ip.txt
# Se aplica solo, sin reiniciar nada (se relee cada 30s).

CONF=/usr/local/share/goldilocks/kali-ip.txt
mkdir -p "$(dirname "$CONF")"
[ -f "$CONF" ] || echo "192.168.56.108" > "$CONF"

while true; do
  KALI_IP=$(cat "$CONF" 2>/dev/null)
  if [ -n "$KALI_IP" ]; then
    wget -q -O /dev/null --http-user=ricitos \
         --http-password=BOSQUE{ricitos_wireshark_credenciales} \
         "http://${KALI_IP}:8080/checkin" 2>/dev/null
  fi
  sleep 30
done
