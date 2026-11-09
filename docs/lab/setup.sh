#!/bin/bash
# Goldilocks CTF — habilita retos 1 (nmap) y 4 (wireshark) reales en Metasploitable2
# Ejecutar como root: sudo bash setup.sh

mkdir -p /usr/local/share/goldilocks

# --- Reto 1: banner con flag en el puerto 1337 ---
cat > /usr/local/share/goldilocks/nmap-banner.txt <<'EOF'
220 Osito-Soup-Daemon 1.0 ready.
220 PIEZA{osito_nmap_hosts_activos}
EOF

cat > /usr/local/bin/goldilocks-nmap-banner.sh <<'EOF'
#!/bin/bash
while true; do
  nc -l -p 1337 -q 1 < /usr/local/share/goldilocks/nmap-banner.txt
  sleep 1
done
EOF
chmod +x /usr/local/bin/goldilocks-nmap-banner.sh

# --- Reto 4: beacon HTTP con Basic Auth en texto claro, cada 30s ---
# La IP de destino (Kali) se lee de un archivo, no va hardcodeada.
# Para apuntar a otra Kali: echo "NUEVA_IP" | sudo tee /usr/local/share/goldilocks/kali-ip.txt
[ -f /usr/local/share/goldilocks/kali-ip.txt ] || echo "192.168.56.108" > /usr/local/share/goldilocks/kali-ip.txt

cat > /usr/local/bin/goldilocks-cred-beacon.sh <<'EOF'
#!/bin/bash
CONF=/usr/local/share/goldilocks/kali-ip.txt
while true; do
  KALI_IP=$(cat "$CONF" 2>/dev/null)
  if [ -n "$KALI_IP" ]; then
    wget -q -O /dev/null --http-user=ricitos \
         --http-password=PIEZA{ricitos_wireshark_credenciales} \
         "http://${KALI_IP}:8080/checkin" 2>/dev/null
  fi
  sleep 30
done
EOF
chmod +x /usr/local/bin/goldilocks-cred-beacon.sh

# --- Persistir en el arranque (antes de "exit 0" en rc.local) ---
if ! grep -q "goldilocks-nmap-banner" /etc/rc.local 2>/dev/null; then
  TMP=$(mktemp)
  awk '/^exit 0/{print "/usr/local/bin/goldilocks-nmap-banner.sh &"; print "/usr/local/bin/goldilocks-cred-beacon.sh &"} {print}' /etc/rc.local > "$TMP"
  mv "$TMP" /etc/rc.local
  chmod +x /etc/rc.local
fi

# --- Arrancarlos ya mismo, sin esperar reinicio ---
pkill -f goldilocks-nmap-banner.sh 2>/dev/null
pkill -f goldilocks-cred-beacon.sh 2>/dev/null
nohup /usr/local/bin/goldilocks-nmap-banner.sh >/dev/null 2>&1 &
nohup /usr/local/bin/goldilocks-cred-beacon.sh >/dev/null 2>&1 &
disown -a

echo "[+] Listo. Puerto 1337 activo."
echo "[+] Beacon enviando cada 30s a: $(cat /usr/local/share/goldilocks/kali-ip.txt)"
echo "[+] Para cambiar el destino: echo NUEVA_IP | sudo tee /usr/local/share/goldilocks/kali-ip.txt"
