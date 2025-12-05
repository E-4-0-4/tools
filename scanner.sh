#!/bin/bash

# Enhanced vulnerability scanning script for educational use
# Supports --fast, --deep, and -o options; includes verbose output
# Handles both domains and IP addresses as input
# For college project use in a safe, authorized environment only

# Function to display usage
usage() {
    echo "Usage: $0 <target> [--fast|--deep] [-o output-dir]"
    echo "Target can be a domain (e.g., example.com) or IP (e.g., 93.184.216.34)"
    echo "Example: $0 example.com --deep -o my_scan"
    echo "Options:"
    echo "  --fast      Quick scan (ports 1-1000, basic scripts)"
    echo "  --deep      Comprehensive scan (all ports, extended scripts)"
    echo "  -o <dir>    Specify output directory (default: scan_results_<timestamp>)" 
    exit 1
}

# Function to check and install tools
check_install_tool() {
    local tool=$1
    local package=$2
    if ! command -v "$tool" &> /dev/null; then
        echo "[VERBOSE] $tool not found. Attempting to install..."
        if [[ $(uname -s) == "Linux" && -n "$(command -v apt-get)" ]]; then
            sudo apt-get update && sudo apt-get install -y "$package"
            if [ $? -ne 0 ]; then
                echo "[ERROR] Failed to install $tool. Please install it manually."
                exit 1
            fi
        else
            echo "[ERROR] $tool not found and auto-install only supported on Debian/Ubuntu. Please install $tool manually."
            exit 1
        fi
    fi
    echo "[VERBOSE] $tool is installed."
}

# Function to generate HTML report
generate_html_report() {
    local output_dir=$1
    local open_ports=$2
    local software_versions=$3
    local bug_types=$4
    cat << EOF > "$output_dir/report.html"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vulnerability Scan Report - $TARGET</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #555; }
        pre { background: #f4f4f4; padding: 10px; border-radius: 5px; }
        .warning { color: #e74c3c; }
        .info { color: #2ecc71; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Vulnerability Scan Report for $TARGET</h1>
    <p>Generated on: $TIMESTAMP</p>
    <h2>Summary</h2>
    <pre>$(cat "$output_dir/summary.txt")</pre>
    <h2>Open Ports and Software Versions</h2>
    <table>
        <tr><th>Port</th><th>Service</th><th>Version</th></tr>
        $software_versions
    </table>
    <h2>Potential Bug Types (SearchSploit)</h2>
    <pre>$bug_types</pre>
    <h2>DNS Lookup</h2>
    <pre>$(cat "$output_dir/dns_lookup.txt")</pre>
    <h2>Nmap Vulnerabilities</h2>
    <pre>$(cat "$output_dir/vuln_scan.txt")</pre>
    <h2>HTTP Headers</h2>
    <pre>$(cat "$output_dir/http_headers.txt")</pre>
    <h2>WordPress Scan</h2>
    <pre>$(cat "$output_dir/wpscan.txt")</pre>
    <h2>SearchSploit Full Results</h2>
    <pre>$(cat "$output_dir/searchsploit.txt")</pre>
</body>
</html>
EOF
}

# Parse arguments
TARGET=""
SCAN_MODE="fast"
OUTPUT_DIR=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            SCAN_MODE="fast"
            shift
            ;;
        --deep)
            SCAN_MODE="deep"
            shift
            ;;
        -o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            if [ -z "$TARGET" ]; then
                TARGET="$1"
            else
                usage
            fi
            shift
            ;;
    esac
done

# Validate target
if [ -z "$TARGET" ]; then
    usage
fi

# Set default output directory if not specified
TIMESTAMP=$(date +%F_%H-%M-%S)
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="scan_results_$TIMESTAMP"
fi
mkdir -p "$OUTPUT_DIR"

# Check and install required tools
echo "[VERBOSE] Checking for required tools..."
check_install_tool "nmap" "nmap"
check_install_tool "curl" "curl"
check_install_tool "dig" "dnsutils"
check_install_tool "wpscan" "wpscan"
check_install_tool "searchsploit" "exploitdb"

echo "[VERBOSE] Starting vulnerability scan for $TARGET at $TIMESTAMP (Mode: $SCAN_MODE)"
echo "Results will be saved in $OUTPUT_DIR"

# Step 1: DNS Lookup (run in background)
echo "[VERBOSE] Performing DNS lookup for $TARGET..." &
dig +all "$TARGET" > "$OUTPUT_DIR/dns_lookup.txt" 2>/dev/null &
DNS_PID=$!

# Step 2: Resolve to IP (handle domain or IP input)
echo "[VERBOSE] Determining IP for $TARGET..."
if [[ $TARGET =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    IP="$TARGET"
    echo "[INFO] Target is an IP address: $IP" | tee -a "$OUTPUT_DIR/summary.txt"
else
    IP=$(dig +short "$TARGET" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1)
    if [ -z "$IP" ]; then
        echo "[ERROR] Could not resolve domain $TARGET to an IP address." | tee -a "$OUTPUT_DIR/summary.txt"
        exit 1
    fi
    echo "[INFO] Resolved domain $TARGET to IP: $IP" | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 3: Check HTTP headers with curl (run in background)
echo "[VERBOSE] Checking HTTP headers for $TARGET..." &
curl -s -I "http://$TARGET" > "$OUTPUT_DIR/http_headers.txt" 2>/dev/null
curl -s -I "https://$TARGET" >> "$OUTPUT_DIR/http_headers.txt" 2>/dev/null &
CURL_PID=$!

# Step 4: Nmap port scan
echo "[VERBOSE] Running nmap port scan ($SCAN_MODE mode)..."
if [ "$SCAN_MODE" = "fast" ]; then
    nmap -vv -sS -Pn -p 1-1000 --open --reason --min-rate 1000 "$IP" -oN "$OUTPUT_DIR/port_scan.txt"
else
    nmap -vv -sS -Pn -p- --open --reason --min-rate 500 "$IP" -oN "$OUTPUT_DIR/port_scan.txt"
fi
if [ $? -ne 0 ]; then
    echo "[ERROR] nmap port scan failed." | tee -a "$OUTPUT_DIR/summary.txt"
    exit 1
fi

# Step 5: Nmap vulnerability scan
echo "[VERBOSE] Running nmap vulnerability scan ($SCAN_MODE mode)..."
if [ "$SCAN_MODE" = "fast" ]; then
    nmap -vv -sV --script="vuln" --script-args="http.useragent=Mozilla/5.0" "$IP" -oN "$OUTPUT_DIR/vuln_scan.txt" -oX "$OUTPUT_DIR/vuln_scan.xml"
else
    nmap -sV --script="vuln,http-enum,ssl-enum-ciphers,smb-vuln*" --script-args="http.useragent=Mozilla/5.0" "$IP" -oN "$OUTPUT_DIR/vuln_scan.txt" -oX "$OUTPUT_DIR/vuln_scan.xml"
fi
if [ $? -ne 0 ]; then
    echo "[WARNING] nmap vulnerability scan encountered an issue." | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 6: Wait for background tasks
echo "[VERBOSE] Waiting for DNS and HTTP header checks to complete..."
wait $DNS_PID
wait $CURL_PID

# Step 7: Analyze DNS results
echo "[VERBOSE] Analyzing DNS results..."
if [ -s "$OUTPUT_DIR/dns_lookup.txt" ]; then
    # For IPs, prioritize PTR; for domains, A/CNAME/MX/NS/TXT
    if [[ $TARGET =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        DNS_INFO=$(grep -E "PTR" "$OUTPUT_DIR/dns_lookup.txt" | awk '{print $4,$5}' | sort -u)
        RECORD_TYPE="PTR Records"
    else
        DNS_INFO=$(grep -E "A|CNAME|MX|NS|TXT" "$OUTPUT_DIR/dns_lookup.txt" | awk '{print $4,$5}' | sort -u)
        RECORD_TYPE="DNS Records"
    fi
    if [ -n "$DNS_INFO" ]; then
        echo "[INFO] $RECORD_TYPE: $DNS_INFO" | tee -a "$OUTPUT_DIR/summary.txt"
    else
        echo "[INFO] No significant DNS records found." | tee -a "$OUTPUT_DIR/summary.txt"
    fi
else
    echo "[WARNING] DNS lookup failed." | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 8: Analyze HTTP headers
echo "[VERBOSE] Analyzing HTTP headers..."
if grep -qi "server: " "$OUTPUT_DIR/http_headers.txt"; then
    SERVER=$(grep -i "server: " "$OUTPUT_DIR/http_headers.txt" | awk '{print $2}' | head -n 1)
    echo "[INFO] Web server detected: $SERVER" | tee -a "$OUTPUT_DIR/summary.txt"
else
    echo "[INFO] No server header found." | tee -a "$OUTPUT_DIR/summary.txt"
fi
if ! grep -qi "strict-transport-security" "$OUTPUT_DIR/http_headers.txt"; then
    echo "[WARNING] HSTS header missing. Site may be vulnerable to SSL stripping." | tee -a "$OUTPUT_DIR/summary.txt"
fi
if grep -qi "x-powered-by" "$OUTPUT_DIR/http_headers.txt"; then
    POWERED_BY=$(grep -i "x-powered-by" "$OUTPUT_DIR/http_headers.txt" | awk '{print $2}' | head -n 1)
    echo "[WARNING] X-Powered-By header exposes $POWERED_BY." | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 9: WPScan for WordPress
echo "[VERBOSE] Running WPScan for WordPress vulnerabilities..."
wpscan --url "http://$TARGET" --enumerate u,vp,vt --random-user-agent --output "$OUTPUT_DIR/wpscan.txt" 2>/dev/null
if [ $? -eq 0 ]; then
    if grep -qi "WordPress version" "$OUTPUT_DIR/wpscan.txt"; then
        WP_VERSION=$(grep -i "WordPress version" "$OUTPUT_DIR/wpscan.txt" | head -n 1)
        echo "[INFO] WordPress detected: $WP_VERSION" | tee -a "$OUTPUT_DIR/summary.txt"
        if grep -qi "Vulnerability" "$OUTPUT_DIR/wpscan.txt"; then
            echo "[WARNING] WordPress vulnerabilities found. Check $OUTPUT_DIR/wpscan.txt." | tee -a "$OUTPUT_DIR/summary.txt"
        else
            echo "[INFO] No WordPress vulnerabilities detected." | tee -a "$OUTPUT_DIR/summary.txt"
        fi
    else
        echo "[INFO] No WordPress installation detected." | tee -a "$OUTPUT_DIR/summary.txt"
    fi
else
    echo "[WARNING] WPScan failed or no WordPress site found." | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 10: Extract open ports and software versions
echo "[VERBOSE] Extracting open ports and software versions..."
SOFTWARE_VERSIONS=""
if [ -s "$OUTPUT_DIR/vuln_scan.txt" ]; then
    while IFS= read -r line; do
        if echo "$line" | grep -q "open"; then
            PORT=$(echo "$line" | awk '{print $1}')
            SERVICE=$(echo "$line" | awk '{print $3}')
            VERSION=$(echo "$line" | awk '{$1=$2=$3=""; print}' | sed 's/^[ \t]*//')
            SOFTWARE_VERSIONS="$SOFTWARE_VERSIONS<tr><td>$PORT</td><td>$SERVICE</td><td>$VERSION</td></tr>\n"
        fi
    done < "$OUTPUT_DIR/vuln_scan.txt"
fi
if [ -z "$SOFTWARE_VERSIONS" ]; then
    SOFTWARE_VERSIONS="<tr><td colspan='3'>No open ports or versions detected.</td></tr>"
fi

# Step 11: SearchSploit for known exploits
echo "[VERBOSE] Searching for known exploits with SearchSploit..."
BUG_TYPES=""
if [ -s "$OUTPUT_DIR/vuln_scan.txt" ]; then
    SERVICES=$(grep -i "open" "$OUTPUT_DIR/vuln_scan.txt" | awk '{print $3}' | sort -u)
    for SERVICE in $SERVICES; do
        echo "[VERBOSE] Searching exploits for $SERVICE..." | tee -a "$OUTPUT_DIR/searchsploit.txt"
        searchsploit --exclude "dos|local" "$SERVICE" >> "$OUTPUT_DIR/searchsploit.txt" 2>/dev/null
        if [ -s "$OUTPUT_DIR/searchsploit.txt" ]; then
            SERVICE_BUGS=$(grep -i "$SERVICE" "$OUTPUT_DIR/searchsploit.txt" | grep -oE "remote|webapps|privilege escalation|code execution|buffer overflow|xss|sql injection" | sort -u | tr '\n' ', ')
            if [ -n "$SERVICE_BUGS" ]; then
                BUG_TYPES="$BUG_TYPES$SERVICE: $SERVICE_BUGS\n"
            fi
        fi
    done
    if [ -s "$OUTPUT_DIR/searchsploit.txt" ]; then
        echo "[INFO] Potential exploits found. Check $OUTPUT_DIR/searchsploit.txt." | tee -a "$OUTPUT_DIR/summary.txt"
    else
        echo "[INFO] No exploits found in SearchSploit." | tee -a "$OUTPUT_DIR/searchsploit.txt"
    fi
else
    echo "[INFO] No services found to search for exploits." | tee -a "$OUTPUT_DIR/searchsploit.txt"
fi
if [ -z "$BUG_TYPES" ]; then
    BUG_TYPES="No specific bug types identified."
fi

# Step 12: Summarize open ports
echo "[VERBOSE] Summarizing open ports..."
OPEN_PORTS=$(grep "open" "$OUTPUT_DIR/port_scan.txt" | awk '{print $1}' | sort -u)
if [ -n "$OPEN_PORTS" ]; then
    echo "[INFO] Open ports found: $OPEN_PORTS" | tee -a "$OUTPUT_DIR/summary.txt"
else
    echo "[INFO] No open ports found." | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 13: Summarize vulnerabilities
echo "[VERBOSE] Summarizing vulnerabilities..."
if [ -s "$OUTPUT_DIR/vuln_scan.txt" ]; then
    VULNS=$(grep -i "VULNERABLE" "$OUTPUT_DIR/vuln_scan.txt")
    if [ -n "$VULNS" ]; then
        echo "[WARNING] Potential vulnerabilities found. Check $OUTPUT_DIR/vuln_scan.txt." | tee -a "$OUTPUT_DIR/summary.txt"
    else
        echo "[INFO] No vulnerabilities detected by nmap scripts." | tee -a "$OUTPUT_DIR/summary.txt"
    fi
else
    echo "[WARNING] No vulnerability scan results available." | tee -a "$OUTPUT_DIR/summary.txt"
fi

# Step 14: Generate HTML report
echo "[VERBOSE] Generating HTML report..."
generate_html_report "$OUTPUT_DIR" "$OPEN_PORTS" "$SOFTWARE_VERSIONS" "$BUG_TYPES"

echo "[INFO] Scan completed. Results saved in $OUTPUT_DIR"
echo "[INFO] Summary available in $OUTPUT_DIR/summary.txt"
echo "[INFO] HTML report available in $OUTPUT_DIR/report.html"
