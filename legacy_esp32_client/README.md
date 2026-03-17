# ESP32-S3 Broccoli Cluster with SLIP

This project implements a distributed computing cluster using ESP32-S3 boards connected via SLIP (Serial Line Internet Protocol).

## Hardware Setup (Testing: 1 Master + 1 Worker)

### Master Node (ESP32-S3)
- **Worker 1 Connection:**
  - TX: GPIO17
  - RX: GPIO18
  - UART1

### Worker Node (ESP32-S3)
- **Master Connection:**
  - TX: GPIO17
  - RX: GPIO18
  - UART1

## Wiring Diagram

```
Master ESP32-S3          Worker ESP32-S3
GPIO17 (TX1) ----------> GPIO18 (RX1)
GPIO18 (RX1) <---------- GPIO17 (TX1)
GND          ----------- GND
```

**Note:** To add more workers later, just connect additional ESP32-S3 boards to other UART pins on the master.

## Building and Flashing

### Flash Master Node:
```bash
pio run -e master_node -t upload
```

### Flash Worker Nodes:
```bash
pio run -e worker_node -t upload
```

## Configuration

Edit `include/config.h` to adjust:
- SLIP baud rate (default: 921600 bps)
- Buffer sizes
- Worker IP addresses

## SLIP Network Configuration

- Master Node IP: 192.168.100.1
- Worker 1 IP: 192.168.100.11
- Subnet: 255.255.255.0

## Speed

SLIP at 921600 baud ≈ 0.9 Mbps effective throughput per connection.

## Integration with Broccoli

This SLIP layer is designed to work **underneath** the existing Broccoli code without any modifications:
- SLIP provides the transport layer (like WiFi would)
- Broccoli's MQTT messages will be carried over SLIP instead of WiFi
- Original Broccoli code in `codes/broccoli/` remains untouched
