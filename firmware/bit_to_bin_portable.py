import sys
import os
import struct

def convert_on_target(input_file):
    if not os.path.exists(input_file):
        print(f"[-] Error: {input_file} not found.")
        return

    output_file = input_file.replace(".bit", ".bin")
    # The standard Xilinx Sync Word in a .bit file
    sync_word = b'\xAA\x99\x55\x66'

    with open(input_file, 'rb') as f:
        data = f.read()

    # 1. Find the start of the actual FPGA configuration data
    idx = data.find(sync_word)
    if idx == -1:
        print(f"[-] Error: Could not find Sync Word in {input_file}.")
        return

    # 2. Strip the header
    raw_config_data = data[idx:]

    # 3. Byte Swap Logic
    # The FPGA Manager on Zynq-7000 requires 32-bit word swapping.
    # We pad the data to ensure it's a multiple of 4 bytes.
    padding = len(raw_config_data) % 4
    if padding != 0:
        raw_config_data += b'\xFF' * (4 - padding)

    print(f"[*] Swapping bytes for {len(raw_config_data)} bytes...")
    
    # This unpacks the data as Big-Endian and repacks it as Little-Endian
    count = len(raw_config_data) // 4
    # 'I' is an unsigned 32-bit integer. '>' is Big-Endian, '<' is Little-Endian.
    words = struct.unpack(f'>{count}I', raw_config_data)
    swapped_data = struct.pack(f'<{count}I', *words)

    # 4. Write the final .bin
    with open(output_file, 'wb') as f:
        f.write(swapped_data)
    
    print(f"[+] Success: Created {output_file}")
    print(f"[!] Now run: fpgautil -b {output_file} -p 1")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 bit_to_bin_portable.py <file.bit>")
    else:
        for bit_file in sys.argv[1:]:
            convert_on_target(bit_file)
