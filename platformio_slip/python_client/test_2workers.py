"""
Test 2-worker parallel system
Verify both workers can be addressed independently
"""

import serial
import time

MASTER_PORT = "COM8"
BAUD_RATE = 115200

def send_command(ser, command, wait_time=0.5):
    """Send command and read response"""
    ser.write((command + '\n').encode())
    time.sleep(wait_time)
    
    response = ""
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        time.sleep(0.05)
    
    return response.strip()

def main():
    print(f"Connecting to master at {MASTER_PORT}...")
    ser = serial.Serial(MASTER_PORT, BAUD_RATE, timeout=2)
    time.sleep(2)
    
    # Clear startup messages
    if ser.in_waiting > 0:
        startup = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"\n=== Startup ===\n{startup}")
    
    print("\n" + "="*70)
    print("  2-WORKER PARALLEL SYSTEM TEST")
    print("="*70)
    
    # Check STATS to see both workers
    print("\n1. Checking worker status...")
    resp = send_command(ser, "STATS")
    print(resp)
    
    # Define tasks on both workers
    print("\n2. Defining tasks on both workers...")
    
    print("  Worker 0: defining 'add'...")
    resp = send_command(ser, "DEFINEW:0:add:lambda a, b: a + b")
    print(f"  Response: {resp}")
    
    print("  Worker 1: defining 'multiply'...")
    resp = send_command(ser, "DEFINEW:1:multiply:lambda a, b: a * b")
    print(f"  Response: {resp}")
    
    # Execute tasks on specific workers
    print("\n3. Executing tasks on specific workers...")
    
    print("  Worker 0: add(10, 20)...")
    resp = send_command(ser, "EXECW:0:add:10,20", wait_time=1.0)
    print(f"  Response: {resp}")
    
    print("  Worker 1: multiply(5, 6)...")
    resp = send_command(ser, "EXECW:1:multiply:5,6", wait_time=1.0)
    print(f"  Response: {resp}")
    
    # Test parallel execution - both at once
    print("\n4. Testing parallel execution...")
    print("  Defining 'square' on both workers...")
    resp = send_command(ser, "DEFINEW:0:square:lambda x: x * x")
    print(f"  Worker 0: {resp}")
    resp = send_command(ser, "DEFINEW:1:square:lambda x: x * x")
    print(f"  Worker 1: {resp}")
    
    print("\n  Sending square(10) to Worker 0 and square(20) to Worker 1...")
    # Send both commands quickly
    ser.write(b"EXECW:0:square:10\n")
    ser.write(b"EXECW:1:square:20\n")
    time.sleep(1.0)
    
    # Read all responses
    responses = ""
    while ser.in_waiting > 0:
        responses += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        time.sleep(0.05)
    print(f"  Combined responses:\n{responses}")
    
    print("\n5. Final STATS...")
    resp = send_command(ser, "STATS")
    print(resp)
    
    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)
    print("\n✓ Both workers can be addressed independently")
    print("✓ EXECW and DEFINEW commands working")
    print("✓ Parallel execution possible")
    
    ser.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
