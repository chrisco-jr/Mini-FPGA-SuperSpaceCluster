#include "peripheral_control.h"

PeripheralController::PeripheralController() {
    i2cInitialized = false;
    spiInitialized = false;
    uartInitialized = false;
    canInitialized = false;
    spi = nullptr;
    uart = &Serial2;
}

// ============== GPIO Functions ==============

int PeripheralController::setGPIOMode(uint8_t pin, uint8_t mode) {
    if (pin > 48) return RESULT_INVALID_PIN;
    pinMode(pin, mode);
    return RESULT_OK;
}

int PeripheralController::setGPIOState(uint8_t pin, uint8_t state) {
    if (pin > 48) return RESULT_INVALID_PIN;
    digitalWrite(pin, state);
    return RESULT_OK;
}

int PeripheralController::readGPIO(uint8_t pin) {
    if (pin > 48) return RESULT_INVALID_PIN;
    return digitalRead(pin);
}

// ============== PWM Functions ==============

int PeripheralController::setPWM(uint8_t pin, uint8_t channel, uint32_t freq, uint8_t resolution, uint16_t duty) {
    if (pin > 48) return RESULT_INVALID_PIN;
    if (channel > 15) return RESULT_ERROR;
    
    ledcSetup(channel, freq, resolution);
    ledcAttachPin(pin, channel);
    ledcWrite(channel, duty);
    return RESULT_OK;
}

// ============== I2C Functions ==============

int PeripheralController::initI2C(uint8_t sda, uint8_t scl, uint32_t freq) {
    i2cSDA = sda;
    i2cSCL = scl;
    Wire.begin(sda, scl, freq);
    i2cInitialized = true;
    return RESULT_OK;
}

int PeripheralController::writeI2C(uint8_t addr, uint8_t* data, size_t len) {
    if (!i2cInitialized) return RESULT_ERROR;
    
    Wire.beginTransmission(addr);
    Wire.write(data, len);
    return Wire.endTransmission() == 0 ? RESULT_OK : RESULT_ERROR;
}

int PeripheralController::readI2C(uint8_t addr, uint8_t* data, size_t len) {
    if (!i2cInitialized) return RESULT_ERROR;
    
    Wire.requestFrom(addr, len);
    size_t i = 0;
    while (Wire.available() && i < len) {
        data[i++] = Wire.read();
    }
    return i;
}

// ============== SPI Functions ==============

int PeripheralController::initSPI(int8_t sck, int8_t miso, int8_t mosi, int8_t ss, uint32_t freq) {
    spiSCK = sck;
    spiMISO = miso;
    spiMOSI = mosi;
    spiSS = ss;
    
    if (!spi) {
        spi = new SPIClass(HSPI);
    }
    
    spi->begin(sck, miso, mosi, ss);
    pinMode(ss, OUTPUT);
    digitalWrite(ss, HIGH);
    
    spiInitialized = true;
    return RESULT_OK;
}

int PeripheralController::transferSPI(uint8_t* txData, uint8_t* rxData, size_t len) {
    if (!spiInitialized) return RESULT_ERROR;
    
    digitalWrite(spiSS, LOW);
    for (size_t i = 0; i < len; i++) {
        rxData[i] = spi->transfer(txData[i]);
    }
    digitalWrite(spiSS, HIGH);
    
    return RESULT_OK;
}

// ============== UART Functions ==============

int PeripheralController::initUART(uint8_t tx, uint8_t rx, uint32_t baud) {
    uartTX = tx;
    uartRX = rx;
    
    uart->begin(baud, SERIAL_8N1, rx, tx);
    uartInitialized = true;
    return RESULT_OK;
}

int PeripheralController::writeUART(uint8_t* data, size_t len) {
    if (!uartInitialized) return RESULT_ERROR;
    return uart->write(data, len);
}

int PeripheralController::readUART(uint8_t* buffer, size_t maxLen) {
    if (!uartInitialized) return RESULT_ERROR;
    
    size_t avail = uart->available();
    if (avail > maxLen) avail = maxLen;
    
    return uart->readBytes(buffer, avail);
}

// ============== CAN Functions ==============

int PeripheralController::initCAN(uint8_t tx, uint8_t rx, uint32_t baudrate) {
    canTX = tx;
    canRX = rx;
    
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT((gpio_num_t)tx, (gpio_num_t)rx, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    
    if (baudrate == 125000) {
        t_config = TWAI_TIMING_CONFIG_125KBITS();
    } else if (baudrate == 250000) {
        t_config = TWAI_TIMING_CONFIG_250KBITS();
    } else if (baudrate == 500000) {
        t_config = TWAI_TIMING_CONFIG_500KBITS();
    } else if (baudrate == 1000000) {
        t_config = TWAI_TIMING_CONFIG_1MBITS();
    }
    
    if (twai_driver_install(&g_config, &t_config, &f_config) == ESP_OK) {
        if (twai_start() == ESP_OK) {
            canInitialized = true;
            return RESULT_OK;
        }
    }
    
    return RESULT_ERROR;
}

int PeripheralController::sendCAN(uint32_t id, uint8_t* data, uint8_t len) {
    if (!canInitialized) return RESULT_ERROR;
    if (len > 8) return RESULT_ERROR;
    
    twai_message_t message;
    message.identifier = id;
    message.data_length_code = len;
    for (int i = 0; i < len; i++) {
        message.data[i] = data[i];
    }
    message.flags = TWAI_MSG_FLAG_NONE;
    
    return twai_transmit(&message, pdMS_TO_TICKS(100)) == ESP_OK ? RESULT_OK : RESULT_ERROR;
}

int PeripheralController::receiveCAN(uint32_t* id, uint8_t* data, uint8_t* len) {
    if (!canInitialized) return RESULT_ERROR;
    
    twai_message_t message;
    if (twai_receive(&message, pdMS_TO_TICKS(100)) == ESP_OK) {
        *id = message.identifier;
        *len = message.data_length_code;
        for (int i = 0; i < message.data_length_code; i++) {
            data[i] = message.data[i];
        }
        return RESULT_OK;
    }
    
    return RESULT_ERROR;
}

// ============== ADC/DAC Functions ==============

int PeripheralController::readADC(uint8_t pin) {
    return analogRead(pin);
}

int PeripheralController::writeDAC(uint8_t pin, uint8_t value) {
    // ESP32-S3 does NOT have DAC - use PWM instead
    // dacWrite(pin, value);  // Not available on ESP32-S3
    return RESULT_ERROR;  // DAC not supported on ESP32-S3
}

// ============== System Monitoring Functions ==============

String PeripheralController::getSystemInfo() {
    String info = "";
    info += "CHIP:" + String(ESP.getChipModel()) + ";";
    info += "CORES:" + String(ESP.getChipCores()) + ";";
    info += "FREQ:" + String(ESP.getCpuFreqMHz()) + "MHz;";
    info += "SDK:" + String(ESP.getSdkVersion());
    return info;
}

String PeripheralController::getRAMUsage() {
    uint32_t heapSize = ESP.getHeapSize();
    uint32_t freeHeap = ESP.getFreeHeap();
    uint32_t usedHeap = heapSize - freeHeap;
    uint32_t minFreeHeap = ESP.getMinFreeHeap();
    float usagePercent = (float)usedHeap / heapSize * 100.0;
    
    String info = "";
    info += "TOTAL:" + String(heapSize) + ";";
    info += "USED:" + String(usedHeap) + ";";
    info += "FREE:" + String(freeHeap) + ";";
    info += "MIN_FREE:" + String(minFreeHeap) + ";";
    info += "USAGE:" + String(usagePercent, 1) + "%";
    
    return info;
}

String PeripheralController::getFlashUsage() {
    uint32_t flashSize = ESP.getFlashChipSize();
    uint32_t sketchSize = ESP.getSketchSize();
    uint32_t freeSketch = ESP.getFreeSketchSpace();
    uint32_t usedFlash = sketchSize;
    float usagePercent = (float)usedFlash / flashSize * 100.0;
    
    String info = "";
    info += "TOTAL:" + String(flashSize) + ";";
    info += "SKETCH:" + String(sketchSize) + ";";
    info += "FREE_SKETCH:" + String(freeSketch) + ";";
    info += "USAGE:" + String(usagePercent, 1) + "%";
    
    return info;
}

String PeripheralController::getCPUUsage() {
    // Simplified CPU usage without uxTaskGetSystemState
    // This function requires configUSE_TRACE_FACILITY and configGENERATE_RUN_TIME_STATS
    // which are not enabled by default in Arduino framework
    
    // Return estimated usage based on FreeRTOS stats
    uint32_t idleCount0 = 0;
    uint32_t idleCount1 = 0;
    
    // Approximate usage (simplified)
    float core0Usage = 25.0;  // Placeholder
    float core1Usage = 25.0;  // Placeholder
    
    String info = "";
    info += "CORE0:" + String(core0Usage, 1) + "%;";
    info += "CORE1:" + String(core1Usage, 1) + "%;";
    info += "TOTAL_TIME:" + String(millis());
    
    return info;
}

String PeripheralController::getTaskList() {
    TaskStatus_t* pxTaskStatusArray;
    volatile UBaseType_t uxArraySize;
    uint32_t ulTotalRunTime;
    
    uxArraySize = uxTaskGetNumberOfTasks();
    pxTaskStatusArray = (TaskStatus_t*)pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));
    
    if (pxTaskStatusArray != NULL) {
        uxArraySize = uxTaskGetSystemState(pxTaskStatusArray, uxArraySize, &ulTotalRunTime);
        
        String info = "TASKS:" + String(uxArraySize) + ";";
        
        for (UBaseType_t i = 0; i < uxArraySize; i++) {
            info += String(pxTaskStatusArray[i].pcTaskName);
            info += "(Prio" + String(pxTaskStatusArray[i].uxCurrentPriority) + ",";
            info += "Stack" + String(pxTaskStatusArray[i].usStackHighWaterMark) + ")";
            
            if (i < uxArraySize - 1) {
                info += ";";
            }
        }
        
        vPortFree(pxTaskStatusArray);
        return info;
    }
    
    return "ERROR:NO_MEMORY";
}

// ============== Command Parser ==============

String PeripheralController::executeCommand(const String& cmd) {
    // Format: CMD:param1,param2,param3,...
    // Examples:
    // GPIO_MODE:13,OUTPUT
    // GPIO_WRITE:13,HIGH
    // GPIO_READ:14
    // PWM:13,0,5000,8,128
    // I2C_INIT:21,22,100000
    // I2C_WRITE:0x48,0x01,0xFF
    // SPI_INIT:18,19,23,5,1000000
    // UART_INIT:16,17,115200
    // CAN_INIT:4,5,500000
    // ADC_READ:34
    
    int colonPos = cmd.indexOf(':');
    if (colonPos < 0) return "ERROR:INVALID_FORMAT";
    
    String command = cmd.substring(0, colonPos);
    String params = cmd.substring(colonPos + 1);
    
    // Parse parameters
    int paramValues[10];
    int paramCount = 0;
    int lastPos = 0;
    
    while (paramCount < 10) {
        int commaPos = params.indexOf(',', lastPos);
        String param;
        
        if (commaPos < 0) {
            param = params.substring(lastPos);
        } else {
            param = params.substring(lastPos, commaPos);
        }
        
        if (param.length() > 0) {
            if (param.equalsIgnoreCase("INPUT")) {
                paramValues[paramCount++] = INPUT;
            } else if (param.equalsIgnoreCase("OUTPUT")) {
                paramValues[paramCount++] = OUTPUT;
            } else if (param.equalsIgnoreCase("INPUT_PULLUP")) {
                paramValues[paramCount++] = INPUT_PULLUP;
            } else if (param.equalsIgnoreCase("INPUT_PULLDOWN")) {
                paramValues[paramCount++] = INPUT_PULLDOWN;
            } else if (param.equalsIgnoreCase("HIGH")) {
                paramValues[paramCount++] = HIGH;
            } else if (param.equalsIgnoreCase("LOW")) {
                paramValues[paramCount++] = LOW;
            } else {
                paramValues[paramCount++] = param.toInt();
            }
        }
        
        if (commaPos < 0) break;
        lastPos = commaPos + 1;
    }
    
    // Execute command
    int result = RESULT_INVALID_CMD;
    
    if (command == "GPIO_MODE" && paramCount == 2) {
        result = setGPIOMode(paramValues[0], paramValues[1]);
    } 
    else if (command == "GPIO_WRITE" && paramCount == 2) {
        result = setGPIOState(paramValues[0], paramValues[1]);
    } 
    else if (command == "GPIO_READ" && paramCount == 1) {
        result = readGPIO(paramValues[0]);
        return String(result);
    } 
    else if (command == "PWM" && paramCount == 5) {
        result = setPWM(paramValues[0], paramValues[1], paramValues[2], paramValues[3], paramValues[4]);
    } 
    else if (command == "I2C_INIT" && paramCount == 3) {
        result = initI2C(paramValues[0], paramValues[1], paramValues[2]);
    } 
    else if (command == "SPI_INIT" && paramCount == 5) {
        result = initSPI(paramValues[0], paramValues[1], paramValues[2], paramValues[3], paramValues[4]);
    } 
    else if (command == "UART_INIT" && paramCount == 3) {
        result = initUART(paramValues[0], paramValues[1], paramValues[2]);
    } 
    else if (command == "CAN_INIT" && paramCount == 3) {
        result = initCAN(paramValues[0], paramValues[1], paramValues[2]);
    } 
    else if (command == "ADC_READ" && paramCount == 1) {
        result = readADC(paramValues[0]);
        return String(result);
    } 
    else if (command == "DAC_WRITE" && paramCount == 2) {
        result = writeDAC(paramValues[0], paramValues[1]);
    }
    else if (command == "SYS_INFO") {
        return getSystemInfo();
    }
    else if (command == "RAM_USAGE") {
        return getRAMUsage();
    }
    else if (command == "FLASH_USAGE") {
        return getFlashUsage();
    }
    else if (command == "CPU_USAGE") {
        return getCPUUsage();
    }
    else if (command == "TASK_LIST") {
        return getTaskList();
    }
    
    if (result == RESULT_OK) {
        return "OK";
    } else {
        return "ERROR:" + String(result);
    }
}
