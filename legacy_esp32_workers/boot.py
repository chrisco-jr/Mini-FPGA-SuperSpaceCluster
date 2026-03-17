# Boot script for MicroPython ESP32 Worker
# This runs before main.py

import gc
import time
from machine import Pin

# Enable automatic garbage collection
gc.enable()

# Initial garbage collection
gc.collect()

print("\n" + "="*50)
print("ESP32-S3 MicroPython Worker Boot")
print("="*50)
print(f"Free memory: {gc.mem_free()} bytes")

# Blink LED to indicate boot
led = Pin(2, Pin.OUT)
for _ in range(5):
    led.value(1)
    time.sleep_ms(100)
    led.value(0)
    time.sleep_ms(100)

print("[Boot] Initialization complete")
print("[Boot] Starting main.py...")
print("="*50 + "\n")

# Import and run main program
try:
    import main
except Exception as e:
    print(f"[Boot] Error loading main.py: {e}")
    # Blink LED rapidly to indicate error
    led = Pin(2, Pin.OUT)
    for _ in range(20):
        led.value(1)
        time.sleep_ms(50)
        led.value(0)
        time.sleep_ms(50)
