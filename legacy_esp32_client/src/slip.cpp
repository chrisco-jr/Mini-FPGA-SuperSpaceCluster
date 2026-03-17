#include "slip.h"

SLIPInterface::SLIPInterface(HardwareSerial* serial, uint8_t rxPin, uint8_t txPin)
    : serial(serial), rxPin(rxPin), txPin(txPin), rxBufferPos(0), 
      escapeNext(false), bytesSent(0), bytesReceived(0), 
      packetsSent(0), packetsReceived(0) {
}

void SLIPInterface::begin(unsigned long baudRate) {
    serial->begin(baudRate, SERIAL_8N1, rxPin, txPin);
    serial->setRxBufferSize(SERIAL_BUFFER_SIZE);
    serial->setTxBufferSize(SERIAL_BUFFER_SIZE);
    
    // Flush any existing data
    while (serial->available()) {
        serial->read();
    }
    
    rxBufferPos = 0;
    escapeNext = false;
}

void SLIPInterface::sendByte(uint8_t b) {
    switch (b) {
        case SLIP_END:
            serial->write(SLIP_ESC);
            serial->write(SLIP_ESC_END);
            bytesSent += 2;
            break;
        case SLIP_ESC:
            serial->write(SLIP_ESC);
            serial->write(SLIP_ESC_ESC);
            bytesSent += 2;
            break;
        default:
            serial->write(b);
            bytesSent++;
            break;
    }
}

size_t SLIPInterface::send(const uint8_t* data, size_t len) {
    if (len == 0) return 0;
    
    // Send SLIP_END to start packet
    serial->write(SLIP_END);
    bytesSent++;
    
    // Send data with SLIP encoding
    for (size_t i = 0; i < len; i++) {
        sendByte(data[i]);
    }
    
    // Send SLIP_END to end packet
    serial->write(SLIP_END);
    bytesSent++;
    
    packetsSent++;
    return len;
}

int SLIPInterface::receiveByte() {
    if (!serial->available()) {
        return -1;
    }
    
    uint8_t b = serial->read();
    bytesReceived++;
    
    if (escapeNext) {
        escapeNext = false;
        switch (b) {
            case SLIP_ESC_END:
                return SLIP_END;
            case SLIP_ESC_ESC:
                return SLIP_ESC;
            default:
                // Protocol error - ignore
                return -1;
        }
    }
    
    if (b == SLIP_ESC) {
        escapeNext = true;
        return -1;  // Don't store escape character
    }
    
    if (b == SLIP_END) {
        return -2;  // Special return value for END marker
    }
    
    return b;
}

int SLIPInterface::receive(uint8_t* buffer, size_t maxLen) {
    while (serial->available()) {
        int b = receiveByte();
        
        if (b == -1) {
            continue;  // Escape character or error, keep reading
        }
        
        if (b == -2) {
            // SLIP_END received
            if (rxBufferPos > 0) {
                // Complete packet received
                size_t len = rxBufferPos;
                memcpy(buffer, rxBuffer, len);
                rxBufferPos = 0;
                packetsReceived++;
                return len;
            }
            // Empty packet, keep reading
            continue;
        }
        
        // Normal data byte
        if (rxBufferPos < SLIP_MTU) {
            rxBuffer[rxBufferPos++] = (uint8_t)b;
        } else {
            // Buffer overflow - reset
            rxBufferPos = 0;
        }
    }
    
    return 0;  // No complete packet yet
}

bool SLIPInterface::available() {
    return serial->available() > 0;
}
