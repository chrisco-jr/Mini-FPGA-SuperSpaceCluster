#include "mqtt_slip_bridge.h"

MQTTSlipBridge::MQTTSlipBridge() {
#ifdef MASTER_NODE
    // Initialize serial ports for each worker
    serialPorts[0] = &Serial1;  // UART1 for Worker 1
    
    #if NUM_WORKERS >= 2
    serialPorts[1] = &Serial2;  // UART2 for Worker 2
    #endif
    
    // Create SLIP interfaces with their respective pins
    workers[0] = new SLIPInterface(serialPorts[0], WORKER1_RX_PIN, WORKER1_TX_PIN);
    
    #if NUM_WORKERS >= 2
    workers[1] = new SLIPInterface(serialPorts[1], WORKER2_RX_PIN, WORKER2_TX_PIN);
    #endif
#endif
}

void MQTTSlipBridge::begin() {
#ifdef MASTER_NODE
    Serial.println("Initializing MQTT-SLIP Bridge (Master)...");
    
    for (int i = 0; i < NUM_WORKERS; i++) {
        workers[i]->begin(SLIP_BAUDRATE);
        Serial.printf("Worker %d SLIP interface initialized\n", i + 1);
    }
    
    Serial.println("MQTT-SLIP Bridge ready");
#endif

#ifdef WORKER_NODE
    Serial.println("Initializing MQTT-SLIP Bridge (Worker)...");
    // Worker uses Serial1 to connect to master
    Serial1.begin(SLIP_BAUDRATE, SERIAL_8N1, MASTER_RX_PIN, MASTER_TX_PIN);
    Serial1.setRxBufferSize(SERIAL_BUFFER_SIZE);
    Serial1.setTxBufferSize(SERIAL_BUFFER_SIZE);
    Serial.println("Worker SLIP interface ready");
#endif
}

bool MQTTSlipBridge::serializeMessage(const SlipMessage& msg, uint8_t* buffer, size_t* len) {
    size_t offset = 0;
    
    // Type
    buffer[offset++] = msg.type;
    
    // Sender (32 bytes)
    memcpy(buffer + offset, msg.sender, 32);
    offset += 32;
    
    // Receiver (32 bytes)
    memcpy(buffer + offset, msg.receiver, 32);
    offset += 32;
    
    // Function (64 bytes)
    memcpy(buffer + offset, msg.function, 64);
    offset += 64;
    
    // Data length (2 bytes)
    buffer[offset++] = (msg.dataLen >> 8) & 0xFF;
    buffer[offset++] = msg.dataLen & 0xFF;
    
    // Data
    if (msg.dataLen > 0) {
        memcpy(buffer + offset, msg.data, msg.dataLen);
        offset += msg.dataLen;
    }
    
    *len = offset;
    return true;
}

bool MQTTSlipBridge::deserializeMessage(const uint8_t* buffer, size_t len, SlipMessage& msg) {
    if (len < 131) {  // Minimum message size
        return false;
    }
    
    size_t offset = 0;
    
    // Type
    msg.type = buffer[offset++];
    
    // Sender
    memcpy(msg.sender, buffer + offset, 32);
    offset += 32;
    
    // Receiver
    memcpy(msg.receiver, buffer + offset, 32);
    offset += 32;
    
    // Function
    memcpy(msg.function, buffer + offset, 64);
    offset += 64;
    
    // Data length
    msg.dataLen = (buffer[offset] << 8) | buffer[offset + 1];
    offset += 2;
    
    // Data
    if (msg.dataLen > 0 && offset + msg.dataLen <= len) {
        memcpy(msg.data, buffer + offset, msg.dataLen);
    } else if (msg.dataLen > 0) {
        return false;  // Invalid data length
    }
    
    return true;
}

bool MQTTSlipBridge::sendMessage(const SlipMessage& msg, uint8_t workerIndex) {
#ifdef MASTER_NODE
    if (workerIndex >= NUM_WORKERS) {
        return false;
    }
    
    uint8_t buffer[PACKET_BUFFER_SIZE];
    size_t len;
    
    if (!serializeMessage(msg, buffer, &len)) {
        return false;
    }
    
    return workers[workerIndex]->send(buffer, len) > 0;
#endif
    return false;
}

bool MQTTSlipBridge::receiveMessage(SlipMessage& msg, uint8_t workerIndex) {
#ifdef MASTER_NODE
    if (workerIndex >= NUM_WORKERS) {
        return false;
    }
    
    uint8_t buffer[PACKET_BUFFER_SIZE];
    int len = workers[workerIndex]->receive(buffer, PACKET_BUFFER_SIZE);
    
    if (len > 0) {
        return deserializeMessage(buffer, len, msg);
    }
#endif
    return false;
}

void MQTTSlipBridge::process() {
#ifdef MASTER_NODE
    // Check all workers for incoming messages
    for (int i = 0; i < NUM_WORKERS; i++) {
        if (workers[i]->available()) {
            SlipMessage msg;
            if (receiveMessage(msg, i)) {
                Serial.printf("Received message from worker %d: type=%d, function=%s\n", 
                              i + 1, msg.type, msg.function);
                // Handle message (to be implemented)
            }
        }
    }
#endif
}

SLIPInterface* MQTTSlipBridge::getWorkerInterface(uint8_t index) {
#ifdef MASTER_NODE
    if (index < NUM_WORKERS) {
        return workers[index];
    }
#endif
    return nullptr;
}
