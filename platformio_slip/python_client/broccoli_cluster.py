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
from typing import Any, Optional, List, Tuple, Dict
from dataclasses import dataclass, field


@dataclass
class Sig:
    """Task signature for multi-worker Canvas primitives."""
    task: str
    args: Tuple[Any, ...] = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    worker: Optional[int] = None  # 0, 1, or None (auto)
    core: Optional[int] = None     # 0, 1, or None (auto)


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
    
    def define_task(self, name: str, code: str, worker: Optional[int] = None):
        """
        Define a new task on the cluster.
        
        Args:
            name: Task name (e.g., 'add', 'multiply')
            code: Python-like expression (e.g., 'x + y', 'x * y')
            worker: Which worker to define on (0, 1, or None for worker 0)
        
        Example:
            cluster.define_task('add', 'x + y')
            cluster.define_task('square', 'x * x', worker=1)
        """
        if worker is None:
            command = f"DEFINE:{name}:{code}"  # Legacy, defaults to worker 0
        else:
            command = f"DEFINEW:{worker}:{name}:{code}"
        
        response = self._send_command(command)
        
        if response.startswith('OK:DEFINED:'):
            worker_info = f" on Worker {worker}" if worker is not None else ""
            print(f">> Task '{name}' defined{worker_info}")
        else:
            print(f"✗ Failed to define task: {response}")
            raise RuntimeError(f"Task definition failed: {response}")
    
    def execute(self, task_name: str, *args, worker: Optional[int] = None, core: Optional[int] = None, wait: bool = True, timeout: float = 5.0) -> Optional[str]:
        """
        Execute a task on the cluster.
        
        Args:
            task_name: Name of the task to execute
            *args: Task arguments (will be joined with commas)
            worker: Which worker to run on (0, 1, or None for worker 0)
            core: Which core to run on (0 or 1). None = auto-assign
            wait: Whether to wait for result (default True)
            timeout: How long to wait for result in seconds
        
        Returns:
            Task result as string, or None if not waiting
        
        Example:
            result = cluster.execute('add', 5, 3)
            result = cluster.execute('add', 10, 20, worker=1, core=1)
        """
        # Format arguments as comma-separated string
        args_str = ','.join(str(arg) for arg in args) if args else ''
        
        # Build command based on worker and core selection
        if worker is not None:
            # Use worker-specific command
            if core is not None:
                command = f"EXECW:{worker}:{task_name}:CORE:{core}:{args_str}"
            else:
                command = f"EXECW:{worker}:{task_name}:{args_str}"
        else:
            # Legacy command (defaults to worker 0)
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
        worker_info = f" on Worker {worker}" if worker is not None else ""
        core_info = f" Core {core}" if core is not None else ""
        print(f">> Task submitted{worker_info}{core_info} (ID: {task_id})")
        
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
        # Convert HIGH/LOW to 1/0 and use task-based approach like ADC
        value = 1 if state.upper() == 'HIGH' else 0
        self.define_task('GPIO_WRITE', f'lambda pin, val: Pin(pin, Pin.OUT).value(val) or f"GPIO{{pin}}={{val}}"')
        return self.execute('GPIO_WRITE', pin, value, core=core)
    
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
        
        # Parse result: "OK:platform=ESP32-S3;freq=240MHz;cores=2"
        info = {}
        if result and 'OK:' in str(result):
            data = str(result).replace('OK:', '')
            for pair in data.split(';'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    info[key] = value
        return info
    
    def get_ram_usage(self):
        """
        Get real-time RAM usage.
        
        Returns:
            Dictionary with total, used, free, min_free (bytes) and usage (%)
        """
        self.define_task('RAM_USAGE', 'ram')
        result = self.execute('RAM_USAGE', wait=True)
        
        # Parse result: "OK:total=320000;used=45000;free=320000;usage=14.1%"
        info = {}
        if result and 'OK:' in str(result):
            data = str(result).replace('OK:', '')
            for pair in data.split(';'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    if key == 'usage':
                        info[key] = value  # Keep percentage as string
                    else:
                        try:
                            info[key] = int(value)
                        except ValueError:
                            info[key] = value
        return info
    
    def get_flash_usage(self):
        """
        Get flash memory (non-volatile storage) usage.
        
        Returns:
            Dictionary with total, sketch, free_sketch (bytes) and usage (%)
        """
        result = self._send_command('FLASH_USAGE', timeout=5.0)
        
        # Parse result: "OK:total=8388608;used=300000;free=8088608;usage=3.6%"
        info = {}
        if result and result.startswith('OK:'):
            data = result[3:]  # Remove "OK:" prefix
            for pair in data.split(';'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    if key == 'usage':
                        info[key] = value
                    else:
                        try:
                            info[key] = int(value)
                        except ValueError:
                            info[key] = value
        return info
    
    def get_cpu_usage(self):
        """
        Get CPU usage per core.
        
        Returns:
            Dictionary with core0, core1 usage percentages
        """
        self.define_task('CPU_USAGE', 'cpu')
        result = self.execute('CPU_USAGE', wait=True)
        
        # Parse result: "OK:core0=50%;core1=50%;note=estimated"
        info = {}
        if result and 'OK:' in str(result):
            data = str(result).replace('OK:', '')
            for pair in data.split(';'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
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
        
        # Parse result: "OK:threads=active;main=running"
        info = {'count': 0, 'tasks': []}
        if result and 'OK:' in str(result):
            data = str(result).replace('OK:', '')
            parts = data.split(';')
            info['count'] = len(parts) if parts and parts[0] else 0
            info['tasks'] = [f"{pair}" for pair in parts if pair] if parts else []
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
        print(f"  Platform: {sys_info.get('platform', 'Unknown')}")
        print(f"  Cores: {sys_info.get('cores', 'Unknown')}")
        print(f"  Frequency: {sys_info.get('freq', 'Unknown')}")
        print(f"  MicroPython: {sys_info.get('micropython', 'Unknown')}")
        
        # RAM Usage
        ram = self.get_ram_usage()
        print("\n[Memory (RAM)]")
        print(f"  Total:    {ram.get('total', 0):>10,} bytes")
        print(f"  Used:     {ram.get('used', 0):>10,} bytes")
        print(f"  Free:     {ram.get('free', 0):>10,} bytes")
        print(f"  Usage:    {ram.get('usage', '0%'):>10}")
        
        # Flash Usage
        flash = self.get_flash_usage()
        print("\n[Flash Memory (Non-Volatile)]")
        print(f"  Total:       {flash.get('total', 0):>10,} bytes")
        print(f"  Used:        {flash.get('used', 0):>10,} bytes")
        print(f"  Free:        {flash.get('free', 0):>10,} bytes")
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
    # CANVAS PRIMITIVES - Multi-Worker Support
    # ============================================================
    
    def sig(self, task: str, *args, worker: Optional[int] = None, core: Optional[int] = None, **kwargs) -> Sig:
        """Create a task signature for Canvas primitives."""
        return Sig(
            task=task,
            args=args,
            kwargs=kwargs,
            worker=worker,
            core=core
        )
    
    def group(self, signatures: List[Sig]) -> List[Any]:
        """
        Execute tasks in parallel across multiple workers and collect results.
        
        Args:
            signatures: List of Sig objects specifying tasks and target workers
        
        Returns:
            List of results in the same order as signatures
        
        Example:
            results = cluster.group([
                cluster.sig("square", 10, worker=0),
                cluster.sig("square", 20, worker=1)
            ])
            # Returns: [100, 400]
        """
        results = []
        for sig in signatures:
            result = self.execute(
                sig.task,
                *sig.args,
                worker=sig.worker,
                core=sig.core,
                wait=True,
                timeout=10.0
            )
            results.append(result)
        return results
    
    def chain(self, signatures: List[Sig]) -> Any:
        """
        Execute tasks sequentially, passing result to next task.
        Can distribute across workers as specified in signatures.
        
        Args:
            signatures: List of Sig objects specifying pipeline
        
        Returns:
            Final result after all tasks complete
        
        Example:
            result = cluster.chain([
                cluster.sig("square", 5, worker=0),   # 25
                cluster.sig("double", worker=1),       # 50
                cluster.sig("increment", worker=0)     # 51
            ])
        """
        if not signatures:
            return None
        
        # Execute first task
        result = self.execute(
            signatures[0].task,
            *signatures[0].args,
            worker=signatures[0].worker,
            core=signatures[0].core,
            wait=True,
            timeout=10.0
        )
        
        # Chain remaining tasks
        for sig in signatures[1:]:
            result = self.execute(
                sig.task,
                result,  # Pass previous result as first argument
                *sig.args,
                worker=sig.worker,
                core=sig.core,
                wait=True,
                timeout=10.0
            )
        
        return result
    
    def chord(self, header_sigs: List[Sig], callback_sig: Sig) -> Any:
        """
        Execute tasks in parallel (map), then reduce with callback.
        
        Args:
            header_sigs: List of Sig objects for parallel execution (map phase)
            callback_sig: Sig object for reduction (receives list of results)
        
        Returns:
            Result from callback task
        
        Example:
            # Map-reduce: square numbers across workers, then sum
            total = cluster.chord(
                [cluster.sig("square", i, worker=i%2) for i in range(10)],
                cluster.sig("sum_list", worker=0)
            )
        """
        # Execute header tasks in parallel
        header_results = self.group(header_sigs)
        
        # Execute callback with collected results
        # Note: We pass results as a single JSON-encoded list
        import json
        result = self.execute(
            callback_sig.task,
            json.dumps(header_results),  # Pass as JSON string
            *callback_sig.args,
            worker=callback_sig.worker,
            core=callback_sig.core,
            wait=True,
            timeout=10.0
        )
        
        return result
    
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
