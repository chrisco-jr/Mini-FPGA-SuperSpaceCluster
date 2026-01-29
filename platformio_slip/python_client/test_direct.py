import serial
import time

ser = serial.Serial('COM25', 115200, timeout=2)
time.sleep(0.5)
ser.reset_input_buffer()

print("1. Sending DEFINE command...")
ser.write(b"DEFINE:add:lambda a,b: a+b\n")
ser.flush()
time.sleep(0.3)

while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"  {line}")

print("\n2. Sending EXEC command...")
ser.write(b"EXEC:add:5,3\n")
ser.flush()
time.sleep(0.3)

while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"  {line}")

print("\n3. Waiting 2 seconds for result...")
time.sleep(2)
while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"  {line}")

ser.close()
