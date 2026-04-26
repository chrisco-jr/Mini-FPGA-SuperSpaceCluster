# Broccoli PYNQ-Z2 Cluster - Complete API Reference

**Version**: 1.0 (Multi-Worker)  
**Date**: April 24, 2026  
**Hardware**: PYNQ-Z2 Master + 2x PYNQ-Z2 Workers

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
Master (<target_ip>): PYNQ Z2
├─ Worker 0: UART0 on /dev/ttyPS1 (AR0 TX, AR1 RX)
└─ Worker 1: UART1 on /dev/ttyPS2 (AR2 TX, AR3 RX)
```

### Basic Python Script
```python
from broccoli_cluster import BroccoliCluster

# Connect to cluster
cluster = BroccoliCluster('<target_ip>')
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
with BroccoliCluster('C<target_ip>') as cluster:
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
[W0 RECV] OK:Task_add_defined
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
[W0 RECV] OK:Task_add_defined
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
[W0 RECV] OK:SUBMITTED:1
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
[W0 RECV] OK:SUBMITTED:1
```

**Error Cases**:
```
EXECW:5:add:1,2              # ERROR:INVALID_WORKER_ID:5
EXECW:0:undefined:10         # ERROR:TASK_NOT_FOUND
EXECW:0:add:                 # OK (empty args)
```

---

### 5. EXEC with Core Selection (Accepted but ignored, task scheduling handled by onboard OS at the moment)

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
[W0 RECV] OK:SUBMITTED:2
```

**Use Cases**:
- Pin tasks to specific cores for performance
- Avoid interference between tasks
- Isolate time-critical operations

---

### 6. GET_RES

**Format**: `GET_RES:<task_id>`  

**Description**: Retrieves the result of an executed task by calling on the task's task ID.

**Examples**:
```
GET_RES:1
GET_RES:2
```

**Response**:
```
[W0 RECV] OK:RESULT:8
```

**Use Cases**:
- Retreive the results of executed tasks
- Allows longer/more intensive tasks to be queried for results periodically and allow other tasks to run without blocking main bus
- Isolate time-critical operations
---




### 7. LIST - List Tasks

**Format**: `LIST`

**Description**: List all defined tasks on Worker 0.

**Example**:
```
LIST
```

**Response**:
```
[W0 RECV] OK:add,sub
```

**Use Cases**:
- See currently available tasks to run
---

---

### 8. STATS - SLIP Statistics

**Format**: `STATS`

**Description**: Show SLIP communication statistics for all workers.

**Example**:
```
STATS
```

**Response**:
```

ID   | STATUS       | TX     | RX     | LATENCY
------------------------------------------------
0    | ONLINE       | 10     | 10     | 15.5ms
1    | UNRESPONSIVE | 1      | 0      | ---
----------------------------------------

```

**Use Cases**:
- Monitor communication health
- Debug connection issues
- Verify worker activity

---

### 9. RESET - Reset Workers (NEEDS DEBUGGING)

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

### 10. DELETE / DELETEW

**Format**: `DELETE:<task_name>` or `DELETEW:<worker_id>:<task_name>`

**Description**: Removes a current task in the list.

**Examples**:
```
DELETE:mult
DELETEW:1:add
```

**Response**:
```
[W0 RECV] OK:Task_mult_deleted
[W1 RECV] OK:Task_add_deleted
```

**Use Cases**:
- Selective deletion of tasks for memory / resource management
- Remove no longer needed tasks


### 11. CLEAR / CLEARW 

**Format**: `CLEAR` or `CLEARW:<worker_id>`

**Description**: Removes all current tasks in task list

**Examples**:
```
CLEAR
CLEARW:1
```

**Response**:
```
[W0 RECV] OK:Cleared_2_tasks
[W1 RECV] OK:Cleared_1_tasks
```
**Use Cases**:
- Fast way to clear task resources
- Bring unit back to a known state

---

### 12. UPLOAD - Upload Code File (Advanced, requires text to already be encoded in base 64 formatting)

**Format**: `UPLOAD:<filename>:<base64_encoded_text>`

**Description**: Upload file to worker filesystem.

**Example**:
```
UPLOAD:led_all_on.py:aW1wb3J0IG1tYXAsIG9zOyBmPW9zLm9wZW4oIi9kZXYvbWVtIiwgb3MuT19SRFdSfG9zLk9fU1lOQyk7IG09bW1hcC5tbWFwKGYsIDQwOTYsIG1tYXAuTUFQX1NIQVJFRCwgbW1hcC5QUk9UX1JFQUR8bW1hcC5QUk9UX1dSSVRFLCBvZmZzZXQ9MHg0MTIwMDAwMCk7IG1bNDo4XT1iJ1x4MDBceDAwXHgwMFx4MDAnOyBtWzA6NF09YidceDBmXHgwMFx4MDBceDAwJzsgbS5mbHVzaCgpOyBtLmNsb3NlKCk7IG9zLmNsb3NlKGYp 

```

**Response**:
```
[W0 RECV] OK:Uploaded_led_all_on.py
```

**Use Cases**:
- Deploy utility modules
- Upload configuration files
- Install custom libraries


### 13. SYS_INFO / SYS_INFOW 

**Format**: `SYS_INFO` or `SYS_INFOW:<worker_id>`

**Description**: See internal health telemetry of nodes

**Examples**:
```
SYS_INFO
SYS_INFO:1
```

**Response**:
```
[W0 RECV] OK:[6.12.10-xilinx-g0a0f70e531c7] TEMP:38.9C | CPU:0.0% | RAM:27.6/496.5MB | UP:0d 1h 2m 2s
[W1 RECV] OK:[6.12.10-xilinx-g0a0f70e531c7] TEMP:39.5C | CPU:9.5% | RAM:28.9/496.5MB | UP:0d 0h 19m 52s
```
**Use Cases**:
- Monitor unit health and resource usage
- Isolate issues to problem nodes

### 14. RESET_STATS

**Format**: `RESET_STATS`

**Description**: Reset the communication statistics for the network

**Examples**:
```
RESET_STATS
```

**Response**:
```
[W0 RECV] OK:[6.12.10-xilinx-g0a0f70e531c7] TEMP:38.9C | CPU:0.0% | RAM:27.6/496.5MB | UP:0d 1h 2m 2s
[W1 RECV] OK:[6.12.10-xilinx-g0a0f70e531c7] TEMP:39.5C | CPU:9.5% | RAM:28.9/496.5MB | UP:0d 0h 19m 52s
```
**Use Cases**:
- Monitor unit health and resource usage
- Isolate issues to problem nodes

---


## Python Client API

Complete reference for `BroccoliCluster` class.

### Connection Management

#### `__init__(target, mode, port, timeout)`

**Description**: Initialize cluster client.

**Parameters**:
- `target` (str): Master Node IP Address (e.g., '192.168.0.100')
- `mode` (str): Mode of master node operation, either 'network' or 'serial' (default 'network'). It is recommended to use network for all API connections
- `port` (int): Port number of IP (default 5000)
- `timeout` (float): Read timeout in seconds (default 5.0)

**Example**:
```python
cluster = BroccoliCluster(target=192.168.0.100, mode='network', port=5000, timeout=5.0)
```

---

#### `connect()`

**Description**: Connects to PYNQ Z2 master node

**Example**:
```python
cluster.connect()
```

**Output**:
```
>> Connected to Broccoli Master (network) at 192.168.1.100
```

---

#### `disconnect()` (not implemented, but honestly a good idea to reimplement)

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

#### `execute(task_name, *args, worker=None)`

**Description**: Execute a task on the cluster.

**Parameters**:
- `task_name` (str): Name of task to execute
- `*args`: Task arguments (variable length)
- `worker` (int, optional): Target worker (0, 1, or None)

**Returns**: Task ID as int (Non-Blocking Operation)

**Examples**:
```python
# Basic execution
taskID = cluster.execute('add', 5, 3)
print(taskID)  # "1"

# Specific worker
taskID = cluster.execute('multiply', 10, 20, worker=1)

```

#### `execute_and_wait(task_name, *args, worker=None, timeout)`

**Description**: Execute a task on the cluster.

**Parameters**:
- `task_name` (str): Name of task to execute
- `*args`: Task arguments (variable length)
- `worker` (int, optional): Target worker (0, 1, or None)
- `timeout` (float, optional): Length of timeout (default 15.0)

**Returns**: Result of executed task name (Blocking Operation)

**Examples**:
```python
# Basic execution
cluster.define_task("id_test", "lambda: 'W0_UNIQUE'")
res0 = cluster.execute_and_wait("id_test", worker=0)
print(res0)  # "W0_UNIQUE"

# Specific worker
cluster.define_task("id_test", "lambda: 'W1_UNIQUE'", worker=1)
res0 = cluster.execute_and_wait("id_test", worker=0)
print(res1)  # "W1_UNIQUE"
```

#### `get_result(task_id, wait, timeout)`

**Description**: Retrieves the results from an executed task with periodic polling

**Parameters**:
- `task_id` (str): ID of task to retrieve results from
- `wait` (bool): Whether to wait for task or not (UNUSED) (default True)
- `timeout` (float, optional): Length of timeout (default 15.0)

**Returns**: A tuple containing the results affiliated with task ID, and the number of polls 

**Example**:
```python
cluster.get_result(tid, wait=True, timeout=2.0)
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


### Orchestration & Canvas Primitives

---

### Canvas Primitives

#### `sig(task, *args, worker=None)`

**Description**: Create a task signature for Canvas operations.

**Parameters**:
- `task` (str): Task name
- `*args`: Task arguments
- `worker` (int, optional): Target worker

**Returns**: `Sig` object

**Examples**:
```python
# Simple signature
s1 = cluster.sig('add', 5, 3)

# With worker
s2 = cluster.sig('square', 10, worker=0)

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

**Returns**: Final result after all tasks. Unpacks values into separate positional arguments when passed directly to next task (eg., if a previous task returned (A,B), next task receives A,B, as separate positional arguments.

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


### Advanced File & Task Management

#### `upload_file(filename, code, worker)`

**Description**: Transfers raw data to Petalinux OS on PYNQ-Z2.

**Parameters**:
- `file_name` (str): Name of file to upload
- `code` (str): Information to be uploaded
- `worker` (int, optional): Target worker (0, 1, or None)

**Examples**:
```python
cluster.upload("test.txt", "Hello World")
cluster.upload("test2.py", "def result(a, b):\n    return a + b", worker=1)
```

#### `upload_python_as_task(task_name, code, worker)`

**Description**: Uploads .py file and registers its 'result' function as a task. SUitable for larger python scripts.

**Parameters**:
- `task_name` (str): Name of task to execute
- `code` (str): Information to be uploaded
- `worker` (int, optional): Target worker (0, 1, or None)

**Examples**:
```python
heavy_logic = """
def result(pixel_buffer, width, height, kernel_type="blur"):
    import math
    if len(pixel_buffer) != (width * height): return {"err": "mismatch"}
    normalized = [round(p / 255.0, 4) for p in pixel_buffer]
    kernels = {"blur": [1/9]*9, "edge": [-1]*4 + [8] + [-1]*4}
    k = kernels.get(kernel_type, kernels["blur"])
    output = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            sum_val = 0
            for ky in range(3):
                for kx in range(3):
                    pixel = normalized[(y + ky - 1) * width + (x + kx - 1)]
                    sum_val += pixel * k[ky * 3 + kx]
            output.append(sum_val)
    return {"status": "SUCCESS", "avg": sum(normalized)/len(normalized)}
"""
cluster.upload_python_as_task("edge_vision", heavy_logic, worker=0)

```
#### `remove_task(name, worker)`

**Description**: Purges task from RAM and deletes associated .py file from disk

**Parameters**:
- `name` (str): Name of task to be removed
- `worker` (int, optional): Target worker (0, 1, or None)


**Examples**:
```python
cluster.upload("test.txt", "Hello World")
cluster.upload("test2.py", "def result(a, b):\n    return a + b", worker=1)
```

#### `list_tasks(worker)`

**Description**: Returns list of registered tasks on a specific worker

**Parameters**:
- `worker` (int, optional): Target worker (0, 1, or None)

**Returns**: List of tasks on task list of a worker

**Examples**:
```python
tasks = cluster.list_tasks()
print(tasks)
w1_tasks = cluster.list_tasks(worker=1)
print (w1_tasks)
```

#### `clear_all_tasks(worker)`

**Description**: Clears all registered tasks on a specific worker

**Parameters**:
- `worker` (int, optional): Target worker (0, 1, or None)

**Examples**:
```python
cluster.clear_all_tasks()
cluster.clear_all_tasks(worker=1)

```

### Utility & Telemetry

#### `stats()`

**Description**: Retrieve Master node network/packet stats 

**Returns**: Concise informatino of network/packet stats of the cluster

**Example**:
```python
stats = cluster.stats()
print(f"[OK] Network Stats: {stats}")
```

**Output**:
```
OK:STATS|W0:ONLINE:329:329:21.3ms|W1:ONLINE:806:806:19.8ms
```

---

Updated up to here

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
