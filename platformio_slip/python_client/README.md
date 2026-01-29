# Broccoli ESP32 Cluster Python Client

Control your ESP32 cluster from Python/Jupyter without reflashing firmware.

## Installation

```bash
pip install pyserial
```

## Quick Start

```python
from broccoli_cluster import BroccoliCluster

# Connect to master node
cluster = BroccoliCluster('COM23')  # Change to your port
cluster.connect()

# Define a task
cluster.define_task('add', 'x + y')

# Execute it
result = cluster.execute('add', 5, 3)
print(f"Result: {result}")  # Output: "8"

# Disconnect
cluster.disconnect()
```

## Using Context Manager

```python
with BroccoliCluster('COM23') as cluster:
    cluster.define_task('multiply', 'x * y')
    result = cluster.execute('multiply', 7, 6)
    print(f"7 * 6 = {result}")
```

## Available Methods

### `define_task(name, code)`
Define a new computational task.

```python
cluster.define_task('square', 'x * x')
cluster.define_task('average', '(x + y) / 2')
```

### `execute(task_name, *args, wait=True, timeout=5.0)`
Execute a task on the cluster.

```python
# Wait for result (default)
result = cluster.execute('add', 10, 20)

# Don't wait (fire and forget)
cluster.execute('compute_heavy', 100, wait=False)
```

### `list_tasks()`
List all defined tasks.

```python
tasks = cluster.list_tasks()
print(tasks)  # ['add', 'multiply', 'square']
```

### `stats()`
Show SLIP communication statistics.

```python
cluster.stats()
# Output:
# Worker 1: TX=512 bytes (4 pkts), RX=320 bytes (6 pkts)
```

## Serial Protocol

The master firmware accepts these commands over serial:

| Command | Format | Example |
|---------|--------|---------|
| DEFINE | `DEFINE:task_name:code` | `DEFINE:add:x+y` |
| EXEC | `EXEC:task_name:args` | `EXEC:add:5,3` |
| LIST | `LIST` | `LIST` |
| STATS | `STATS` | `STATS` |

Responses:

| Response | Format | Example |
|----------|--------|---------|
| Task defined | `OK:DEFINED:task_name` | `OK:DEFINED:add` |
| Task submitted | `OK:SUBMITTED:task_id` | `OK:SUBMITTED:1` |
| Task result | `RESULT:function:value` | `RESULT:add:8` |
| Error | `ERROR:message` | `ERROR:TASK_NOT_DEFINED` |

## Jupyter Notebook

See [notebooks/cluster_control.ipynb](../../notebooks/cluster_control.ipynb) for a complete example.

## Limitations

- Currently supports simple arithmetic expressions only
- Worker firmware needs to be updated to support new operations
- Single worker connection (can be extended to multiple workers)

## Extending Task Support

To add support for more complex operations (like trigonometry, string operations, etc.), modify the worker firmware in `src/main_worker.cpp` to handle additional function types.
