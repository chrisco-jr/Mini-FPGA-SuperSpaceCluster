#ifndef SLIP_H
#define SLIP_H

#include <Arduino.h>
#include "config.h"

class SLIPInterface {
public:
    SLIPInterface(HardwareSerial* serial, uint8_t rxPin, uint8_t txPin);
    
    void begin(unsigned long baudRate);
    
    // Send data with SLIP encoding
    size_t send(const uint8_t* data, size_t len);
    
    // Receive data with SLIP decoding
    int receive(uint8_t* buffer, size_t maxLen);
    
    // Check if data is available
    bool available();
    
    // Get statistics
    unsigned long getBytesSent() { return bytesSent; }
    unsigned long getBytesReceived() { return bytesReceived; }
    unsigned long getPacketsSent() { return packetsSent; }
    unsigned long getPacketsReceived() { return packetsReceived; }
    
private:
    HardwareSerial* serial;
    uint8_t rxPin;
    uint8_t txPin;
    
    uint8_t rxBuffer[SLIP_MTU];
    size_t rxBufferPos;
    bool escapeNext;
    
    unsigned long bytesSent;
    unsigned long bytesReceived;
    unsigned long packetsSent;
    unsigned long packetsReceived;
    
    void sendByte(uint8_t b);
    int receiveByte();
};

#endif // SLIP_H
