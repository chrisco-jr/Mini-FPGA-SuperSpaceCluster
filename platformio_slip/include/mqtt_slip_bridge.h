#ifndef MQTT_SLIP_BRIDGE_H
#define MQTT_SLIP_BRIDGE_H

#include <Arduino.h>
#include "slip.h"
#include "config.h"

// Simple MQTT-like message structure for SLIP transport
struct SlipMessage {
    uint8_t type;           // 1=task, 2=result, 3=control
    char sender[32];
    char receiver[32];
    char function[64];
    uint16_t dataLen;
    uint8_t data[PACKET_BUFFER_SIZE - 128];  // Payload
};

class MQTTSlipBridge {
public:
    MQTTSlipBridge();
    
    // Initialize bridge with SLIP interfaces
    void begin();
    
    // Send message over SLIP
    bool sendMessage(const SlipMessage& msg, uint8_t workerIndex);
    
    // Receive message from SLIP
    bool receiveMessage(SlipMessage& msg, uint8_t workerIndex);
    
    // Process incoming messages (call in loop)
    void process();
    
    // Get SLIP interface for a worker
    SLIPInterface* getWorkerInterface(uint8_t index);
    
private:
    SLIPInterface* workers[NUM_WORKERS];
    HardwareSerial* serialPorts[NUM_WORKERS];
    
    bool serializeMessage(const SlipMessage& msg, uint8_t* buffer, size_t* len);
    bool deserializeMessage(const uint8_t* buffer, size_t len, SlipMessage& msg);
};

#endif // MQTT_SLIP_BRIDGE_H
