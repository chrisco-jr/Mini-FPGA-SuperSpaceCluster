# Peripheral Control for MicroPython
# GPIO, PWM, I2C, SPI, UART, CAN, ADC/DAC control

import machine
from machine import Pin, PWM, ADC, I2C, SPI, UART
try:
    from machine import DAC
except ImportError:
    DAC = None  # ESP32-S3 doesn't have DAC


class PeripheralController:
    """Hardware peripheral control matching C++ API"""
    
    def __init__(self):
        self.i2c = None
        self.spi = None
        self.uart_peripheral = None
        self.can = None
        self.pwm_channels = {}
        print("[Peripherals] Controller initialized")
    
    # GPIO Control
    def gpio_mode(self, pin, mode):
        """Set GPIO pin mode (INPUT/OUTPUT)"""
        try:
            if mode.upper() == "OUTPUT":
                p = Pin(pin, Pin.OUT)
            else:
                p = Pin(pin, Pin.IN)
            return f"OK:GPIO{pin}={mode}"
        except Exception as e:
            return f"ERROR:{e}"
    
    def gpio_write(self, pin, value):
        """Write digital value to GPIO pin"""
        try:
            p = Pin(pin, Pin.OUT)
            p.value(int(value))
            return f"OK:GPIO{pin}={value}"
        except Exception as e:
            return f"ERROR:{e}"
    
    def gpio_read(self, pin):
        """Read digital value from GPIO pin"""
        try:
            p = Pin(pin, Pin.IN)
            value = p.value()
            return f"OK:{value}"
        except Exception as e:
            return f"ERROR:{e}"
    
    # PWM Control
    def pwm_setup(self, pin, freq, duty):
        """Setup PWM on pin with frequency and duty cycle (0-1023)"""
        try:
            if pin not in self.pwm_channels:
                self.pwm_channels[pin] = PWM(Pin(pin), freq=freq)
            else:
                self.pwm_channels[pin].freq(freq)
            
            self.pwm_channels[pin].duty(int(duty))
            return f"OK:PWM{pin}={freq}Hz,{duty}"
        except Exception as e:
            return f"ERROR:{e}"
    
    # ADC Control
    def adc_read(self, pin):
        """Read analog value from ADC pin"""
        try:
            adc = ADC(Pin(pin))
            adc.atten(ADC.ATTN_11DB)  # Full range: 0-3.3V
            value = adc.read()
            return f"OK:{value}"
        except Exception as e:
            return f"ERROR:{e}"
    
    # DAC Control
    def dac_write(self, pin, value):
        """Write analog value to DAC pin (0-255)"""
        if DAC is None:
            return "ERROR:DAC_not_available_on_ESP32-S3"
        try:
            dac = DAC(Pin(pin))
            dac.write(int(value))
            return f"OK:DAC{pin}={value}"
        except Exception as e:
            return f"ERROR:{e}"
    
    # I2C Control
    def i2c_init(self, sda, scl, freq):
        """Initialize I2C bus"""
        try:
            self.i2c = I2C(0, scl=Pin(scl), sda=Pin(sda), freq=freq)
            devices = self.i2c.scan()
            return f"OK:I2C_initialized,devices={devices}"
        except Exception as e:
            return f"ERROR:{e}"
    
    def i2c_write(self, addr, data):
        """Write data to I2C device"""
        try:
            if self.i2c is None:
                return "ERROR:I2C_not_initialized"
            self.i2c.writeto(addr, bytes(data))
            return f"OK:I2C_write_{len(data)}_bytes"
        except Exception as e:
            return f"ERROR:{e}"
    
    def i2c_read(self, addr, nbytes):
        """Read data from I2C device"""
        try:
            if self.i2c is None:
                return "ERROR:I2C_not_initialized"
            data = self.i2c.readfrom(addr, nbytes)
            return f"OK:{list(data)}"
        except Exception as e:
            return f"ERROR:{e}"
    
    # SPI Control
    def spi_init(self, miso, mosi, sck, cs, freq):
        """Initialize SPI bus"""
        try:
            self.spi = SPI(1, baudrate=freq, polarity=0, phase=0,
                          sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
            self.spi_cs = Pin(cs, Pin.OUT)
            self.spi_cs.value(1)  # CS high (inactive)
            return f"OK:SPI_initialized_{freq}Hz"
        except Exception as e:
            return f"ERROR:{e}"
    
    def spi_transfer(self, data):
        """Transfer data over SPI"""
        try:
            if self.spi is None:
                return "ERROR:SPI_not_initialized"
            
            self.spi_cs.value(0)  # CS low (active)
            result = self.spi.read(len(data), data[0] if data else 0)
            self.spi_cs.value(1)  # CS high (inactive)
            
            return f"OK:{list(result)}"
        except Exception as e:
            return f"ERROR:{e}"
    
    # UART Control
    def uart_init(self, rx, tx, baudrate):
        """Initialize UART peripheral"""
        try:
            self.uart_peripheral = UART(2, baudrate=baudrate, tx=tx, rx=rx)
            return f"OK:UART_initialized_{baudrate}"
        except Exception as e:
            return f"ERROR:{e}"
    
    def uart_write(self, data):
        """Write data to UART"""
        try:
            if self.uart_peripheral is None:
                return "ERROR:UART_not_initialized"
            
            if isinstance(data, str):
                data = data.encode()
            
            self.uart_peripheral.write(data)
            return f"OK:UART_write_{len(data)}_bytes"
        except Exception as e:
            return f"ERROR:{e}"
    
    def uart_read(self, nbytes):
        """Read data from UART"""
        try:
            if self.uart_peripheral is None:
                return "ERROR:UART_not_initialized"
            
            data = self.uart_peripheral.read(nbytes)
            if data:
                return f"OK:{list(data)}"
            return "OK:[]"
        except Exception as e:
            return f"ERROR:{e}"
    
    # CAN Control (ESP32 TWAI/CAN)
    def can_init(self, tx, rx, baudrate):
        """Initialize CAN bus (TWAI driver)"""
        try:
            # MicroPython doesn't have built-in CAN yet
            # Would need custom driver or use machine.bitstream
            return f"WARNING:CAN_not_supported_in_standard_MicroPython"
        except Exception as e:
            return f"ERROR:{e}"
    
    # Parse and execute peripheral command
    def execute_command(self, cmd_string):
        """Parse and execute peripheral command string"""
        try:
            parts = cmd_string.split(':')
            cmd = parts[0]
            
            if cmd.startswith("GPIO_MODE"):
                args = parts[1].split(',')
                return self.gpio_mode(int(args[0]), args[1])
            
            elif cmd.startswith("GPIO_WRITE"):
                args = parts[1].split(',')
                return self.gpio_write(int(args[0]), int(args[1]))
            
            elif cmd.startswith("GPIO_READ"):
                return self.gpio_read(int(parts[1]))
            
            elif cmd.startswith("PWM"):
                args = parts[1].split(',')
                return self.pwm_setup(int(args[0]), int(args[1]), int(args[2]))
            
            elif cmd.startswith("ADC_READ"):
                return self.adc_read(int(parts[1]))
            
            elif cmd.startswith("DAC_WRITE"):
                args = parts[1].split(',')
                return self.dac_write(int(args[0]), int(args[1]))
            
            elif cmd.startswith("I2C_INIT"):
                args = parts[1].split(',')
                return self.i2c_init(int(args[0]), int(args[1]), int(args[2]))
            
            elif cmd.startswith("SPI_INIT"):
                args = parts[1].split(',')
                return self.spi_init(int(args[0]), int(args[1]), int(args[2]), 
                                    int(args[3]), int(args[4]))
            
            elif cmd.startswith("UART_INIT"):
                args = parts[1].split(',')
                return self.uart_init(int(args[0]), int(args[1]), int(args[2]))
            
            else:
                return f"ERROR:Unknown_command_{cmd}"
        
        except Exception as e:
            return f"ERROR:{e}"
