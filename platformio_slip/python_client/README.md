# Broccoli / Mini-ESP SuperSpaceCluster — Python Client

This folder is the **PC-side control plane**. It talks to the ESP32-S3 master over USB serial and lets you:
- define tasks dynamically
- execute tasks (optionally selecting core 0/1)
- run Celery-like Canvas primitives (GROUP/CHAIN/CHORD)
- run a comprehensive integration test suite against real hardware

If you want the big-picture architecture and project status, start here:
- `../../README.md`

---

## What this project is (so far)

Think: “Celery, but the workers are ESP32s”.

You send commands from the PC to a master MCU, the master forwards them to a worker MCU, and the worker runs the task runtime.

High-level topology:

```
PC (Python/Jupyter)
    |
    |  USB Serial (line-delimited commands)
    v
ESP32-S3 MASTER (Arduino)
    |
    |  interconnect (UART / framing layer)
    v
ESP32-S3 WORKER (MicroPython)
```

---

## Installation

```bash
pip install pyserial
```

---

## Quick start

```python
from broccoli_cluster import BroccoliCluster

with BroccoliCluster("COM25") as cluster:  # change to your master port
        cluster.define_task("add", "lambda a, b: a + b")
        print(cluster.execute("add", 5, 3))
```

Tip: the comprehensive test suite reads the port from an env var:

```bash
set BROCCOLI_PORT=COM25
```

---

## Protocol (PC ↔ master)

The PC-facing protocol is intentionally simple: **one command per line**, **one response per line**.

Commands:

| Command | Format | Example |
|---|---|---|
| Define | `DEFINE:<task_name>:<code>` | `DEFINE:add:lambda a,b: a+b` |
| Execute | `EXEC:<task_name>:<args>` | `EXEC:add:5,3` |
| Execute w/ core | `EXEC:<task>:CORE:<0|1>:<args>` | `EXEC:square:CORE:1:100` |
| List | `LIST` | `LIST` |
| Canvas | `CANVAS:<TYPE>:<json>` | `CANVAS:GROUP:{...}` |
| Stats | `STATS` | `STATS` |
| Upload | `UPLOAD:<filename>:<content>` | `UPLOAD:test.py:def f():...` |

Responses (typical):

| Response | Format | Example |
|---|---|---|
| OK | `OK:<...>` | `OK:DEFINED:add` |
| Submitted | `OK:SUBMITTED:<id>` | `OK:SUBMITTED:1` |
| Result | `RESULT:<task>:<value>` | `RESULT:add:8` |
| Error | `ERROR:<message>` | `ERROR:TASK_NOT_DEFINED` |

---

## Core features

### Dynamic tasks

The worker stores the task code and evaluates it at runtime.

```python
cluster.define_task("square", "lambda x: x * x")
print(cluster.execute("square", 9))
```

### Dual-core execution

```python
cluster.define_task("square", "lambda x: x * x")
print(cluster.execute("square", 50, core=0))
print(cluster.execute("square", 100, core=1))
```

### Canvas primitives

```python
cluster.define_task("add", "lambda a,b: a+b")
cluster.define_task("multiply", "lambda a,b: a*b")
cluster.define_task("square", "lambda x: x*x")

print(cluster.group([
        cluster.sig("add", 5, 3),
        cluster.sig("multiply", 4, 7),
        cluster.sig("square", 9),
]))
```

---

## Tests

### Smoke test

`test_direct.py` is the fastest “is the pipeline alive?” check.

```bash
python test_direct.py
```

### Comprehensive test suite (14 tests)

`test_everything.py` runs end-to-end integration tests against real hardware.

```bash
python test_everything.py
```

What it covers:
- Task definition/execution
- GROUP/CHAIN/CHORD
- Dual-core
- Peripheral init (I2C/SPI/UART/CAN)
- GPIO/PWM
- ADC
- System monitoring
- Dynamic upload
- Error handling
- Task listing

---

## Known issues (practical)

- **Hardware-dependent serial stability**: if you see corruption/timeouts, lower the interconnect baud and keep wiring short + common ground.
- **Dynamic upload payloads**: large strings need more robust framing/escaping.
- **Terminology mismatch**: some modules still use “SLIP” naming even though the PC-facing protocol is line-delimited text.

---

## Jupyter

See `../../notebooks/cluster_control.ipynb` for interactive control.
