#ifdef WORKER_NODE

#include <Arduino.h>
#include "config.h"
#include "slip.h"
#include "peripheral_control.h"

SLIPInterface slipMaster(&Serial1, MASTER_RX_PIN, MASTER_TX_PIN);
PeripheralController peripherals;

// FreeRTOS task queue for dual-core execution
QueueHandle_t taskQueue;
SemaphoreHandle_t resultMutex;

// Task structure for core execution
struct TaskMessage {
    uint8_t type;
    char function[65];
    char args[256];
    uint8_t targetCore;  // 0 or 1
};

struct ResultMessage {
    char function[65];
    char result[256];
};

QueueHandle_t resultQueue;

// Core 0: Task Executor (parallel processing)
void taskExecutorCore0(void* params) {
    Serial.println("[Core 0] Task executor started");
    
    while (true) {
        TaskMessage task;
        if (xQueueReceive(taskQueue, &task, portMAX_DELAY)) {
            // Only process tasks targeted for Core 0
            if (task.targetCore != 0) {
                continue;
            }
            
            Serial.printf("[Core 0] Executing: %s(%s)\n", task.function, task.args);
            
            ResultMessage result;
            strcpy(result.function, task.function);
            
            // Check if it's a peripheral command
            if (strncmp(task.function, "GPIO", 4) == 0 || 
                strncmp(task.function, "PWM", 3) == 0 ||
                strncmp(task.function, "I2C", 3) == 0 ||
                strncmp(task.function, "SPI", 3) == 0 ||
                strncmp(task.function, "UART", 4) == 0 ||
                strncmp(task.function, "CAN", 3) == 0 ||
                strncmp(task.function, "ADC", 3) == 0 ||
                strncmp(task.function, "DAC", 3) == 0) {
                
                // Execute peripheral command
                String cmd = String(task.function) + ":" + String(task.args);
                String res = peripherals.executeCommand(cmd);
                strcpy(result.result, res.c_str());
            } 
            // Arithmetic tasks
            else if (strcmp(task.function, "add") == 0) {
                int x, y;
                if (sscanf(task.args, "%d,%d", &x, &y) == 2) {
                    snprintf(result.result, sizeof(result.result), "%d", x + y);
                }
            } 
            else if (strcmp(task.function, "mul") == 0) {
                int x, y;
                if (sscanf(task.args, "%d,%d", &x, &y) == 2) {
                    snprintf(result.result, sizeof(result.result), "%d", x * y);
                }
            }
            else {
                strcpy(result.result, "ERROR:UNKNOWN_FUNCTION");
            }
            
            // Send result to queue
            xQueueSend(resultQueue, &result, portMAX_DELAY);
            Serial.printf("[Core 0] Result: %s\n", result.result);
        }
    }
}

// Core 1: Task Executor (parallel processing)
void taskExecutorCore1(void* params) {
    Serial.println("[Core 1] Task executor started");
    
    while (true) {
        TaskMessage task;
        if (xQueueReceive(taskQueue, &task, portMAX_DELAY)) {
            // Only process tasks targeted for Core 1
            if (task.targetCore != 1) {
                continue;
            }
            
            Serial.printf("[Core 1] Executing: %s(%s)\n", task.function, task.args);
            
            ResultMessage result;
            strcpy(result.function, task.function);
            
            // Check if it's a peripheral command
            if (strncmp(task.function, "GPIO", 4) == 0 || 
                strncmp(task.function, "PWM", 3) == 0 ||
                strncmp(task.function, "I2C", 3) == 0 ||
                strncmp(task.function, "SPI", 3) == 0 ||
                strncmp(task.function, "UART", 4) == 0 ||
                strncmp(task.function, "CAN", 3) == 0 ||
                strncmp(task.function, "ADC", 3) == 0 ||
                strncmp(task.function, "DAC", 3) == 0) {
                
                // Execute peripheral command
                String cmd = String(task.function) + ":" + String(task.args);
                String res = peripherals.executeCommand(cmd);
                strcpy(result.result, res.c_str());
            } 
            // Arithmetic tasks
            else if (strcmp(task.function, "add") == 0) {
                int x, y;
                if (sscanf(task.args, "%d,%d", &x, &y) == 2) {
                    snprintf(result.result, sizeof(result.result), "%d", x + y);
                }
            } 
            else if (strcmp(task.function, "mul") == 0) {
                int x, y;
                if (sscanf(task.args, "%d,%d", &x, &y) == 2) {
                    snprintf(result.result, sizeof(result.result), "%d", x * y);
                }
            }
            else {
                strcpy(result.result, "ERROR:UNKNOWN_FUNCTION");
            }
            
            // Send result to queue
            xQueueSend(resultQueue, &result, portMAX_DELAY);
            Serial.printf("[Core 1] Result: %s\n", result.result);
        }
    }
}

void setup() {
    // Initialize USB serial for debugging
    Serial.begin(115200);
    while (!Serial && millis() < 3000);
    
    Serial.println("\n\n=================================");
    Serial.println("ESP32-S3 Broccoli Worker Node");
    Serial.println("Dual-Core + Peripheral Control");
    Serial.println("=================================");
    
    // Create FreeRTOS queues
    taskQueue = xQueueCreate(10, sizeof(TaskMessage));
    resultQueue = xQueueCreate(10, sizeof(ResultMessage));
    resultMutex = xSemaphoreCreateMutex();
    
    // Initialize SLIP connection to master
    slipMaster.begin(SLIP_BAUDRATE);
    
    // Start task executors on both cores
    xTaskCreatePinnedToCore(
        taskExecutorCore0,
        "TaskCore0",
        8192,
        NULL,
        1,
        NULL,
        0  // Core 0
    );
    
    xTaskCreatePinnedToCore(
        taskExecutorCore1,
        "TaskCore1",
        8192,
        NULL,
        1,
        NULL,
        1  // Core 1
    );
    
    Serial.println("\n✓ Worker node ready!");
    Serial.println("✓ Dual-core task execution enabled");
    Serial.println("✓ Peripheral control available");
    Serial.println("✓ Connected to master via SLIP");
}


void loop() {
    static unsigned long lastStats = 0;
    
    // Receive messages from master (SLIP communication on Main core)
    if (slipMaster.available()) {
        uint8_t buffer[PACKET_BUFFER_SIZE];
        int len = slipMaster.receive(buffer, PACKET_BUFFER_SIZE);
        
        if (len >= 131) {
            uint8_t msgType = buffer[0];
            
            if (msgType == 1) {  // MSG_TYPE_TASK
                // Parse task
                TaskMessage task;
                task.type = msgType;
                memcpy(task.function, buffer + 65, 64);
                task.function[64] = '\0';
                
                // Parse arguments
                uint16_t dataLen = (buffer[129] << 8) | buffer[130];
                if (dataLen > 0 && len > 131) {
                    uint16_t argLen = (dataLen < 255) ? dataLen : 255;
                    memcpy(task.args, buffer + 131, argLen);
                    task.args[argLen] = '\0';
                }
                
                // Parse target core (look for "CORE:0" or "CORE:1" in args)
                task.targetCore = 0;  // Default to Core 0
                if (strstr(task.args, "CORE:1") != NULL) {
                    task.targetCore = 1;
                    // Remove "CORE:1" from args
                    char* coreTag = strstr(task.args, "CORE:1");
                    if (coreTag) {
                        memmove(coreTag, coreTag + 6, strlen(coreTag + 6) + 1);
                    }
                } else if (strstr(task.args, "CORE:0") != NULL) {
                    task.targetCore = 0;
                    // Remove "CORE:0" from args
                    char* coreTag = strstr(task.args, "CORE:0");
                    if (coreTag) {
                        memmove(coreTag, coreTag + 6, strlen(coreTag + 6) + 1);
                    }
                }
                
                Serial.printf("[Main] Received task: %s(%s) -> Core %d\n", 
                             task.function, task.args, task.targetCore);
                
                // Send to task queue
                xQueueSend(taskQueue, &task, portMAX_DELAY);
            }
            else if (msgType == 3) {  // MSG_TYPE_PING
                Serial.println("[Main] Received ping, sending pong...");
                
                uint8_t response[131];
                response[0] = 4;  // MSG_TYPE_PONG
                strcpy((char*)response + 1, "worker");
                strcpy((char*)response + 33, "master");
                strcpy((char*)response + 65, "pong");
                response[129] = 0;
                response[130] = 0;
                
                slipMaster.send(response, 131);
            }
        }
    }
    
    // Check for completed tasks and send results
    ResultMessage result;
    if (xQueueReceive(resultQueue, &result, 0)) {
        // Send result back to master
        uint8_t response[131 + 256];
        response[0] = 2;  // MSG_TYPE_RESULT
        strcpy((char*)response + 1, "worker");
        strcpy((char*)response + 33, "master");
        strcpy((char*)response + 65, result.function);
        
        uint16_t resultLen = strlen(result.result);
        response[129] = (resultLen >> 8) & 0xFF;
        response[130] = resultLen & 0xFF;
        memcpy(response + 131, result.result, resultLen);
        
        slipMaster.send(response, 131 + resultLen);
        Serial.printf("[Main] Sent result: %s = %s\n", result.function, result.result);
    }
    
    // Print statistics every 5 seconds
    if (millis() - lastStats > 5000) {
        lastStats = millis();
        
        Serial.println("\n--- SLIP Statistics ---");
        Serial.printf("TX: %lu bytes (%lu packets)\n", 
                      slipMaster.getBytesSent(),
                      slipMaster.getPacketsSent());
        Serial.printf("RX: %lu bytes (%lu packets)\n",
                      slipMaster.getBytesReceived(),
                      slipMaster.getPacketsReceived());
        Serial.printf("Task Queue: %d pending\n", uxQueueMessagesWaiting(taskQueue));
        Serial.printf("Result Queue: %d pending\n", uxQueueMessagesWaiting(resultQueue));
    }
    
    delay(1);
}

#endif // WORKER_NODE
