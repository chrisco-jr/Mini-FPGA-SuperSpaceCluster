import os
import mmap
import time

# GPIO Physical Address
GPIO_BASE = 0x41200000
GPIO_DATA = 0x00
GPIO_TRI  = 0x04

def start_counter():
    # Open /dev/mem for physical memory access
    fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    mem = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=GPIO_BASE)

    try:
        # Set GPIO pins as outputs (write 0 to TRI register)
        mem[GPIO_TRI:GPIO_TRI+4] = (0).to_bytes(4, byteorder='little')
        
        print("Starting 4-bit Binary Counter (0-15)...")
        print("Press Ctrl+C to stop.")

        while True:
            for count in range(16):  # 0 to 15
                # Write the count to the Data register
                mem[GPIO_DATA:GPIO_DATA+4] = count.to_bytes(4, byteorder='little')
                
                # Format string to show binary representation in terminal
                print(f"Count: {count:2} | Binary: {count:04b}")
                
                time.sleep(0.5)  # Adjust speed here
            break
    except KeyboardInterrupt:
        print("\nStopping counter. Resetting LEDs...")
        mem[GPIO_DATA:GPIO_DATA+4] = (0).to_bytes(4, byteorder='little')
    finally:
        mem.close()
        os.close(fd)

if __name__ == "__main__":
    start_counter()
