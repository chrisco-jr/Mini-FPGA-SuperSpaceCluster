#ifndef CONFIG_H
#define CONFIG_H

// SLIP Configuration
#define SLIP_BAUDRATE 921600
#define SLIP_MTU 1500
#define SLIP_END 0xC0
#define SLIP_ESC 0xDB
#define SLIP_ESC_END 0xDC
#define SLIP_ESC_ESC 0xDD

// Network Configuration
#define MASTER_IP "192.168.100.1"
#define WORKER1_IP "192.168.100.11"
#define WORKER2_IP "192.168.100.12"
#define WORKER3_IP "192.168.100.13"
#define SUBNET_MASK "255.255.255.0"

// Master Node UART Pin Configuration
#ifdef MASTER_NODE
    // Worker 1 on UART1
    #define WORKER1_TX_PIN 17
    #define WORKER1_RX_PIN 18
    #define WORKER1_UART_NUM 1
    
    // Worker 2 on UART2
    #define WORKER2_TX_PIN 16
    #define WORKER2_RX_PIN 15
    #define WORKER2_UART_NUM 2
    
    // Worker reset control pin (connect to worker EN pin)
    #define WORKER_RESET_PIN 4  // Pull LOW to reset worker
#endif

// Worker Node UART Pin Configuration
#ifdef WORKER_NODE
    #define MASTER_TX_PIN 17
    #define MASTER_RX_PIN 18
    #define MASTER_UART_NUM 1
#endif

// MQTT Configuration (runs over SLIP)
#define MQTT_SERVER "192.168.100.1"  // Master node
#define MQTT_PORT 1883
#define MQTT_BUFFER_SIZE 2048

// Task Queue Configuration
#define MAX_TASK_QUEUE_SIZE 50
#define MAX_RESULT_QUEUE_SIZE 50

// Buffer Sizes
#define SERIAL_BUFFER_SIZE 4096
#define PACKET_BUFFER_SIZE 2048

#endif // CONFIG_H
