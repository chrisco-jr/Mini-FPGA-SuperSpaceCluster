#ifndef PERIPHERAL_CONTROL_H
#define PERIPHERAL_CONTROL_H

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <driver/twai.h>

// Peripheral command types
#define CMD_GPIO_MODE       1
#define CMD_GPIO_WRITE      2
#define CMD_GPIO_READ       3
#define CMD_PWM_WRITE       4
#define CMD_I2C_INIT        5
#define CMD_I2C_WRITE       6
#define CMD_I2C_READ        7
#define CMD_SPI_INIT        8
#define CMD_SPI_TRANSFER    9
#define CMD_UART_INIT       10
#define CMD_UART_WRITE      11
#define CMD_UART_READ       12
#define CMD_CAN_INIT        13
#define CMD_CAN_SEND        14
#define CMD_CAN_RECEIVE     15
#define CMD_ADC_READ        16
#define CMD_DAC_WRITE       17
#define CMD_SYS_INFO        18
#define CMD_RAM_USAGE       19
#define CMD_FLASH_USAGE     20
#define CMD_CPU_USAGE       21
#define CMD_TASK_LIST       22

// Result codes
#define RESULT_OK           0
#define RESULT_ERROR        -1
#define RESULT_INVALID_CMD  -2
#define RESULT_INVALID_PIN  -3

class PeripheralController {
public:
    PeripheralController();
    
    // GPIO Functions
    int setGPIOMode(uint8_t pin, uint8_t mode);  // INPUT, OUTPUT, INPUT_PULLUP, INPUT_PULLDOWN
    int setGPIOState(uint8_t pin, uint8_t state); // HIGH, LOW
    int readGPIO(uint8_t pin);
    
    // PWM Functions
    int setPWM(uint8_t pin, uint8_t channel, uint32_t freq, uint8_t resolution, uint16_t duty);
    
    // I2C Functions
    int initI2C(uint8_t sda, uint8_t scl, uint32_t freq);
    int writeI2C(uint8_t addr, uint8_t* data, size_t len);
    int readI2C(uint8_t addr, uint8_t* data, size_t len);
    
    // SPI Functions
    int initSPI(int8_t sck, int8_t miso, int8_t mosi, int8_t ss, uint32_t freq);
    int transferSPI(uint8_t* txData, uint8_t* rxData, size_t len);
    
    // UART Functions (using Serial2 as example)
    int initUART(uint8_t tx, uint8_t rx, uint32_t baud);
    int writeUART(uint8_t* data, size_t len);
    int readUART(uint8_t* buffer, size_t maxLen);
    
    // CAN Functions
    int initCAN(uint8_t tx, uint8_t rx, uint32_t baudrate);
    int sendCAN(uint32_t id, uint8_t* data, uint8_t len);
    int receiveCAN(uint32_t* id, uint8_t* data, uint8_t* len);
    
    // ADC/DAC Functions
    int readADC(uint8_t pin);
    int writeDAC(uint8_t pin, uint8_t value);
    
    // System Monitoring Functions
    String getSystemInfo();
    String getRAMUsage();
    String getFlashUsage();
    String getCPUUsage();
    String getTaskList();
    
    // Execute peripheral command from string
    String executeCommand(const String& cmd);
    
private:
    bool i2cInitialized;
    bool spiInitialized;
    bool uartInitialized;
    bool canInitialized;
    
    uint8_t i2cSDA, i2cSCL;
    int8_t spiSCK, spiMISO, spiMOSI, spiSS;
    uint8_t uartTX, uartRX;
    uint8_t canTX, canRX;
    
    SPIClass* spi;
    HardwareSerial* uart;
};

#endif // PERIPHERAL_CONTROL_H
