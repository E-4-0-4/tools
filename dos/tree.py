#!/usr/bin/env python3
# iptracker.py
import sys, socket, requests

API = "http://ip-api.com/json/{}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"

def lookup(target: str):
    # Accept either an IP or a hostname
    try:
        socket.inet_aton(target)           # raises if not IPv4
        ip = target
    except OSError:
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror as e:
            return f"Cannot resolve {target}: {e}"

    try:
        data = requests.get(API.format(ip), timeout=5).json()
    except requests.RequestException as e:
        return f"Network error: {e}"

    if data.get("status") == "fail":
        return f"API error: {data.get('message', 'unknown')}"

    return (
        f"Target        : {target}\n"
        f"Resolved IP   : {data['query']}\n"
        f"Country       : {data['country']} ({data['regionName']})\n"
        f"City          : {data['city']}  {data['zip']}\n"
        f"Coordinates   : {data['lat']}, {data['lon']}\n"
        f"Timezone      : {data['timezone']}\n"
        f"ISP           : {data['isp']}\n"
        f"Organization  : {data['org']}\n"
        f"ASN           : {data['as']}"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 iptracker.py <IP|hostname>")
        sys.exit(1)
    print(lookup(sys.argv[1]))