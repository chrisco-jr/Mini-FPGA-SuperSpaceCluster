# SLIP Protocol for Linux / PetaLinux / PYNQ
# Works with standard pyserial

import time
import serial

SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD


class SLIPInterface:
    """SLIP protocol encoder/decoder for Linux (pyserial)"""

    def __init__(self, uart_device="/dev/ttyPS1", baudrate=115200, timeout=0.01):
        self.serial = serial.Serial(uart_device, baudrate=baudrate, timeout=timeout)
        self.buffer = bytearray()
        print(f"[SLIP] Initialized {uart_device} at {baudrate} baud")

    def encode(self, data):
        """Encode data with SLIP framing"""
        if isinstance(data, str):
            data = data.encode("utf-8")

        packet = bytearray([SLIP_END])
        for byte in data:
            if byte == SLIP_END:
                packet.extend([SLIP_ESC, SLIP_ESC_END])
            elif byte == SLIP_ESC:
                packet.extend([SLIP_ESC, SLIP_ESC_ESC])
            else:
                packet.append(byte)
        packet.append(SLIP_END)
        return packet

    def send(self, data):
        """Send data with SLIP encoding"""
        try:
            packet = self.encode(data)
            self.serial.write(packet)
            self.serial.flush()
        except Exception as e:
            print(f"[SLIP] Send failed: {e}")

    def receive(self):
        """Receive and decode SLIP packet (non-blocking)"""
        try:
            while self.serial.in_waiting:
                byte = self.serial.read(1)
                if not byte:
                    break
                byte = byte[0]

                if byte == SLIP_END:
                    if self.buffer:
                        packet = bytes(self.buffer)
                        self.buffer = bytearray()
                        return packet
                elif byte == SLIP_ESC:
                    next_byte = self.serial.read(1)
                    if not next_byte:
                        continue
                    next_byte = next_byte[0]
                    if next_byte == SLIP_ESC_END:
                        self.buffer.append(SLIP_END)
                    elif next_byte == SLIP_ESC_ESC:
                        self.buffer.append(SLIP_ESC)
                else:
                    self.buffer.append(byte)

        except Exception as e:
            print(f"[SLIP] Receive failed: {e}")

        return None

    def receive_blocking(self, timeout_ms=5000):
        """Receive SLIP packet with timeout (ms)"""
        start_time = time.time()
        timeout_s = timeout_ms / 1000.0
        while (time.time() - start_time) < timeout_s:
            packet = self.receive()
            if packet:
                return packet
            time.sleep(0.001)  # 1 ms sleep to prevent CPU spin
        return None


class SLIPProtocol:
    """High-level SLIP wrapper for Linux / FPGA"""

    def __init__(self, uart_device="/dev/ttyPS1", baudrate=115200):
        self.slip = SLIPInterface(uart_device, baudrate)
        print("[SLIPProtocol] Ready")

    def send_packet(self, data):
        """Send packet (string or bytes)"""
        self.slip.send(data)

    def receive_packet(self):
        """Non-blocking receive"""
        return self.slip.receive()

    def receive_packet_blocking(self, timeout_ms=5000):
        """Blocking receive with timeout"""
        return self.slip.receive_blocking(timeout_ms)
