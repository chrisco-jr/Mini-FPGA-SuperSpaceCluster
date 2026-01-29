import serial
import time

ser = serial.Serial('COM25', 115200, timeout=1)
time.sleep(0.5)

print("Checking if master responds...")
ser.reset_input_buffer()
ser.write(b"LIST\n")
ser.flush()
time.sleep(0.3)

print("Response:")
found_response = False
while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"  {line}")
    found_response = True

if not found_response:
    print("  (no response)")

ser.close()
