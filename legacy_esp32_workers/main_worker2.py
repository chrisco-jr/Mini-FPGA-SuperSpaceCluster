# Main Worker 2 Program for MicroPython ESP32
# Modified for UART2 connection to master
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

# Configuration for Worker 2 (connects to Master UART2)
MASTER_UART_ID = 1
MASTER_TX_PIN = 18  # Worker TX=18 connects to Master UART2 RX=15 (crossover)
MASTER_RX_PIN = 17  # Worker RX=17 connects to Master UART2 TX=16 (crossover)
SLIP_BAUDRATE = 921600

# LED for status indication
LED_PIN = 2


class WorkerNode:
    """Main worker node that handles all functionality"""
    
    def __init__(self):
        print("\n" + "="*50)
        print("ESP32 MicroPython Worker Node 2")
        print("Connecting to Master UART2")
        print("="*50)
        
        # Status LED
        self.led = Pin(LED_PIN, Pin.OUT)
        self.led.on()  # LED on during init
        
        # Initialize SLIP interface
        print("\nInitializing SLIP interface...")
        print(f"  UART ID: {MASTER_UART_ID}")
        print(f"  TX Pin: {MASTER_TX_PIN} (to Master RX15)")
        print(f"  RX Pin: {MASTER_RX_PIN} (from Master TX16)")
        print(f"  Baudrate: {SLIP_BAUDRATE}")
        
        self.slip = SLIPInterface(
            uart_id=MASTER_UART_ID,
            tx_pin=MASTER_TX_PIN,
            rx_pin=MASTER_RX_PIN,
            baudrate=SLIP_BAUDRATE
        )
        
        # Initialize peripheral controller
        print("\nInitializing peripheral controller...")
        self.peripherals = PeripheralController()
        
        # Initialize system monitor
        print("Initializing system monitor...")
        self.monitor = SystemMonitor()
        
        # Initialize dual-core executor
        print("Initializing dual-core executor...")
        self.dual_core = DualCoreExecutor()
        
        # Initialize task executor
        print("Initializing task executor...")
        self.task_executor = TaskExecutor()
        
        # Create canvas API
        print("Initializing canvas API...")
        self.canvas_api = create_canvas_api(self.task_executor)
        
        print("\n" + "="*50)
        print("Worker Node 2 Ready!")
        print("Waiting for commands from Master...")
        print("="*50 + "\n")
        
        self.led.off()  # LED off when ready
    
    def handle_command(self, cmd_type, payload):
        """Process commands from master"""
        try:
            # PING - Health check
            if cmd_type == "PING":
                return "PONG"
            
            # STATS - System statistics
            elif cmd_type == "STATS":
                stats = self.monitor.get_stats()
                return str(stats)
            
            # DEFINE - Define a new task
            elif cmd_type == "DEFINE":
                parts = payload.split(':', 1)
                if len(parts) != 2:
                    return "ERROR:Invalid DEFINE format"
                task_name, task_code = parts
                self.task_executor.define_task(task_name.strip(), task_code.strip())
                return f"OK:Task {task_name} defined"
            
            # EXEC - Execute a task
            elif cmd_type == "EXEC":
                parts = payload.split(':', 1)
                if len(parts) < 1:
                    return "ERROR:Invalid EXEC format"
                
                task_name = parts[0].strip()
                args = parts[1] if len(parts) > 1 else ""
                
                # Parse arguments
                if args:
                    import json
                    try:
                        args_list = json.loads(args)
                    except:
                        args_list = [args]
                else:
                    args_list = []
                
                # Check for core assignment
                core = None
                if args_list and isinstance(args_list[-1], dict) and 'core' in args_list[-1]:
                    core_info = args_list.pop()
                    core = core_info['core']
                
                # Execute task
                if core is not None:
                    result = self.dual_core.execute_on_core(
                        lambda: self.task_executor.execute_task(task_name, *args_list),
                        core
                    )
                else:
                    result = self.task_executor.execute_task(task_name, *args_list)
                
                return str(result)
            
            # LIST - List all defined tasks
            elif cmd_type == "LIST":
                tasks = self.task_executor.list_tasks()
                return str(tasks)
            
            # UPLOAD - Upload code to file
            elif cmd_type == "UPLOAD":
                parts = payload.split(':', 1)
                if len(parts) != 2:
                    return "ERROR:Invalid UPLOAD format"
                filename, code = parts
                try:
                    with open(filename.strip(), 'w') as f:
                        f.write(code)
                    return f"OK:File {filename} uploaded"
                except Exception as e:
                    return f"ERROR:{str(e)}"
            
            # Canvas commands
            elif cmd_type == "GROUP":
                return self.canvas_api.handle_group(payload)
            
            elif cmd_type == "CHAIN":
                return self.canvas_api.handle_chain(payload)
            
            elif cmd_type == "CHORD":
                return self.canvas_api.handle_chord(payload)
            
            # Peripheral commands
            elif cmd_type.startswith("I2C_"):
                return self.peripherals.handle_i2c_command(cmd_type, payload)
            
            elif cmd_type.startswith("SPI_"):
                return self.peripherals.handle_spi_command(cmd_type, payload)
            
            elif cmd_type.startswith("UART_"):
                return self.peripherals.handle_uart_command(cmd_type, payload)
            
            elif cmd_type.startswith("CAN_"):
                return self.peripherals.handle_can_command(cmd_type, payload)
            
            elif cmd_type.startswith("GPIO_"):
                return self.peripherals.handle_gpio_command(cmd_type, payload)
            
            elif cmd_type.startswith("ADC_"):
                return self.peripherals.handle_adc_command(cmd_type, payload)
            
            else:
                return f"ERROR:Unknown command {cmd_type}"
                
        except Exception as e:
            import sys
            sys.print_exception(e)
            return f"ERROR:{str(e)}"
    
    def run(self):
        """Main event loop"""
        print("Worker 2 entering main loop...")
        
        while True:
            try:
                # Check for incoming SLIP packets
                packet = self.slip.receive_packet()
                
                if packet:
                    # Blink LED on packet receive
                    self.led.on()
                    
                    # Parse command
                    packet_str = packet.decode('utf-8', 'ignore')
                    
                    # Split into command and payload
                    if ':' in packet_str:
                        cmd_type, payload = packet_str.split(':', 1)
                    else:
                        cmd_type = packet_str
                        payload = ""
                    
                    # Handle command
                    response = self.handle_command(cmd_type, payload)
                    
                    # Send response
                    self.slip.send_packet(response.encode('utf-8'))
                    
                    self.led.off()
                
                # Small delay to prevent busy-waiting
                time.sleep_ms(1)
                
            except KeyboardInterrupt:
                print("\nWorker 2 shutting down...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                import sys
                sys.print_exception(e)
                time.sleep_ms(100)


# Main entry point
def main():
    worker = WorkerNode()
    worker.run()


if __name__ == "__main__":
    main()
