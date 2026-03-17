# MicroPython Worker Setup Guide
# Complete instructions for flashing and deploying

## Overview

This guide converts ESP32 workers from C++ to MicroPython, enabling:
- ✅ Dynamic code uploads (no reflashing!)
- ✅ Import Python modules on the fly
- ✅ @Task decorator and Canvas primitives (group, chain, chord)
- ✅ All peripheral control (GPIO, PWM, I2C, SPI, UART, ADC/DAC)
- ✅ Dual-core execution
- ✅ System monitoring
- ✅ SLIP communication with master

## Prerequisites

```powershell
# Install required tools
pip install esptool
pip install adafruit-ampy
pip install pyserial
```

## Step 1: Download MicroPython Firmware

Download ESP32-S3 MicroPython firmware:
- https://micropython.org/download/ESP32_GENERIC_S3/
- Get latest stable version (v1.22+ recommended)
- File: `ESP32_GENERIC_S3-XXXXXXXX-vX.XX.X.bin`

## Step 2: Flash MicroPython to Workers

### Worker 1 (COM23)

```powershell
# Erase existing firmware
esptool.py --chip esp32s3 --port COM23 erase_flash

# Flash MicroPython (adjust filename)
esptool.py --chip esp32s3 --port COM23 --baud 460800 write_flash -z 0x0 ESP32_GENERIC_S3-20240222-v1.22.2.bin
```

### Worker 2 (COM26)

```powershell
# Erase existing firmware
esptool.py --chip esp32s3 --port COM26 erase_flash

# Flash MicroPython
esptool.py --chip esp32s3 --port COM26 --baud 460800 write_flash -z 0x0 ESP32_GENERIC_S3-20240222-v1.22.2.bin
```

## Step 3: Upload Worker Code

### Worker 1 Configuration

Edit `micropython_workers/main.py` line 13:
```python
MASTER_TX_PIN = 17  # Worker 1
MASTER_RX_PIN = 18
```

Upload to Worker 1:
```powershell
cd micropython_workers

# Upload all modules
ampy --port COM23 --baud 115200 put boot.py
ampy --port COM23 --baud 115200 put main.py
ampy --port COM23 --baud 115200 put slip_protocol.py
ampy --port COM23 --baud 115200 put peripheral_control.py
ampy --port COM23 --baud 115200 put system_monitor.py
ampy --port COM23 --baud 115200 put dual_core.py
ampy --port COM23 --baud 115200 put task_executor.py
ampy --port COM23 --baud 115200 put canvas.py
```

### Worker 2 Configuration

Edit `micropython_workers/main.py` line 13:
```python
MASTER_TX_PIN = 16  # Worker 2
MASTER_RX_PIN = 15
```

Upload to Worker 2:
```powershell
# Upload all modules (same as Worker 1)
ampy --port COM26 --baud 115200 put boot.py
ampy --port COM26 --baud 115200 put main.py
ampy --port COM26 --baud 115200 put slip_protocol.py
ampy --port COM26 --baud 115200 put peripheral_control.py
ampy --port COM26 --baud 115200 put system_monitor.py
ampy --port COM26 --baud 115200 put dual_core.py
ampy --port COM26 --baud 115200 put task_executor.py
ampy --port COM26 --baud 115200 put canvas.py
```

## Step 4: Verify Installation

Test Worker 1:
```powershell
# Connect to REPL
python -m serial.tools.miniterm COM23 115200

# Should see:
# ==================================================
# ESP32-S3 MicroPython Worker Boot
# ==================================================
# [Worker] All systems initialized
# [Worker] Ready to receive commands

# Press Ctrl+C to interrupt, then test:
>>> import gc
>>> gc.mem_free()  # Should show available RAM
>>> import machine
>>> machine.freq()  # Should show 240000000 (240 MHz)
```

## Step 5: Master Node (Keep C++ Master)

Master node stays as C++ (no changes needed):
```powershell
# Already flashed, no action required
# Master on COM23 communicates via SLIP to MicroPython workers
```

## Step 6: Test Complete System

Run the test script:
```powershell
cd platformio_slip\python_client
python test_everything.py
```

Expected behavior:
- ✅ Connection successful
- ✅ Tasks define and execute
- ✅ Dual-core execution works
- ✅ GPIO/peripheral control works
- ✅ System monitoring works

## Step 7: Dynamic Code Upload (NEW FEATURE!)

Now you can upload code without reflashing:

```python
from broccoli_cluster import BroccoliCluster

with BroccoliCluster("COM23") as cluster:
    # Upload a Python module
    cluster.upload_file("my_algorithm.py")
    
    # Define task that uses it
    cluster.define_task("run_algo", """
import my_algorithm
result = my_algorithm.process(data)
return result
""")
    
    # Execute
    result = cluster.execute("run_algo", my_data)
```

## File Structure

```
micropython_workers/
├── boot.py                   # Boot script (runs first)
├── main.py                   # Main worker program
├── slip_protocol.py          # SLIP encoder/decoder
├── peripheral_control.py     # GPIO, PWM, I2C, SPI, etc.
├── system_monitor.py         # RAM, Flash, CPU monitoring
├── dual_core.py              # Dual-core task execution
├── task_executor.py          # Dynamic task engine
└── canvas.py                 # Canvas primitives (group, chain, chord)
```

## Pin Configuration Summary

| Worker | UART | TX Pin | RX Pin | Purpose |
|--------|------|--------|--------|---------|
| Master | UART0 | USB | USB | PC Connection (COM25) |
| Master | UART1 | GPIO17 | GPIO18 | To Worker 1 |
| Master | UART2 | GPIO16 | GPIO15 | To Worker 2 |
| Worker 1 | UART1 | GPIO17 | GPIO18 | SLIP to Master (COM23) |
| Worker 2 | UART1 | GPIO16 | GPIO15 | SLIP to Master (COM26) |

## Troubleshooting

### Workers not responding
```powershell
# Check if MicroPython is running
python -m serial.tools.miniterm COM23 115200
# Press Ctrl+C to interrupt
# Should see >>> REPL prompt
```

### Upload fails
```powershell
# Increase delay between ampy commands
ampy --port COM23 --baud 115200 --delay 2 put main.py
```

### Memory errors
```python
# In MicroPython REPL
>>> import gc
>>> gc.collect()  # Force garbage collection
>>> gc.mem_free()  # Check available memory
```

### Import errors
```powershell
# Verify all files uploaded
ampy --port COM23 --baud 115200 ls
# Should show all .py files
```

## Performance Notes

- MicroPython is ~10x slower than C++ but still fast enough for most tasks
- Dual-core helps with parallel I/O
- Trade-off: Flexibility vs Speed (you gain dynamic code, lose some speed)

## Space Application Notes

For space deployment:
1. ✅ Can update code from ground station (no reflashing!)
2. ✅ Import new modules as mission needs change
3. ✅ Watchdog timer recommended (add to main.py)
4. ✅ Error logging to file for telemetry
5. ✅ Dual-partition firmware for rollback (ESP32 OTA feature)

## Next Steps

1. Run `test_everything.py` to verify all features
2. Try uploading custom Python modules
3. Test Canvas primitives (group, chain, chord)
4. Monitor system resources during operation
5. Develop space-specific tasks and upload dynamically

## Advantages Over C++ Version

| Feature | C++ | MicroPython |
|---------|-----|-------------|
| Dynamic code upload | ❌ Must reflash | ✅ Upload anytime |
| Import libraries | ❌ Hardcoded | ✅ On-the-fly |
| Canvas primitives | ❌ Not implemented | ✅ Full support |
| @Task decorator | ❌ Manual | ✅ Elegant |
| Speed | ✅ Fast | ⚠️ ~10x slower |
| Peripheral control | ✅ Full | ✅ Full |
| Dual-core | ✅ FreeRTOS | ✅ _thread |
| System monitoring | ✅ Detailed | ✅ Good enough |

## Support

If issues occur:
1. Check serial connections
2. Verify pin assignments
3. Test REPL access
4. Check memory with gc.mem_free()
5. Review error messages from SLIP communication
