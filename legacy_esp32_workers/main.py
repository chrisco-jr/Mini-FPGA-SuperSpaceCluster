# Main Worker Program for MicroPython ESP32
# Combines all modules: SLIP, peripherals, dual-core, tasks, monitoring

import time
from machine import Pin

# Import our modules
from slip_protocol import SLIPInterface
from peripheral_control import PeripheralController
from system_monitor import SystemMonitor
from dual_core import DualCoreExecutor
from task_executor import TaskExecutor
from canvas import create_canvas_api

# Configuration
MASTER_UART_ID = 1
MASTER_TX_PIN = 18  # Worker TX=18 connects to Master RX=18 (crossover)
MASTER_RX_PIN = 17  # Worker RX=17 connects to Master TX=17 (crossover)
SLIP_BAUDRATE = 921600

# LED for status indication
LED_PIN = 2


class WorkerNode:
    """Main worker node that handles all functionality"""
    
    def __init__(self):
        print("\n" + "="*50)
        print("ESP32 MicroPython Worker Node")
        print("="*50)
        
        # Initialize LED
        self.led = Pin(LED_PIN, Pin.OUT)
        self.blink_led(3)
        
        # Initialize SLIP communication
        self.slip = SLIPInterface(MASTER_UART_ID, MASTER_TX_PIN, 
                                  MASTER_RX_PIN, SLIP_BAUDRATE)
        
        # Initialize subsystems
        self.peripherals = PeripheralController()
        self.monitor = SystemMonitor()
        self.dual_core = DualCoreExecutor()
        
        # Add peripheral functions to global scope first
        self._setup_global_functions()
        
        # Initialize task executor with the configured global scope
        self.task_executor = TaskExecutor(self.dual_core, globals())
        
        # Start Core 1 worker thread
        self.dual_core.start_core1_worker()
        
        # Create Canvas API
        self.canvas = create_canvas_api(self.task_executor)
        
        print("\n[Worker] All systems initialized")
        print("[Worker] Ready to receive commands")
        self.blink_led(2)
    
    def _setup_global_functions(self):
        """Add peripheral and system functions to global scope"""
        # Make peripherals and monitor available globally
        g = globals()
        g['peripherals'] = self.peripherals
        g['monitor'] = self.monitor
        
        # Import machine and common modules for tasks
        import machine
        from machine import Pin, PWM, ADC, I2C, SPI, UART
        g['machine'] = machine
        g['Pin'] = Pin
        g['PWM'] = PWM
        g['ADC'] = ADC
        g['I2C'] = I2C
        g['SPI'] = SPI
        g['UART'] = UART
        
        # Create wrapper functions for peripherals
        g['i2c_init'] = lambda sda, scl, freq=100000: I2C(0, scl=Pin(scl), sda=Pin(sda), freq=freq)
        g['spi_init'] = lambda sck, miso, mosi, freq=1000000: SPI(1, baudrate=freq, sck=Pin(sck), miso=Pin(miso), mosi=Pin(mosi))
        g['uart_init'] = lambda tx, rx, baud=115200: UART(2, baudrate=baud, tx=Pin(tx), rx=Pin(rx))
        g['can_init'] = lambda tx, rx, baudrate=500000: f"CAN_initialized_TX{tx}_RX{rx}"  # Placeholder
        g['adc'] = lambda pin: ADC(Pin(pin)).read()
        g['pwm_control'] = lambda pin, channel, freq, resolution, duty: PWM(Pin(pin), freq=freq, duty=duty)
        g['ram'] = lambda: self.monitor.get_ram_usage()
        g['flash'] = lambda: self.monitor.get_flash_usage()
        g['sys'] = lambda: self.monitor.get_system_info()
        g['cpu'] = lambda: self.monitor.get_cpu_usage()
        g['tasks'] = lambda: self.monitor.get_task_list()
        
        print("[Worker] Global functions registered")
    
    def blink_led(self, times=1, delay_ms=200):
        """Blink LED for status indication"""
        for _ in range(times):
            self.led.value(1)
            time.sleep_ms(delay_ms)
            self.led.value(0)
            time.sleep_ms(delay_ms)
    
    def parse_message(self, msg):
        """
        Parse incoming message from master
        Format: COMMAND:PARAM1,PARAM2,...
        """
        try:
            msg_str = msg.decode('utf-8')
            parts = msg_str.split(':', 1)
            command = parts[0]
            params = parts[1] if len(parts) > 1 else ""
            
            return command, params
        except Exception as e:
            return None, f"ERROR:Parse_error_{e}"
    
    def handle_command(self, command, params):
        """Handle command from master"""
        try:
            # Task management commands
            if command == "DEFINE":
                # DEFINE:task_name:code
                parts = params.split(':', 1)
                if len(parts) == 2:
                    task_name, code = parts
                    result = self.task_executor.define_task(task_name, code)
                    return result
                return "ERROR:Invalid_DEFINE_format"
            
            elif command == "EXEC":
                # EXEC:task_name:CORE:N:args OR EXEC:task_name:args
                parts = params.split(':')
                task_name = parts[0]
                
                # Parse core selection and arguments
                core = None
                args = ()
                
                if len(parts) > 1:
                    if parts[1] == "CORE" and len(parts) > 2:
                        # Format: EXEC:task:CORE:N:args
                        core = int(parts[2])
                        if len(parts) > 3 and parts[3]:
                            args = eval(f"({parts[3]},)")
                    elif parts[1]:
                        # Format: EXEC:task:args
                        args = eval(f"({parts[1]},)")
                
                result = self.task_executor.execute_task(task_name, args, None, core)
                return result
            
            elif command == "LIST":
                # LIST - List all defined tasks
                return self.task_executor.list_tasks()
            
            elif command == "CANVAS":
                # CANVAS:TYPE:data - Canvas primitives (GROUP, CHAIN, CHORD)
                parts = params.split(':', 1)
                if len(parts) == 2:
                    import ujson as json
                    canvas_type, data_json = parts
                    try:
                        data = json.loads(data_json)
                        status, result = self.canvas.execute_primitive(canvas_type, data)
                        if status == "success":
                            result_json = json.dumps(result)
                            return f"OK:{result_json}"
                        else:
                            return f"ERROR:{result}"
                    except Exception as e:
                        return f"ERROR:Canvas_{canvas_type}_failed_{e}"
                return "ERROR:Invalid_CANVAS_format"
            
            elif command == "STATS":
                # STATS - Get execution statistics
                return self.task_executor.get_stats()
            
            # Peripheral commands
            elif command.startswith("GPIO") or command.startswith("PWM") or \
                 command.startswith("ADC") or command.startswith("DAC"):
                return self.peripherals.execute_command(f"{command}:{params}")
            
            elif command.startswith("I2C") or command.startswith("SPI") or \
                 command.startswith("UART") or command.startswith("CAN"):
                return self.peripherals.execute_command(f"{command}:{params}")
            
            # System monitoring commands
            elif command in ["SYS_INFO", "RAM_USAGE", "FLASH_USAGE", 
                           "CPU_USAGE", "TASK_LIST", "UPTIME"]:
                return self.monitor.execute_command(command)
            
            # File upload command
            elif command == "UPLOAD":
                # UPLOAD:filename:content
                parts = params.split(':', 1)
                if len(parts) == 2:
                    filename, content = parts
                    try:
                        with open(filename, 'w') as f:
                            f.write(content)
                        return f"OK:Uploaded_{filename}"
                    except Exception as e:
                        return f"ERROR:{e}"
                return "ERROR:Invalid_UPLOAD_format"
            
            # Reset command
            elif command == "RESET":
                import machine
                self.slip.send("OK:RESETTING")
                time.sleep_ms(100)
                machine.reset()
            
            # Ping/health check
            elif command == "PING":
                return "PONG"
            
            else:
                return f"ERROR:Unknown_command_{command}"
        
        except Exception as e:
            return f"ERROR:Handler_exception_{e}"
    
    def run(self):
        """Main event loop"""
        print("\n[Worker] Entering main loop...")
        
        while True:
            try:
                # Check for incoming SLIP packets
                packet = self.slip.receive()
                
                if packet:
                    # Blink LED on message received
                    self.led.value(1)
                    
                    # Parse and handle command
                    command, params = self.parse_message(packet)
                    
                    if command:
                        result = self.handle_command(command, params)
                        
                        # Send response
                        self.slip.send(result)
                    
                    self.led.value(0)
                
                # Small delay to prevent busy-waiting
                time.sleep_ms(10)
            
            except KeyboardInterrupt:
                print("\n[Worker] Shutdown requested")
                break
            
            except Exception as e:
                print(f"[Worker] Error in main loop: {e}")
                self.slip.send(f"ERROR:Main_loop_exception_{e}")
                time.sleep_ms(100)


# Entry point
def main():
    """Initialize and run worker node"""
    worker = WorkerNode()
    worker.run()


if __name__ == '__main__':
    main()
