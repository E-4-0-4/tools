## 🔧 Usage

Run the tool with root privileges (required for raw sockets and stress testing):

```bash
sudo python3 ddos.py <target> [OPTIONS]
```

### 📌 Positional Argument:

- `target`  
  The target IP address or domain name to stress test.

---

### ⚙️ Optional Arguments:

| Option              | Description                                                  | Default         |
|---------------------|--------------------------------------------------------------|-----------------|
| `--port`            | Target port number                                            | `80`            |
| `--mode`            | Attack mode: `udp` or `tcp`                                   | `udp`           |
| `--rate`            | Packets per second **per thread**                            | `100`           |
| `--duration`        | Duration of the attack in seconds                             | `10`            |
| `--threads`         | Number of concurrent threads to use                           | `5`             |
| `--packet-size`     | Size of each UDP packet in bytes (only for UDP mode)          | `1024`          |

---

### 🧪 Example Commands:

#### 1. UDP Flood on Localhost:
```bash
sudo python3 ddos.py 127.0.0.1 --mode udp --port 8080 --rate 500 --duration 30 --threads 10
```

#### 2. TCP SYN Flood on Localhost:
```bash
sudo python3 ddos.py 127.0.0.1 --mode tcp --port 80 --rate 100 --duration 20 --threads 5
```

#### 3. UDP Flood on a Domain:
```bash
sudo python3 ddos.py example.com --mode udp --rate 200 --threads 8
```
