"""
Broccoli ESP32 Cluster Client
Connect to ESP32 master via serial and submit tasks dynamically.
Usage:
    from broccoli_cluster import BroccoliCluster
    cluster = BroccoliCluster('COM23')
    cluster.define_task('add', 'x + y')
    result = cluster.execute('add', 5, 3)
"""

import serial
import time
import re
from typing import Any, Optional, List


class BroccoliCluster:
    """Client for controlling ESP32 cluster via serial."""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        """
        Initialize connection to ESP32 master.
        
        Args:
            port: Serial port (e.g., 'COM23' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Serial baud rate (default 115200)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self._result_buffer = []
        
    def connect(self):
        """Connect to the ESP32 master node."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(0.5)  # Wait for connection to stabilize
            
            # Clear any existing data
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            self.connected = True
            print(f">> Connected to ESP32 cluster on {self.port}")
            
            # Read welcome message
            time.sleep(0.5)
            while self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('==='):
                    print(f"  {line}")
                    
        except serial.SerialException as e:
            print(f"✗ Failed to connect: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from the ESP32 master."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            print(">> Disconnected from cluster")
    
    def _send_command(self, command: str, timeout: float = None) -> str:
        """Send a command and return the response."""
        if not self.connected:
            raise RuntimeError("Not connected to cluster. Call connect() first.")
        
        if timeout is None:
            timeout = self.timeout
        
        # Clear input buffer
        self.ser.reset_input_buffer()
        
        # Send command
        self.ser.write(f"{command}\n".encode('utf-8'))
        self.ser.flush()
        
        # Read response
        time.sleep(0.1)
        response_lines = []
        
        timeout_start = time.time()
        while time.time() - timeout_start < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # Filter out debug lines
                    if not line.startswith('[DEBUG]'):
                        response_lines.append(line)
                    
                    # Check for completion markers (excluding debug lines)
                    if not line.startswith('[DEBUG]') and (line.startswith('OK:') or line.startswith('ERROR:') or line == 'END'):
                        break
            else:
                time.sleep(0.01)
        
        return '\n'.join(response_lines)
    
    def define_task(self, name: str, code: str):
        """
        Define a new task on the cluster.
        
        Args:
            name: Task name (e.g., 'add', 'multiply')
            code: Python-like expression (e.g., 'x + y', 'x * y')
        
        Example:
            cluster.define_task('add', 'x + y')
            cluster.define_task('square', 'x * x')
        """
        command = f"DEFINE:{name}:{code}"
        response = self._send_command(command)
        
        if response.startswith('OK:DEFINED:'):
            print(f">> Task '{name}' defined")
        else:
            print(f"✗ Failed to define task: {response}")
            raise RuntimeError(f"Task definition failed: {response}")
    
    def execute(self, task_name: str, *args, core: Optional[int] = None, wait: bool = True, timeout: float = 5.0) -> Optional[str]:
        """
        Execute a task on the cluster.
        
        Args:
            task_name: Name of the task to execute
            *args: Task arguments (will be joined with commas)
            core: Which core to run on (0 or 1). None = auto-assign
            wait: Whether to wait for result (default True)
            timeout: How long to wait for result in seconds
        
        Returns:
            Task result as string, or None if not waiting
        
        Example:
            result = cluster.execute('add', 5, 3)
            result = cluster.execute('add', 10, 20, core=1)  # Run on Core 1
        """
        # Format arguments as comma-separated string
        args_str = ','.join(str(arg) for arg in args)
        
        # Add core selection if specified (use separate colons for proper parsing)
        if core is not None:
            command = f"EXEC:{task_name}:CORE:{core}:{args_str}" if args_str else f"EXEC:{task_name}:CORE:{core}"
        else:
            command = f"EXEC:{task_name}:{args_str}"
        
        response = self._send_command(command)
        
        if not response.startswith('OK:SUBMITTED:'):
            print(f"✗ Failed to submit task: {response}")
            raise RuntimeError(f"Task execution failed: {response}")
        
        # Extract task ID
        task_id = response.split(':')[2]
        core_info = f" on Core {core}" if core is not None else ""
        print(f">> Task submitted{core_info} (ID: {task_id})")
        
        if not wait:
            return None
        
        # Wait for result
        print(f"  Waiting for result...", end='', flush=True)
        result = self._wait_for_result(task_name, timeout)
        
        if result:
            print(f" OK")
            return result
        else:
            print(f" ✗ Timeout")
            return None
    
    def _wait_for_result(self, task_name: str, timeout: float) -> Optional[str]:
        """Wait for a result from the cluster."""
        timeout_start = time.time()
        
        while time.time() - timeout_start < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Look for RESULT:function:value
                if line.startswith('RESULT:'):
                    parts = line.split(':', 2)
                    if len(parts) >= 3 and parts[1] == task_name:
                        return parts[2]
            
            time.sleep(0.01)
        
        return None
    
    def _read_response(self, timeout: float = 5.0) -> Optional[str]:
        """Read a single line response from the serial port."""
        timeout_start = time.time()
        
        while time.time() - timeout_start < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:  # Return first non-empty line
                    return line
            
            time.sleep(0.01)
        
        return None
    
    def list_tasks(self) -> List[str]:
        """
        List all defined tasks.
        
        Returns:
            List of task names
        """
        # Clear buffer first
        self.ser.reset_input_buffer()
        
        # Send LIST command
        self.ser.write(b"LIST\n")
        self.ser.flush()
        time.sleep(0.2)
        
        # Read multi-line response
        tasks = []
        in_list = False
        timeout_start = time.time()
        
        while time.time() - timeout_start < 2.0:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line == 'OK:TASKS:':
                    in_list = True
                elif line == 'END':
                    break
                elif in_list and line.strip():
                    tasks.append(line.strip())
            else:
                time.sleep(0.01)
        
        return tasks
    
    def stats(self):
        """Print SLIP statistics."""
        response = self._send_command("STATS")
        print("\n" + response)
    
    # ============== GPIO Control Methods ==============
    
    def gpio_mode(self, pin: int, mode: str, core: Optional[int] = None):
        """
        Set GPIO pin mode.
        
        Args:
            pin: GPIO pin number
            mode: 'INPUT', 'OUTPUT', 'INPUT_PULLUP', or 'INPUT_PULLDOWN'
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('GPIO_MODE', mode)
        return self.execute('GPIO_MODE', pin, mode, core=core)
    
    def gpio_write(self, pin: int, state: str, core: Optional[int] = None):
        """
        Write to GPIO pin.
        
        Args:
            pin: GPIO pin number
            state: 'HIGH' or 'LOW'
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('GPIO_WRITE', state)
        return self.execute('GPIO_WRITE', pin, state, core=core)
    
    def gpio_read(self, pin: int, core: Optional[int] = None):
        """
        Read from GPIO pin.
        
        Args:
            pin: GPIO pin number
            core: Which core to run on (0 or 1, optional)
        
        Returns:
            Pin state (0 or 1)
        """
        self.define_task('GPIO_READ', 'pin')
        return self.execute('GPIO_READ', pin, core=core)
    
    def pwm(self, pin: int, channel: int, freq: int, resolution: int, duty: int, core: Optional[int] = None):
        """
        Set PWM output.
        
        Args:
            pin: GPIO pin number
            channel: PWM channel (0-15)
            freq: Frequency in Hz
            resolution: Resolution in bits (1-16)
            duty: Duty cycle (0 - 2^resolution-1)
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('PWM', 'pwm_control')
        return self.execute('PWM', pin, channel, freq, resolution, duty, core=core)
    
    def adc_read(self, pin: int, core: Optional[int] = None):
        """
        Read analog value from ADC pin.
        
        Args:
            pin: ADC pin number
            core: Which core to run on (0 or 1, optional)
        
        Returns:
            ADC value (0-4095 for 12-bit)
        """
        self.define_task('ADC_READ', 'adc')
        return self.execute('ADC_READ', pin, core=core)
    
    # ============== Peripheral Init Methods ==============
    
    def i2c_init(self, sda: int, scl: int, freq: int = 100000, core: Optional[int] = None):
        """
        Initialize I2C bus.
        
        Args:
            sda: SDA pin number
            scl: SCL pin number
            freq: I2C frequency in Hz (default 100kHz)
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('I2C_INIT', 'i2c_init')
        return self.execute('I2C_INIT', sda, scl, freq, core=core)
    
    def spi_init(self, sck: int, miso: int, mosi: int, ss: int, freq: int = 1000000, core: Optional[int] = None):
        """
        Initialize SPI bus.
        
        Args:
            sck: SCK pin number
            miso: MISO pin number
            mosi: MOSI pin number
            ss: SS pin number
            freq: SPI frequency in Hz (default 1MHz)
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('SPI_INIT', 'spi_init')
        return self.execute('SPI_INIT', sck, miso, mosi, ss, freq, core=core)
    
    def uart_init(self, tx: int, rx: int, baud: int = 115200, core: Optional[int] = None):
        """
        Initialize UART.
        
        Args:
            tx: TX pin number
            rx: RX pin number
            baud: Baud rate (default 115200)
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('UART_INIT', 'uart_init')
        return self.execute('UART_INIT', tx, rx, baud, core=core)
    
    def can_init(self, tx: int, rx: int, baudrate: int = 500000, core: Optional[int] = None):
        """
        Initialize CAN bus.
        
        Args:
            tx: TX pin number
            rx: RX pin number
            baudrate: CAN baudrate (125000, 250000, 500000, 1000000)
            core: Which core to run on (0 or 1, optional)
        """
        self.define_task('CAN_INIT', 'can_init')
        return self.execute('CAN_INIT', tx, rx, baudrate, core=core)
    
    # ============== System Monitoring Methods ==============
    
    def get_system_info(self):
        """
        Get system information (chip model, cores, frequency, SDK version).
        
        Returns:
            Dictionary with system info
        """
        self.define_task('SYS_INFO', 'sys')
        result = self.execute('SYS_INFO', wait=True)
        
        # Parse result: "CHIP:ESP32-S3;CORES:2;FREQ:240MHz;SDK:v4.4"
        info = {}
        if result:
            for pair in result.split(';'):
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    info[key.lower()] = value
        return info
    
    def get_ram_usage(self):
        """
        Get real-time RAM usage.
        
        Returns:
            Dictionary with total, used, free, min_free (bytes) and usage (%)
        """
        self.define_task('RAM_USAGE', 'ram')
        result = self.execute('RAM_USAGE', wait=True)
        
        # Parse result: "TOTAL:320000;USED:45000;FREE:275000;MIN_FREE:250000;USAGE:14.1%"
        info = {}
        if result:
            for pair in result.split(';'):
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    key = key.lower()
                    if key == 'usage':
                        info[key] = value  # Keep percentage as string
                    else:
                        info[key] = int(value)
        return info
    
    def get_flash_usage(self):
        """
        Get flash memory (non-volatile storage) usage.
        
        Returns:
            Dictionary with total, sketch, free_sketch (bytes) and usage (%)
        """
        self.define_task('FLASH_USAGE', 'flash')
        result = self.execute('FLASH_USAGE', wait=True)
        
        # Parse result: "TOTAL:8388608;SKETCH:300000;FREE_SKETCH:2000000;USAGE:3.6%"
        info = {}
        if result:
            for pair in result.split(';'):
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    key = key.lower()
                    if key == 'usage':
                        info[key] = value
                    else:
                        info[key] = int(value)
        return info
    
    def get_cpu_usage(self):
        """
        Get CPU usage per core.
        
        Returns:
            Dictionary with core0, core1 usage percentages
        """
        self.define_task('CPU_USAGE', 'cpu')
        result = self.execute('CPU_USAGE', wait=True)
        
        # Parse result: "CORE0:45.2%;CORE1:23.1%;TOTAL_TIME:1234567"
        info = {}
        if result:
            for pair in result.split(';'):
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    key = key.lower()
                    info[key] = value
        return info
    
    def get_task_list(self):
        """
        Get list of all FreeRTOS tasks running on the worker.
        
        Returns:
            Dictionary with task count and list of tasks
        """
        self.define_task('TASK_LIST', 'tasks')
        result = self.execute('TASK_LIST', wait=True)
        
        # Parse result: "TASKS:5;TaskName1(Core0,Prio1,Stack100);TaskName2(Core1,Prio2,Stack200);..."
        info = {'count': 0, 'tasks': []}
        if result:
            parts = result.split(';')
            if parts[0].startswith('TASKS:'):
                info['count'] = int(parts[0].split(':')[1])
            
            for i in range(1, len(parts)):
                if '(' in parts[i]:
                    info['tasks'].append(parts[i])
        
        return info
    
    def print_system_status(self):
        """
        Print a formatted system status report (like Task Manager).
        """
        print("\n" + "="*60)
        print("ESP32 SYSTEM STATUS")
        print("="*60)
        
        # System Info
        sys_info = self.get_system_info()
        print("\n[System Information]")
        print(f"  Chip: {sys_info.get('chip', 'Unknown')}")
        print(f"  Cores: {sys_info.get('cores', 'Unknown')}")
        print(f"  Frequency: {sys_info.get('freq', 'Unknown')}")
        print(f"  SDK: {sys_info.get('sdk', 'Unknown')}")
        
        # RAM Usage
        ram = self.get_ram_usage()
        print("\n[Memory (RAM)]")
        print(f"  Total:    {ram.get('total', 0):>10,} bytes")
        print(f"  Used:     {ram.get('used', 0):>10,} bytes")
        print(f"  Free:     {ram.get('free', 0):>10,} bytes")
        print(f"  Min Free: {ram.get('min_free', 0):>10,} bytes")
        print(f"  Usage:    {ram.get('usage', '0%'):>10}")
        
        # Flash Usage
        flash = self.get_flash_usage()
        print("\n[Flash Memory (Non-Volatile)]")
        print(f"  Total:       {flash.get('total', 0):>10,} bytes")
        print(f"  Sketch Size: {flash.get('sketch', 0):>10,} bytes")
        print(f"  Free Sketch: {flash.get('free_sketch', 0):>10,} bytes")
        print(f"  Usage:       {flash.get('usage', '0%'):>10}")
        
        # CPU Usage
        cpu = self.get_cpu_usage()
        print("\n[CPU Usage]")
        print(f"  Core 0: {cpu.get('core0', '0%'):>6}")
        print(f"  Core 1: {cpu.get('core1', '0%'):>6}")
        
        # Task List
        tasks = self.get_task_list()
        print(f"\n[FreeRTOS Tasks] ({tasks['count']} tasks)")
        for task in tasks.get('tasks', []):
            print(f"  {task}")
        
        print("="*60)
    
    # ============================================================
    # CANVAS PRIMITIVES
    # ============================================================
    
    def sig(self, task, *args, core=None, **kwargs):
        """Create a task signature for Canvas primitives."""
        return {
            "task": task,
            "args": args,
            "kwargs": kwargs,
            "core": core
        }
    
    def group(self, signatures):
        """Execute tasks in parallel and collect results."""
        import json
        data = []
        for sig in signatures:
            data.append({
                "task": sig["task"],
                "args": sig.get("args", []),
                "kwargs": sig.get("kwargs", {}),
                "core": sig.get("core")
            })
        
        cmd = f"CANVAS:GROUP:{json.dumps(data)}"
        response = self._send_command(cmd, timeout=30.0)  # Canvas needs longer timeout
        
        if response and response.startswith("OK:"):
            try:
                return json.loads(response[3:])
            except:
                return response[3:]
        return None
    
    def chain(self, signatures):
        """Execute tasks sequentially, passing result to next."""
        import json
        data = []
        for sig in signatures:
            data.append({
                "task": sig["task"],
                "args": sig.get("args", []),
                "kwargs": sig.get("kwargs", {}),
                "core": sig.get("core")
            })
        
        cmd = f"CANVAS:CHAIN:{json.dumps(data)}"
        print(f"[DEBUG] Sending CHAIN command: {cmd}")
        response = self._send_command(cmd, timeout=30.0)  # Canvas needs longer timeout
        print(f"[DEBUG] Received response: {response}")
        
        if response and response.startswith("OK:"):
            try:
                return json.loads(response[3:])
            except:
                return response[3:]
        return None
    
    def chord(self, header_sigs, callback_sig):
        """Execute tasks in parallel, then callback with results."""
        import json
        header = []
        for sig in header_sigs:
            header.append({
                "task": sig["task"],
                "args": sig.get("args", []),
                "kwargs": sig.get("kwargs", {}),
                "core": sig.get("core")
            })
        
        data = {
            "header": header,
            "callback": {
                "task": callback_sig["task"],
                "args": callback_sig.get("args", []),
                "kwargs": callback_sig.get("kwargs", {}),
                "core": callback_sig.get("core")
            }
        }
        
        cmd = f"CANVAS:CHORD:{json.dumps(data)}"
        response = self._send_command(cmd, timeout=30.0)  # Canvas needs longer timeout
        
        if response and response.startswith("OK:"):
            try:
                return json.loads(response[3:])
            except:
                return response[3:]
        return None
    
    # ============================================================
    # FILE UPLOAD
    # ============================================================
    
    def upload_code(self, filename, code):
        """Upload Python code file to worker via SLIP."""
        # Encode file upload command
        cmd = f"UPLOAD:{filename}:{code}"
        self._send_command(cmd)
        response = self._read_response()
        return response
    
    def list_tasks(self):
        """List all defined tasks on the worker."""
        self._send_command("LIST")
        response = self._read_response()
        
        if response and response.startswith("OK:"):
            tasks_str = response[3:]
            if tasks_str:
                return tasks_str.split(",")
        return []
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Decorator for defining tasks (syntactic sugar)
class Task:
    """
    Decorator for defining cluster tasks.
    
    Example:
        @Task
        def add(x, y):
            return x + y
        
        # Later, execute with:
        result = add.remote(5, 3)
    """
    
    _cluster = None
    
    @classmethod
    def set_cluster(cls, cluster: BroccoliCluster):
        """Set the default cluster for all Task decorators."""
        cls._cluster = cluster
    
    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        
        # Try to extract simple expression from function
        import inspect
        source = inspect.getsource(func)
        
        # Look for return statement
        match = re.search(r'return\s+(.+)', source)
        if match:
            expression = match.group(1).strip()
            
            # Define task on cluster if available
            if Task._cluster:
                Task._cluster.define_task(self.name, expression)
    
    def remote(self, *args, **kwargs):
        """Execute task on cluster."""
        if not Task._cluster:
            raise RuntimeError("No cluster set. Call Task.set_cluster(cluster) first.")
        
        return Task._cluster.execute(self.name, *args, **kwargs)
    
    def __call__(self, *args, **kwargs):
        """Execute task locally (for testing)."""
        return self.func(*args, **kwargs)
