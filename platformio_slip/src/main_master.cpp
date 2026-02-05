#ifdef MASTER_NODE

#include <Arduino.h>
#include "config.h"
#include "slip.h"
#include "mqtt_slip_bridge.h"
#include <map>
#include <string>

MQTTSlipBridge bridge;

// Store task definitions and pending results
std::map<String, String> taskDefinitions;  // task_name -> code
int nextTaskId = 1;

void setup() {
    // Initialize USB serial for debugging
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n=================================");
    Serial.println("ESP32-S3 Broccoli Master Node");
    Serial.println("SLIP Network Configuration");
    Serial.println("=================================");
    
    // Initialize MQTT-SLIP bridge
    bridge.begin();
    
    // Initialize worker reset pin (HIGH = running, LOW = reset)
    pinMode(WORKER_RESET_PIN, OUTPUT);
    digitalWrite(WORKER_RESET_PIN, HIGH);  // Keep worker running
    
    Serial.println("\nMaster node ready!");
    Serial.println("Waiting for worker connections...");
    Serial.println("\nCommands:");
    Serial.println("  DEFINE:task_name:code  - Define new task");
    Serial.println("  EXEC:task_name:args    - Execute task");
    Serial.println("  LIST                   - List defined tasks");
    Serial.println("  STATS                  - Show SLIP statistics");
}

void processSerialCommand() {
    static uint8_t buffer[512];  // Static buffer for SLIP responses
    
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        
        if (cmd.startsWith("DEFINE:")) {
            // Format: DEFINE:task_name:code
            // Example: DEFINE:add:x+y
            int firstColon = cmd.indexOf(':');
            int secondColon = cmd.indexOf(':', firstColon + 1);
            
            if (secondColon > 0) {
                String taskName = cmd.substring(firstColon + 1, secondColon);
                String taskCode = cmd.substring(secondColon + 1);
                taskDefinitions[taskName] = taskCode;
                
                // Forward DEFINE command to worker
                String workerCmd = cmd;  // Send full command
                SLIPInterface* slip = bridge.getWorkerInterface(0);
                if (slip) {
                    slip->send((uint8_t*)workerCmd.c_str(), workerCmd.length());
                }
                
                Serial.printf("OK:DEFINED:%s\n", taskName.c_str());
            } else {
                Serial.println("ERROR:INVALID_DEFINE_FORMAT");
            }
        }
        else if (cmd.startsWith("EXEC:")) {
            // Format: EXEC:task_name:args
            // Example: EXEC:add:5,3
            int firstColon = cmd.indexOf(':');
            int secondColon = cmd.indexOf(':', firstColon + 1);
            
            if (secondColon > 0) {
                String taskName = cmd.substring(firstColon + 1, secondColon);
                String args = cmd.substring(secondColon + 1);
                
                if (taskDefinitions.find(taskName) != taskDefinitions.end()) {
                    // Forward command directly to worker via SLIP
                    String workerCmd = "EXEC:" + taskName + ":" + args;
                    
                    // Send text command over SLIP
                    SLIPInterface* slip = bridge.getWorkerInterface(0);
                    if (slip && slip->send((uint8_t*)workerCmd.c_str(), workerCmd.length())) {
                        int taskId = nextTaskId++;
                        Serial.printf("OK:SUBMITTED:%d\n", taskId);
                        Serial.flush();
                        
                        // Poll for response with proper formatting
                        delay(100);  // Give worker time to execute
                        uint8_t buffer[512];
                        for (int attempt = 0; attempt < 100; attempt++) {
                            int len = slip->receive(buffer, sizeof(buffer) - 1);
                            if (len > 0) {
                                buffer[len] = '\0';
                                String response = String((char*)buffer);
                                
                                // Format as RESULT:task_name:value for client
                                if (response.startsWith("OK:")) {
                                    String value = response.substring(3);  // Remove "OK:"
                                    Serial.printf("RESULT:%s:%s\n", taskName.c_str(), value.c_str());
                                } else if (response.startsWith("ERROR:")) {
                                    Serial.printf("RESULT:%s:ERROR:%s\n", taskName.c_str(), response.substring(6).c_str());
                                } else {
                                    Serial.println(response);  // Forward as-is
                                }
                                Serial.flush();
                                break;
                            }
                            delay(10);
                        }
                    } else {
                        Serial.println("ERROR:SEND_FAILED");
                    }
                } else {
                    Serial.println("ERROR:TASK_NOT_DEFINED");
                }
            } else {
                Serial.println("ERROR:INVALID_EXEC_FORMAT");
            }
        }
        else if (cmd == "LIST") {
            Serial.println("OK:TASKS:");
            for (auto& task : taskDefinitions) {
                Serial.printf("  %s\n", task.first.c_str());
            }
            Serial.println("END");
        }
        else if (cmd == "STATS") {
            Serial.println("\n--- SLIP Statistics ---");
            for (int i = 0; i < NUM_WORKERS; i++) {
                SLIPInterface* slip = bridge.getWorkerInterface(i);
                if (slip) {
                    Serial.printf("Worker %d: TX=%lu bytes (%lu pkts), RX=%lu bytes (%lu pkts)\n",
                                  i + 1,
                                  slip->getBytesSent(),
                                  slip->getPacketsSent(),
                                  slip->getBytesReceived(),
                                  slip->getPacketsReceived());
                }
            }
        }
        else if (cmd.startsWith("UPLOAD:")) {
            // Forward UPLOAD command to worker
            SLIPInterface* slip = bridge.getWorkerInterface(0);
            if (slip && slip->send((uint8_t*)cmd.c_str(), cmd.length())) {
                Serial.println("OK:UPLOAD_SENT");
                // Wait for worker response
                unsigned long start = millis();
                while (millis() - start < 5000) {
                    if (slip->available()) {
                        int len = slip->receive(buffer, sizeof(buffer) - 1);
                        if (len > 0) {
                            buffer[len] = '\0';
                            Serial.println((char*)buffer);
                            break;
                        }
                    }
                    delay(1);
                }
            } else {
                Serial.println("ERROR:UPLOAD_FAILED");
            }
        }
        else if (cmd.startsWith("CANVAS:")) {
            // CANVAS:TYPE:data - Forward Canvas primitives to worker
            int secondColon = cmd.indexOf(':', 7);
            if (secondColon > 0) {
                String canvasType = cmd.substring(7, secondColon);
                String data = cmd.substring(secondColon + 1);
                
                // Forward to worker
                String workerCmd = "CANVAS:" + canvasType + ":" + data;
                SLIPInterface* slip = bridge.getWorkerInterface(0);
                if (slip && slip->send((uint8_t*)workerCmd.c_str(), workerCmd.length())) {
                    // Wait for response (Canvas operations may take longer)
                    unsigned long start = millis();
                    while (millis() - start < 30000) {  // 30 second timeout
                        if (slip->available()) {
                            int len = slip->receive(buffer, sizeof(buffer) - 1);
                            if (len > 0) {
                                buffer[len] = '\0';
                                Serial.println((char*)buffer);  // Forward response to PC
                                Serial.flush();
                                break;
                            }
                        }
                        delay(1);
                    }
                } else {
                    Serial.println("ERROR:CANVAS_SEND_FAILED");
                }
            } else {
                Serial.println("ERROR:INVALID_CANVAS_FORMAT");
            }
        }
        else if (cmd.startsWith("UPLOAD:")) {
            // Forward UPLOAD command to worker
            SLIPInterface* slip = bridge.getWorkerInterface(0);
            if (slip && slip->send((uint8_t*)cmd.c_str(), cmd.length())) {
                Serial.println("OK:UPLOAD_SENT");
                // Wait for worker response
                delay(500);
                int len = slip->receive(buffer, sizeof(buffer) - 1);
                if (len > 0) {
                    buffer[len] = '\0';
                    Serial.println((char*)buffer);
                } else {
                    Serial.println("ERROR:NO_RESPONSE");
                }
            } else {
                Serial.println("ERROR:SEND_FAILED");
            }
        }
        else if (cmd == "RESET") {
            // Hardware reset worker by toggling GPIO
            Serial.println("OK:RESETTING_WORKER");
            digitalWrite(WORKER_RESET_PIN, LOW);   // Pull EN pin LOW
            delay(200);                             // Hold for 200ms
            digitalWrite(WORKER_RESET_PIN, HIGH);  // Release EN pin
            Serial.println("OK:WORKER_RESET_COMPLETE");
        }
        else if (cmd.startsWith("SETUART:")) {
            // Format: SETUART:1 or SETUART:2
            // Dynamically switch between UART1 and UART2
            int uartNum = cmd.substring(8).toInt();
            
            if (uartNum == 1 || uartNum == 2) {
                Serial.printf("OK:SWITCHING_TO_UART%d\n", uartNum);
                
                // Update UART pins based on selection
                int txPin, rxPin, resetPin;
                if (uartNum == 1) {
                    txPin = 17;
                    rxPin = 18;
                    resetPin = 4;
                } else {  // UART2
                    txPin = 16;
                    rxPin = 15;
                    resetPin = 5;
                }
                
                // Update reset pin
                pinMode(WORKER_RESET_PIN, INPUT);  // Release old pin
                pinMode(resetPin, OUTPUT);
                digitalWrite(resetPin, HIGH);
                
                // Reinitialize the SLIP interface with new pins
                bridge.switchUART(0, uartNum, rxPin, txPin);
                
                Serial.printf("OK:UART%d_ACTIVE (TX=%d, RX=%d, Reset=%d)\n", 
                             uartNum, txPin, rxPin, resetPin);
            } else {
                Serial.println("ERROR:INVALID_UART_NUMBER (use 1 or 2)");
            }
        }
        else {
            Serial.println("ERROR:UNKNOWN_COMMAND");
        }
    }
}

void loop() {
    // Process serial commands from PC
    processSerialCommand();
    
    // Check for async responses from workers over SLIP (rarely used since EXEC polls synchronously)
    for (int i = 0; i < NUM_WORKERS; i++) {
        SLIPInterface* slip = bridge.getWorkerInterface(i);
        if (slip && slip->available()) {
            uint8_t buffer[512];
            int len = slip->receive(buffer, sizeof(buffer) - 1);
            if (len > 0) {
                buffer[len] = '\0';  // Null terminate
                String response = String((char*)buffer);
                
                // Forward worker response to PC
                if (response.startsWith("OK:") || response.startsWith("ERROR:") || 
                    response.startsWith("RESULT:")) {
                    Serial.println(response);
                    Serial.flush();
                }
            }
        }
    }
    
    delay(10);
}

#endif // MASTER_NODE
