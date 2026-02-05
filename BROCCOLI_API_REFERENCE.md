# Broccoli ESP32 Cluster - Complete API Reference

**Version**: 2.0 (Multi-Worker)  
**Date**: February 4, 2026  
**Hardware**: ESP32-S3 Master + 2x ESP32 Workers

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Serial Commands (Master)](#serial-commands-master)
3. [Python Client API](#python-client-api)
4. [Canvas Primitives](#canvas-primitives)
5. [GPIO Operations](#gpio-operations)
6. [System Monitoring](#system-monitoring)
7. [Peripheral Control](#peripheral-control)
8. [File Operations](#file-operations)
9. [Advanced Examples](#advanced-examples)

---

## Quick Start

### Hardware Setup
```
Master (COM8): ESP32-S3
├─ Worker 0: UART1 (GPIO17 TX, GPIO18 RX, GPIO4 Reset)
└─ Worker 1: UART2 (GPIO16 TX, GPIO15 RX, GPIO5 Reset)
```

### Basic Python Script
```python
from broccoli_cluster import BroccoliCluster

# Connect to cluster
cluster = BroccoliCluster('COM8')
cluster.connect()

# Define a task
cluster.define_task('add', 'lambda x, y: x + y')

# Execute it
result = cluster.execute('add', 5, 3)
print(f"Result: {result}")  # Output: Result: 8

# Disconnect
cluster.disconnect()
```

### Context Manager (Recommended)
```python
with BroccoliCluster('COM8') as cluster:
    cluster.define_task('square', 'lambda x: x * x')
    result = cluster.execute('square', 10)
    print(f"Result: {result}")
```

---

## Serial Commands (Master)

Commands sent directly to master via serial terminal or Python `_send_command()`.

### 1. DEFINE - Define Task (Worker 0)

**Format**: `DEFINE:<task_name>:<code>`

**Description**: Define a Python lambda task on Worker 0 (legacy, backwards compatible).

**Examples**:
```
DEFINE:add:lambda x, y: x + y
DEFINE:square:lambda x: x * x
DEFINE:multiply:lambda x, y: x * y
DEFINE:greet:lambda name: f"Hello, {name}!"
```

**Response**:
```
OK:DEFINED:add:WORKER0
OK:Task_add_defined
```

**Use Cases**:
- Simple mathematical operations
- String manipulation
- Data transformations
- Sensor data processing

---

### 2. DEFINEW - Define Task (Specific Worker)

**Format**: `DEFINEW:<worker_id>:<task_name>:<code>`

**Description**: Define a task on a specific worker (0 or 1).

**Examples**:
```
DEFINEW:0:add:lambda x, y: x + y
DEFINEW:1:multiply:lambda x, y: x * y
DEFINEW:0:process:lambda data: [x*2 for x in data]
DEFINEW:1:encode:lambda msg: msg.upper()
```

**Response**:
```
OK:DEFINED:add:WORKER0
OK:Task_add_defined
```

**Use Cases**:
- Load distribution across workers
- Worker-specific task libraries
- Parallel algorithm implementations

---

### 3. EXEC - Execute Task (Worker 0)

**Format**: `EXEC:<task_name>:<arg1>,<arg2>,...`

**Description**: Execute a task on Worker 0 with comma-separated arguments.

**Examples**:
```
EXEC:add:5,3
EXEC:square:10
EXEC:multiply:7,8
EXEC:greet:Alice
```

**Response**:
```
OK:SUBMITTED:1:WORKER0
RESULT:add:8
```

**Special Cases**:
```
EXEC:no_args:              # Task with no arguments
EXEC:single_arg:42         # Single argument
EXEC:string_arg:hello      # String argument
```

---

### 4. EXECW - Execute Task (Specific Worker)

**Format**: `EXECW:<worker_id>:<task_name>:<arg1>,<arg2>,...`

**Description**: Execute task on specific worker.

**Examples**:
```
EXECW:0:add:5,3
EXECW:1:multiply:10,20
EXECW:0:process:42
EXECW:1:encode:hello world
```

**Response**:
```
OK:SUBMITTED:2:WORKER1
RESULT:multiply:200
```

**Error Cases**:
```
EXECW:5:add:1,2              # ERROR:INVALID_WORKER_ID:5
EXECW:0:undefined:10         # ERROR:TASK_NOT_FOUND
EXECW:0:add:                 # OK (empty args)
```

---

### 5. EXEC with Core Selection

**Format**: `EXEC:<task_name>:CORE:<core_id>:<args>`  
**Format**: `EXECW:<worker_id>:<task_name>:CORE:<core_id>:<args>`

**Description**: Execute task on specific dual-core (0 or 1) within a worker.

**Examples**:
```
EXEC:heavy_calc:CORE:0:1000
EXEC:sensor_read:CORE:1:
EXECW:0:process_a:CORE:0:data1
EXECW:1:process_b:CORE:1:data2
```

**Response**:
```
OK:SUBMITTED:3:WORKER0:CORE0
RESULT:heavy_calc:42
```

**Use Cases**:
- Pin tasks to specific cores for performance
- Avoid interference between tasks
- Isolate time-critical operations

---

### 6. LIST - List Tasks

**Format**: `LIST`

**Description**: List all defined tasks on Worker 0.

**Example**:
```
LIST
```

**Response**:
```
OK:TASKS:
add
square
multiply
greet
END
```

---

### 7. STATS - SLIP Statistics

**Format**: `STATS`

**Description**: Show SLIP communication statistics for all workers.

**Example**:
```
STATS
```

**Response**:
```
--- SLIP Statistics ---
Worker 1: TX=533 bytes (30 pkts), RX=292 bytes (32 pkts)
Worker 2: TX=309 bytes (17 pkts), RX=167 bytes (17 pkts)
```

**Use Cases**:
- Monitor communication health
- Debug connection issues
- Verify worker activity

---

### 8. RESET - Reset Workers

**Format**: `RESET`

**Description**: Hardware reset both workers via GPIO pins.

**Example**:
```
RESET
```

**Response**:
```
OK:RESETTING_WORKERS
```

**Effect**:
- GPIO4 (Worker 0) and GPIO5 (Worker 1) pulsed LOW
- Workers reboot completely
- All defined tasks cleared
- SLIP connections re-established

---

### 9. SETUART - Switch UART (Legacy)

**Format**: `SETUART:<uart_num>`

**Description**: Switch active UART (legacy single-worker mode).

**Examples**:
```
SETUART:1    # Switch to UART1 (Worker 0)
SETUART:2    # Switch to UART2 (Worker 1)
```

**Response**:
```
OK:UART_SWITCHED:1
```

**Note**: For backwards compatibility. Use EXECW/DEFINEW for multi-worker.

---

### 10. UPLOAD - Upload Code File

**Format**: `UPLOAD:<filename>:<code>`

**Description**: Upload Python code file to worker filesystem.

**Example**:
```
UPLOAD:mymodule.py:def helper(x): return x * 2
```

**Response**:
```
OK:UPLOADED:mymodule.py
```

**Use Cases**:
- Deploy utility modules
- Upload configuration files
- Install custom libraries

---

## Python Client API

Complete reference for `BroccoliCluster` class.

### Connection Management

#### `__init__(port, baudrate=115200, timeout=2.0)`

**Description**: Initialize cluster client.

**Parameters**:
- `port` (str): Serial port (e.g., 'COM8', '/dev/ttyUSB0')
- `baudrate` (int): Baud rate (default 115200)
- `timeout` (float): Read timeout in seconds

**Example**:
```python
cluster = BroccoliCluster('COM8', baudrate=115200, timeout=5.0)
```

---

#### `connect()`

**Description**: Connect to ESP32 master node.

**Example**:
```python
cluster.connect()
```

**Output**:
```
>> Connected to ESP32 cluster on COM8
```

---

#### `disconnect()`

**Description**: Close serial connection.

**Example**:
```python
cluster.disconnect()
```

**Output**:
```
>> Disconnected from cluster
```

---

### Task Management

#### `define_task(name, code, worker=None)`

**Description**: Define a task on the cluster.

**Parameters**:
- `name` (str): Task name
- `code` (str): Python lambda expression or function
- `worker` (int, optional): Worker ID (0, 1, or None for Worker 0)

**Examples**:
```python
# Basic math
cluster.define_task('add', 'lambda x, y: x + y')
cluster.define_task('square', 'lambda x: x * x')

# On specific worker
cluster.define_task('process', 'lambda data: data * 2', worker=1)

# String operations
cluster.define_task('upper', 'lambda s: s.upper()')
cluster.define_task('reverse', 'lambda s: s[::-1]')

# List comprehension
cluster.define_task('double_list', 'lambda lst: [x*2 for x in lst]')

# Complex expression
cluster.define_task('fibonacci', 'lambda n: n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)')
```

---

#### `execute(task_name, *args, worker=None, core=None, wait=True, timeout=5.0)`

**Description**: Execute a task on the cluster.

**Parameters**:
- `task_name` (str): Name of task to execute
- `*args`: Task arguments (variable length)
- `worker` (int, optional): Target worker (0, 1, or None)
- `core` (int, optional): Target core (0, 1, or None)
- `wait` (bool): Wait for result (default True)
- `timeout` (float): Timeout in seconds

**Returns**: Task result as string, or None if not waiting.

**Examples**:
```python
# Basic execution
result = cluster.execute('add', 5, 3)
print(result)  # "8"

# Specific worker
result = cluster.execute('multiply', 10, 20, worker=1)

# Specific worker and core
result = cluster.execute('heavy_task', 1000, worker=0, core=1)

# Non-blocking
cluster.execute('long_task', 100, wait=False)

# Custom timeout
result = cluster.execute('slow_task', 50, timeout=10.0)
```

---

#### `list_tasks()`

**Description**: Get list of defined tasks.

**Returns**: List of task names.

**Example**:
```python
tasks = cluster.list_tasks()
print(tasks)  # ['add', 'square', 'multiply']
```

---

### Canvas Primitives

#### `sig(task, *args, worker=None, core=None, **kwargs)`

**Description**: Create a task signature for Canvas operations.

**Parameters**:
- `task` (str): Task name
- `*args`: Task arguments
- `worker` (int, optional): Target worker
- `core` (int, optional): Target core
- `**kwargs`: Keyword arguments (reserved)

**Returns**: `Sig` object

**Examples**:
```python
# Simple signature
s1 = cluster.sig('add', 5, 3)

# With worker
s2 = cluster.sig('square', 10, worker=0)

# With worker and core
s3 = cluster.sig('process', 100, worker=1, core=0)

# Multiple signatures
sigs = [
    cluster.sig('square', i, worker=i % 2)
    for i in range(10)
]
```

---

#### `group(signatures)`

**Description**: Execute tasks in parallel and collect results.

**Parameters**:
- `signatures` (List[Sig]): List of task signatures

**Returns**: List of results in same order.

**Examples**:
```python
# Parallel execution on both workers
results = cluster.group([
    cluster.sig('square', 10, worker=0),
    cluster.sig('square', 20, worker=1)
])
print(results)  # ['100', '400']

# Distribute computation
results = cluster.group([
    cluster.sig('process', i, worker=i % 2)
    for i in range(10)
])

# Mixed tasks
results = cluster.group([
    cluster.sig('add', 5, 3, worker=0),
    cluster.sig('multiply', 10, 20, worker=1),
    cluster.sig('square', 7, worker=0)
])
```

---

#### `chain(signatures)`

**Description**: Execute tasks sequentially, passing result to next.

**Parameters**:
- `signatures` (List[Sig]): List of task signatures (pipeline)

**Returns**: Final result after all tasks.

**Examples**:
```python
# Simple pipeline
result = cluster.chain([
    cluster.sig('square', 5, worker=0),      # 25
    cluster.sig('double', worker=1),          # 50
    cluster.sig('increment', worker=0)        # 51
])
print(result)  # "51"

# Data transformation pipeline
result = cluster.chain([
    cluster.sig('parse', raw_data),
    cluster.sig('normalize'),
    cluster.sig('filter'),
    cluster.sig('aggregate')
])

# Cross-worker processing
result = cluster.chain([
    cluster.sig('encode', message, worker=0),
    cluster.sig('encrypt', worker=1),
    cluster.sig('compress', worker=0)
])
```

---

#### `chord(header_sigs, callback_sig)`

**Description**: Execute tasks in parallel (map), then callback with results (reduce).

**Parameters**:
- `header_sigs` (List[Sig]): Parallel tasks (map phase)
- `callback_sig` (Sig): Reduction task (receives results)

**Returns**: Result from callback task.

**Examples**:
```python
# Map-reduce pattern
results = cluster.group([
    cluster.sig('square', i, worker=i % 2)
    for i in range(10)
])
total = sum(int(x) for x in results)

# Distributed aggregation
partial_sums = cluster.group([
    cluster.sig('sum_range', start, end, worker=i % 2)
    for i, (start, end) in enumerate(ranges)
])
final_sum = sum(int(x) for x in partial_sums)
```

---

### GPIO Operations

#### `gpio_write(pin, state, core=None)`

**Description**: Write to GPIO pin.

**Parameters**:
- `pin` (int): GPIO pin number
- `state` (str): 'HIGH' or 'LOW'
- `core` (int, optional): Target core

**Examples**:
```python
# Turn on LED
cluster.gpio_write(2, 'HIGH')

# Turn off LED
cluster.gpio_write(2, 'LOW')

# On specific core
cluster.gpio_write(13, 'HIGH', core=1)
```

---

#### `gpio_read(pin, core=None)`

**Description**: Read from GPIO pin.

**Parameters**:
- `pin` (int): GPIO pin number
- `core` (int, optional): Target core

**Returns**: Pin state ('0' or '1')

**Examples**:
```python
# Read button state
state = cluster.gpio_read(14)
if state == '1':
    print("Button pressed")

# Read sensor
value = cluster.gpio_read(25, core=0)
```

---

#### `pwm(pin, channel, freq, resolution, duty, core=None)`

**Description**: Set PWM output.

**Parameters**:
- `pin` (int): GPIO pin number
- `channel` (int): PWM channel (0-15)
- `freq` (int): Frequency in Hz
- `resolution` (int): Resolution in bits (1-16)
- `duty` (int): Duty cycle (0 to 2^resolution - 1)
- `core` (int, optional): Target core

**Examples**:
```python
# 50% duty cycle at 1kHz, 8-bit resolution
cluster.pwm(pin=5, channel=0, freq=1000, resolution=8, duty=127)

# Servo control (50Hz, 16-bit)
cluster.pwm(pin=18, channel=1, freq=50, resolution=16, duty=3276)

# LED brightness control
for brightness in range(0, 256, 16):
    cluster.pwm(pin=2, channel=0, freq=5000, resolution=8, duty=brightness)
    time.sleep(0.1)
```

---

#### `adc_read(pin, core=None)`

**Description**: Read analog value from ADC pin.

**Parameters**:
- `pin` (int): ADC pin number (32-39 on ESP32)
- `core` (int, optional): Target core

**Returns**: ADC value (0-4095 for 12-bit ADC)

**Examples**:
```python
# Read potentiometer
value = cluster.adc_read(34)
print(f"ADC: {value}")

# Read multiple sensors
sensor1 = cluster.adc_read(36, core=0)
sensor2 = cluster.adc_read(39, core=1)

# Average multiple readings
readings = [int(cluster.adc_read(34)) for _ in range(10)]
average = sum(readings) / len(readings)
```

---

### System Monitoring

#### `get_system_info()`

**Description**: Get system information.

**Returns**: Dictionary with platform, cores, freq, micropython version.

**Example**:
```python
info = cluster.get_system_info()
print(f"Platform: {info['platform']}")
print(f"Cores: {info['cores']}")
print(f"Frequency: {info['freq']}")
```

**Output**:
```
Platform: ESP32-S3
Cores: 2
Frequency: 240MHz
```

---

#### `get_ram_usage()`

**Description**: Get real-time RAM usage.

**Returns**: Dictionary with total, used, free, usage.

**Example**:
```python
ram = cluster.get_ram_usage()
print(f"RAM Usage: {ram['usage']}")
print(f"Free: {ram['free']:,} bytes")
```

**Output**:
```
RAM Usage: 14.1%
Free: 320,000 bytes
```

---

#### `get_flash_usage()`

**Description**: Get flash memory usage.

**Returns**: Dictionary with total, used, free, usage.

**Example**:
```python
flash = cluster.get_flash_usage()
print(f"Flash: {flash['usage']}")
```

---

#### `get_cpu_usage()`

**Description**: Get CPU usage per core.

**Returns**: Dictionary with core0, core1 usage.

**Example**:
```python
cpu = cluster.get_cpu_usage()
print(f"Core 0: {cpu['core0']}")
print(f"Core 1: {cpu['core1']}")
```

---

#### `get_task_list()`

**Description**: Get FreeRTOS task list.

**Returns**: Dictionary with count and tasks list.

**Example**:
```python
tasks = cluster.get_task_list()
print(f"Running {tasks['count']} tasks")
for task in tasks['tasks']:
    print(f"  {task}")
```

---

#### `print_system_status()`

**Description**: Print formatted system status report.

**Example**:
```python
cluster.print_system_status()
```

**Output**:
```
============================================================
ESP32 SYSTEM STATUS
============================================================

[System Information]
  Platform: ESP32-S3
  Cores: 2
  Frequency: 240MHz
  MicroPython: v1.22.2

[Memory (RAM)]
  Total:        327,680 bytes
  Used:          45,000 bytes
  Free:         282,680 bytes
  Usage:           13.7%

[Flash Memory (Non-Volatile)]
  Total:      8,388,608 bytes
  Used:         300,000 bytes
  Free:       8,088,608 bytes
  Usage:            3.6%

[CPU Usage]
  Core 0:   45.2%
  Core 1:   32.8%

[FreeRTOS Tasks] (5 tasks)
  main=running
  mp_task=running
  ...
============================================================
```

---

#### `stats()`

**Description**: Print SLIP statistics.

**Example**:
```python
cluster.stats()
```

**Output**:
```
--- SLIP Statistics ---
Worker 1: TX=533 bytes (30 pkts), RX=292 bytes (32 pkts)
Worker 2: TX=309 bytes (17 pkts), RX=167 bytes (17 pkts)
```

---

### Peripheral Control

#### `i2c_init(sda, scl, freq=100000, core=None)`

**Description**: Initialize I2C bus.

**Parameters**:
- `sda` (int): SDA pin number
- `scl` (int): SCL pin number
- `freq` (int): I2C frequency in Hz (default 100kHz)
- `core` (int, optional): Target core

**Example**:
```python
# Standard I2C at 100kHz
cluster.i2c_init(sda=21, scl=22, freq=100000)

# Fast mode at 400kHz
cluster.i2c_init(sda=21, scl=22, freq=400000)
```

---

#### `spi_init(sck, miso, mosi, ss, freq=1000000, core=None)`

**Description**: Initialize SPI bus.

**Parameters**:
- `sck` (int): SCK pin number
- `miso` (int): MISO pin number
- `mosi` (int): MOSI pin number
- `ss` (int): SS pin number
- `freq` (int): SPI frequency in Hz (default 1MHz)
- `core` (int, optional): Target core

**Example**:
```python
# Standard SPI
cluster.spi_init(sck=18, miso=19, mosi=23, ss=5, freq=1000000)

# High-speed SPI
cluster.spi_init(sck=18, miso=19, mosi=23, ss=5, freq=10000000)
```

---

#### `uart_init(tx, rx, baud=115200, core=None)`

**Description**: Initialize UART.

**Parameters**:
- `tx` (int): TX pin number
- `rx` (int): RX pin number
- `baud` (int): Baud rate (default 115200)
- `core` (int, optional): Target core

**Example**:
```python
# GPS module at 9600 baud
cluster.uart_init(tx=17, rx=16, baud=9600)

# High-speed UART
cluster.uart_init(tx=17, rx=16, baud=921600)
```

---

#### `can_init(tx, rx, baudrate=500000, core=None)`

**Description**: Initialize CAN bus.

**Parameters**:
- `tx` (int): TX pin number
- `rx` (int): RX pin number
- `baudrate` (int): CAN baudrate (125000, 250000, 500000, 1000000)
- `core` (int, optional): Target core

**Example**:
```python
# Standard CAN at 500kbps
cluster.can_init(tx=5, rx=4, baudrate=500000)

# High-speed CAN at 1Mbps
cluster.can_init(tx=5, rx=4, baudrate=1000000)
```

---

### File Operations

#### `upload_code(filename, code)`

**Description**: Upload Python code file to worker.

**Parameters**:
- `filename` (str): Target filename
- `code` (str): Python code content

**Example**:
```python
# Upload utility module
code = """
def helper(x):
    return x * 2

def process(data):
    return [helper(x) for x in data]
"""
cluster.upload_code('utils.py', code)

# Upload configuration
config = "THRESHOLD = 100\nMAX_RETRIES = 3"
cluster.upload_code('config.py', config)
```

---

## Advanced Examples

### Example 1: Parallel Data Processing

```python
with BroccoliCluster('COM8') as cluster:
    # Define tasks on both workers
    cluster.define_task('process', 'lambda x: x * x + 1', worker=0)
    cluster.define_task('process', 'lambda x: x * x + 1', worker=1)
    
    # Generate data
    data = range(100)
    
    # Parallel processing
    results = cluster.group([
        cluster.sig('process', val, worker=i % 2)
        for i, val in enumerate(data)
    ])
    
    # Aggregate
    total = sum(int(x) for x in results)
    print(f"Total: {total}")
```

---

### Example 2: Sensor Data Pipeline

```python
with BroccoliCluster('COM8') as cluster:
    # Define pipeline stages
    cluster.define_task('read_sensor', 'lambda pin: adc_read(pin)', worker=0)
    cluster.define_task('normalize', 'lambda x: x / 4095.0', worker=1)
    cluster.define_task('smooth', 'lambda x: x * 0.8 + prev * 0.2', worker=0)
    cluster.define_task('threshold', 'lambda x: 1 if x > 0.5 else 0', worker=1)
    
    # Execute pipeline
    result = cluster.chain([
        cluster.sig('read_sensor', 34, worker=0),
        cluster.sig('normalize', worker=1),
        cluster.sig('smooth', worker=0),
        cluster.sig('threshold', worker=1)
    ])
    
    print(f"Threshold result: {result}")
```

---

### Example 3: LED Control with PWM

```python
with BroccoliCluster('COM8') as cluster:
    # Fade LED in and out
    pin = 2
    channel = 0
    freq = 5000
    resolution = 8  # 8-bit (0-255)
    
    # Fade in
    for duty in range(0, 256, 5):
        cluster.pwm(pin, channel, freq, resolution, duty)
        time.sleep(0.02)
    
    # Fade out
    for duty in range(255, -1, -5):
        cluster.pwm(pin, channel, freq, resolution, duty)
        time.sleep(0.02)
```

---

### Example 4: Multi-Sensor Monitoring

```python
with BroccoliCluster('COM8') as cluster:
    # Define sensor reading tasks
    cluster.define_task('read_temp', 'lambda: adc_read(34)', worker=0)
    cluster.define_task('read_light', 'lambda: adc_read(35)', worker=0)
    cluster.define_task('read_pressure', 'lambda: adc_read(36)', worker=1)
    cluster.define_task('read_humidity', 'lambda: adc_read(39)', worker=1)
    
    # Read all sensors in parallel
    while True:
        readings = cluster.group([
            cluster.sig('read_temp', worker=0),
            cluster.sig('read_light', worker=0),
            cluster.sig('read_pressure', worker=1),
            cluster.sig('read_humidity', worker=1)
        ])
        
        temp, light, pressure, humidity = readings
        print(f"T={temp} L={light} P={pressure} H={humidity}")
        time.sleep(1.0)
```

---

### Example 5: Image Processing Pipeline

```python
with BroccoliCluster('COM8') as cluster:
    # Define image processing stages
    cluster.define_task('grayscale', 'lambda img: convert_grayscale(img)', worker=0)
    cluster.define_task('blur', 'lambda img: gaussian_blur(img, 5)', worker=1)
    cluster.define_task('edge_detect', 'lambda img: sobel_filter(img)', worker=0)
    cluster.define_task('threshold', 'lambda img: binary_threshold(img, 128)', worker=1)
    
    # Process image through pipeline
    result = cluster.chain([
        cluster.sig('grayscale', worker=0),
        cluster.sig('blur', worker=1),
        cluster.sig('edge_detect', worker=0),
        cluster.sig('threshold', worker=1)
    ])
    
    print(f"Processed image: {result}")
```

---

### Example 6: Distributed Monte Carlo Simulation

```python
import random

with BroccoliCluster('COM8') as cluster:
    # Define Monte Carlo iteration
    code = '''
lambda n: sum(1 for _ in range(n) 
              if random.random()**2 + random.random()**2 <= 1)
'''
    cluster.define_task('monte_carlo', code, worker=0)
    cluster.define_task('monte_carlo', code, worker=1)
    
    # Run parallel iterations
    iterations_per_worker = 100000
    results = cluster.group([
        cluster.sig('monte_carlo', iterations_per_worker, worker=0),
        cluster.sig('monte_carlo', iterations_per_worker, worker=1)
    ])
    
    # Estimate Pi
    total_inside = sum(int(x) for x in results)
    total_points = iterations_per_worker * 2
    pi_estimate = 4 * total_inside / total_points
    print(f"Pi estimate: {pi_estimate}")
```

---

### Example 7: Real-Time Control System

```python
with BroccoliCluster('COM8') as cluster:
    # PID controller on Worker 0
    cluster.define_task('pid_compute', '''
lambda setpoint, measured, kp, ki, kd: 
    kp * (setpoint - measured) + ki * integral + kd * derivative
''', worker=0)
    
    # Motor control on Worker 1
    cluster.define_task('set_motor', 'lambda pwm_value: motor_set(pwm_value)', worker=1)
    
    # Control loop
    setpoint = 100
    while True:
        # Read sensor
        measured = int(cluster.execute('read_sensor', 34, worker=0))
        
        # Compute control signal
        control = cluster.execute('pid_compute', setpoint, measured, 
                                 1.0, 0.1, 0.01, worker=0)
        
        # Apply control
        cluster.execute('set_motor', control, worker=1)
        
        time.sleep(0.01)  # 100Hz control loop
```

---

### Example 8: Network Packet Processing

```python
with BroccoliCluster('COM8') as cluster:
    # Define packet processing stages
    cluster.define_task('parse_header', 'lambda pkt: extract_header(pkt)', worker=0)
    cluster.define_task('validate', 'lambda hdr: check_checksum(hdr)', worker=1)
    cluster.define_task('decrypt', 'lambda data: aes_decrypt(data)', worker=0)
    cluster.define_task('decompress', 'lambda data: zlib_decompress(data)', worker=1)
    
    # Process packet queue
    packets = get_packet_queue()
    
    results = cluster.group([
        cluster.chain([
            cluster.sig('parse_header', worker=0),
            cluster.sig('validate', worker=1),
            cluster.sig('decrypt', worker=0),
            cluster.sig('decompress', worker=1)
        ])
        for pkt in packets
    ])
```

---

### Example 9: System Diagnostics

```python
with BroccoliCluster('COM8') as cluster:
    print("=" * 60)
    print("CLUSTER DIAGNOSTICS")
    print("=" * 60)
    
    # Test both workers
    cluster.define_task('test', 'lambda x: x * 2', worker=0)
    cluster.define_task('test', 'lambda x: x * 2', worker=1)
    
    # Execute test
    results = cluster.group([
        cluster.sig('test', 21, worker=0),
        cluster.sig('test', 21, worker=1)
    ])
    
    print(f"\nWorker 0 test: {results[0]} {'✓ PASS' if results[0] == '42' else '✗ FAIL'}")
    print(f"Worker 1 test: {results[1]} {'✓ PASS' if results[1] == '42' else '✗ FAIL'}")
    
    # Check SLIP stats
    print("\n")
    cluster.stats()
    
    # System info
    print("\n")
    cluster.print_system_status()
```

---

### Example 10: Task Decorator Pattern

```python
from broccoli_cluster import BroccoliCluster, Task

# Set default cluster
cluster = BroccoliCluster('COM8')
cluster.connect()
Task.set_cluster(cluster)

# Define tasks with decorators
@Task
def add(x, y):
    return x + y

@Task
def square(x):
    return x * x

# Execute remotely
result1 = add.remote(5, 3)      # Executes on cluster
result2 = square.remote(10)     # Executes on cluster

# Or execute locally (for testing)
result3 = add(5, 3)             # Executes locally
result4 = square(10)            # Executes locally

print(f"Remote: {result1}, {result2}")
print(f"Local: {result3}, {result4}")

cluster.disconnect()
```

---

## Error Handling

### Common Errors

#### Connection Errors
```python
try:
    cluster = BroccoliCluster('COM8')
    cluster.connect()
except serial.SerialException as e:
    print(f"Failed to connect: {e}")
    # Check if port exists, cable connected, etc.
```

#### Task Execution Errors
```python
try:
    result = cluster.execute('undefined_task', 10)
except RuntimeError as e:
    print(f"Execution failed: {e}")
    # Task not defined, check with list_tasks()
```

#### Timeout Errors
```python
# Increase timeout for slow tasks
result = cluster.execute('slow_task', 1000, timeout=30.0)

# Or disable wait
cluster.execute('background_task', 100, wait=False)
```

#### Worker Unavailable
```python
# Check STATS to verify worker communication
cluster.stats()

# Reset workers if needed
cluster._send_command('RESET')
time.sleep(2.0)
```

---

## Performance Tips

### 1. Use Parallel Execution
```python
# ✗ Slow: Sequential
for i in range(10):
    result = cluster.execute('process', i, worker=0)

# ✓ Fast: Parallel
results = cluster.group([
    cluster.sig('process', i, worker=i % 2)
    for i in range(10)
])
```

### 2. Minimize Data Transfer
```python
# ✗ Bad: Send large data back and forth
data = range(10000)
for x in data:
    cluster.execute('process', x)

# ✓ Good: Upload code, process on worker
code = "lambda: [process(x) for x in range(10000)]"
cluster.define_task('batch_process', code)
result = cluster.execute('batch_process')
```

### 3. Use Core Pinning
```python
# Pin time-critical tasks to specific cores
cluster.execute('sensor_read', 34, worker=0, core=0)
cluster.execute('control_loop', 100, worker=0, core=1)
```

### 4. Batch Operations
```python
# Define multiple tasks at once
tasks = {
    'add': 'lambda x, y: x + y',
    'multiply': 'lambda x, y: x * y',
    'square': 'lambda x: x * x'
}

for name, code in tasks.items():
    cluster.define_task(name, code)
```

---

## Troubleshooting

### Worker Not Responding
```bash
# Check serial connection
cluster.stats()

# Reset workers
cluster._send_command('RESET')
time.sleep(2.0)

# Re-upload worker code if needed
```

### Task Returns Wrong Result
```python
# List defined tasks
tasks = cluster.list_tasks()
print(f"Defined tasks: {tasks}")

# Redefine task
cluster.define_task('task_name', 'corrected_code')
```

### Slow Execution
```python
# Check SLIP stats for errors
cluster.stats()

# Monitor system resources
cluster.print_system_status()

# Reduce timeout for faster failure detection
result = cluster.execute('task', 10, timeout=1.0)
```

### Import Errors on Worker
```python
# Upload required modules
with open('mymodule.py') as f:
    code = f.read()
cluster.upload_code('mymodule.py', code)

# Then import in task
cluster.define_task('use_module', 'lambda: import_and_use()')
```

---

## Complete API Summary

### Serial Commands
| Command | Format | Description |
|---------|--------|-------------|
| DEFINE | `DEFINE:name:code` | Define task on Worker 0 |
| DEFINEW | `DEFINEW:worker:name:code` | Define task on specific worker |
| EXEC | `EXEC:name:args` | Execute on Worker 0 |
| EXECW | `EXECW:worker:name:args` | Execute on specific worker |
| LIST | `LIST` | List all tasks |
| STATS | `STATS` | Show SLIP statistics |
| RESET | `RESET` | Reset all workers |
| SETUART | `SETUART:uart_num` | Switch UART (legacy) |
| UPLOAD | `UPLOAD:file:code` | Upload code file |

### Python Methods
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `connect()` | - | None | Connect to master |
| `disconnect()` | - | None | Disconnect |
| `define_task()` | name, code, worker | None | Define task |
| `execute()` | name, *args, worker, core, wait, timeout | str | Execute task |
| `sig()` | task, *args, worker, core | Sig | Create signature |
| `group()` | signatures | List | Parallel execution |
| `chain()` | signatures | Any | Sequential pipeline |
| `chord()` | headers, callback | Any | Map-reduce |
| `list_tasks()` | - | List[str] | List tasks |
| `stats()` | - | None | Print SLIP stats |
| `gpio_write()` | pin, state, core | str | Write GPIO |
| `gpio_read()` | pin, core | str | Read GPIO |
| `pwm()` | pin, channel, freq, res, duty, core | str | Set PWM |
| `adc_read()` | pin, core | str | Read ADC |
| `get_system_info()` | - | Dict | System info |
| `get_ram_usage()` | - | Dict | RAM usage |
| `get_flash_usage()` | - | Dict | Flash usage |
| `get_cpu_usage()` | - | Dict | CPU usage |
| `get_task_list()` | - | Dict | FreeRTOS tasks |
| `print_system_status()` | - | None | Print diagnostics |
| `i2c_init()` | sda, scl, freq, core | str | Init I2C |
| `spi_init()` | sck, miso, mosi, ss, freq, core | str | Init SPI |
| `uart_init()` | tx, rx, baud, core | str | Init UART |
| `can_init()` | tx, rx, baudrate, core | str | Init CAN |
| `upload_code()` | filename, code | str | Upload file |

---

## Version History

### v2.0 (Feb 4, 2026)
- ✓ Multi-worker support (2 workers)
- ✓ Worker-specific commands (EXECW, DEFINEW)
- ✓ Canvas primitives (group, chain, chord)
- ✓ Sig class for signatures
- ✓ Parallel execution across workers
- ✓ Comprehensive API reference

### v1.0 (Earlier)
- ✓ Single worker support
- ✓ Basic task definition and execution
- ✓ GPIO operations
- ✓ System monitoring
- ✓ Peripheral control

---

## License & Credits

**License**: MIT  
**Authors**: Broccoli Development Team  
**Hardware**: ESP32-S3 Master + ESP32 Workers  
**Firmware**: PlatformIO + Arduino Framework  
**Workers**: MicroPython v1.22.2

For more information, see:
- [MULTI_WORKER_IMPLEMENTATION.md](MULTI_WORKER_IMPLEMENTATION.md)
- [README.md](README.md)

---

**End of API Reference**
