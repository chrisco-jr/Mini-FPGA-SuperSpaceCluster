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

### 9. RESET - Reset Workers (NOT IMPLEMENTED)

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
cluster.remove_task("add_complex") # Removes task from worker 0 by default
cluster.remove_task("add_complex", worker=1) # Removes task from worker 1
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

---
#### `stats()`

**Description**: Retrieve Master node network/packet stats 

**Returns**: Concise information of network/packet stats of the cluster

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

#### `reset_stats()`

**Description**: Resets network/packet stats recorded on Master back to 0


**Example**:
```python
cluster.reset_stats()
```

**Output**:
```
Pending...
```

---

#### `get_system_info(worker)`

**Description**: Retrieves system information from worker nodes

**Returns**: Printed report of kernel, cpu temp, cpu utilization, RAM utilization, and uptime

**Example**:
```python
sys_info = cluster.get_system_info(worker = 1)
print(sys_info)
```

**Output**:
```
Pending...
```
#### `broadcast_action(action_type, num_workers)`

**Description**: Uses existing SDK logic to perform cluster-wide operations. Currently supports 'clear' and 'telemetry' broadcast actions. 

**Returns**: List of responses from applied action_types from each node.

**Example**:
```python
reset_responses = cluster.broadcast_action("clear", num_workers)
print(reset_responses)
```

**Output**:
```
Pending...
```

### FPGA Reconfiguration

---
#### `reconfig(module, worker)` (TO BE IMPLEMENTED)

**Description**: Commands a worker to load a binary bitsream located in the firmware folder if it exists

**Returns**: Response from the worker node

**Example**:
```python
reconfig_response = cluster.reconfig('led_module.bin')
print(reconfig_response)
```

**Output**:
```
OK:FPGA_Reconfigured_led_module.bin
```

---

---

## Complete API Summary

### Serial Commands
| Command | Format | Description |
|---------|--------|-------------|
| DEFINE | `DEFINE:name:code` | Define task on Worker 0 |
| DEFINEW | `DEFINEW:worker_id:name:code` | Define task on specific worker |
| EXEC | `EXEC:name:args` | Execute on Worker 0; returns Task ID |
| EXECW | `EXECW:worker_id:name:args` | Execute on specific worker; returns Task ID |
| GET_RES | `GET_RES:task_id` | Retrieve result for a specific Task ID |
| LIST | `LIST` | List all tasks on Worker 0 |
| STATS | `STATS` | Show SLIP statistics for all workers |
| DELETE | `DELETE:name` | Remove a task from Worker 0 |
| DELETEW | `DELETEW:worker_id:name` | Remove task from a specific worker |
| CLEAR | `CLEAR` | Remove all tasks from Worker 0 |
| CLEARW | `CLEARW:worker_id` | Remove all tasks from a specific worker |
| UPLOAD | `UPLOAD:filename:base64` | Upload code file to worker filesystem |
| SYS_INFO | `SYS_INFO` | Get telemetry for Worker 0 |
| SYS_INFOW | `SYS_INFOW:worker_id` | Get telemetry for a specific worker |
| RESET_STATS | `RESET_STATS` | Reset network communication statistics |
| RESET | `RESET` | Hardware reset all workers (Not Implemented) |

### Python Methods
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `connect()` | - | None | Connect to master |
| `disconnect()` | - | None | Disconnect from cluster |
| `define_task()` | name, code, worker | None | Define task on specified worker |
| `execute()` | name, *args, worker | int | Execute task (Non-blocking); returns Task ID |
| `execute_and_wait()` | name, *args, worker, timeout | Any | Execute task (Blocking); returns Result |
| `get_result()` | task_id, wait, timeout | tuple | Retrieve results and poll count |
| `sig()` | task, *args, worker | Sig | Create signature for Canvas operations |
| `group()` | signatures | List | Parallel execution and result collection |
| `chain()` | signatures | Any | Sequential pipeline; passing results forward |
| `chord()` | header_sigs, callback_sig | Any | Parallel map followed by reduction callback |
| `list_tasks()` | worker | List[str] | List tasks on a specific worker |
| `stats()` | - | str | Print Master node network/packet stats |
| `reset_stats()` | - | None | Reset communication statistics on Master |
| `get_system_info()` | worker | str | Get worker health (CPU, Temp, RAM) |
| `upload_file()` | filename, code, worker | str | Transfer raw data to worker filesystem |
| `upload_python_as_task()` | name, code, worker | str | Upload .py file and register result function |
| `remove_task()` | name, worker | str | Purge task from RAM and disk |
| `clear_all_tasks()` | worker | str | Clear all registered tasks on a worker |
| `broadcast_action()` | action_type, num_workers | List | Perform cluster-wide operations |
| `reconfig()` | module, worker | str | Command FPGA reconfiguration (Beta) |

---

## Version History

### v3.0 (May 7, 2026)
- ✓ Port to PYNQ-Z2 with most key functions preserved
- ✓ Introduction of partial reconfiguration and sample firmware (currently via serial)
- ✓ Rework of repo for easier development and maintenance

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
