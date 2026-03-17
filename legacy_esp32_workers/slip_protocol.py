# SLIP Protocol for MicroPython
# Serial Line Internet Protocol implementation

SLIP_END = const(0xC0)
SLIP_ESC = const(0xDB)
SLIP_ESC_END = const(0xDC)
SLIP_ESC_ESC = const(0xDD)


class SLIPInterface:
    """SLIP protocol encoder/decoder for MicroPython"""
    
    def __init__(self, uart_id, tx_pin, rx_pin, baudrate=921600):
        from machine import UART, Pin
        self.uart = UART(uart_id, baudrate=baudrate, tx=tx_pin, rx=rx_pin, timeout=10)
        self.buffer = bytearray()
        print(f"[SLIP] Initialized UART{uart_id} at {baudrate} baud")
    
    def encode(self, data):
        """Encode data with SLIP framing"""
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
        if isinstance(data, str):
            data = data.encode('utf-8')
        packet = self.encode(data)
        self.uart.write(packet)
    
    def receive(self):
        """Receive and decode SLIP packet (non-blocking)"""
        while self.uart.any():
            byte = self.uart.read(1)[0]
            
            if byte == SLIP_END:
                if len(self.buffer) > 0:
                    data = bytes(self.buffer)
                    self.buffer = bytearray()
                    return data
            elif byte == SLIP_ESC:
                if self.uart.any():
                    next_byte = self.uart.read(1)[0]
                    if next_byte == SLIP_ESC_END:
                        self.buffer.append(SLIP_END)
                    elif next_byte == SLIP_ESC_ESC:
                        self.buffer.append(SLIP_ESC)
            else:
                self.buffer.append(byte)
        
        return None
    
    def receive_blocking(self, timeout_ms=5000):
        """Receive SLIP packet with timeout"""
        import time
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            packet = self.receive()
            if packet:
                return packet
            time.sleep_ms(10)
        
        return None


class SLIPProtocol:
    """High-level SLIP protocol wrapper for main program"""
    
    def __init__(self):
        # Configure for UART pins 18/17 @ 921600 baud (TX=18, RX=17 for crossover with master)
        self.slip = SLIPInterface(1, 18, 17, 921600)
        print("[SLIPProtocol] Ready")
    
    def send_packet(self, data):
        """Send packet"""
        self.slip.send(data)
    
    def receive_packet(self):
        """Receive packet (non-blocking)"""
        return self.slip.receive()
    
    def receive_packet_blocking(self, timeout_ms=5000):
        """Receive packet (blocking with timeout)"""
        return self.slip.receive_blocking(timeout_ms)
