# main_worker_linux.py
import time
import sys
from dual_core_linux import DualCoreExecutor
from task_executor import TaskExecutor
from canvas import create_canvas_api
from slip_protocol_linux import SLIPProtocol
from worker_commands import WorkerProcessor

class WorkerNode:
    def __init__(self, uart_device="/dev/ttyPS1", baudrate=115200, debug=True):
        self.debug = debug
        print(f"[*] [WorkerNode] Initializing on {uart_device} @ {baudrate}...")
        
        # Initialize SLIP Transport
        try:
            self.slip = SLIPProtocol(uart_device, baudrate)
        except Exception as e:
            print(f"[FATAL] UART Initialization failed: {e}")
            sys.exit(1)

        # Initialize Execution Stack (Cortex-A9 Core Management)
        self.dual_core = DualCoreExecutor()
        self.task_executor = TaskExecutor(self.dual_core, global_scope=globals())
        self.canvas = create_canvas_api(self.task_executor)

        # Initialize the Command Processor (The Registry)
        self.processor = WorkerProcessor(
            self.task_executor, 
            self.canvas, 
            self.dual_core
        )
        print("[*] [WorkerNode] Hardware & Command Stack READY")

    def start(self):
        print("[*] [WorkerNode] Listening for Master commands...")
        while True:
            try:
                # 1. Blocking wait for SLIP-framed packet
                packet = self.slip.receive_packet_blocking(timeout_ms=1000)
                if not packet: 
                    continue

                # 2. Robust Decoding
                # We strip null bytes which often appear on serial lines during noise
                try:
                    message = packet.decode("utf-8", errors='ignore').strip().replace('\x00', '')
                    if not message: continue
                except Exception as e:
                    if self.debug: print(f"[WARN] Decode error: {e}")
                    continue

                if self.debug: 
                    print(f"[{time.strftime('%H:%M:%S')}] RECV: {message}")

                # 3. Process Command
                # The processor returns a string (e.g., "OK:SUBMITTED:12345")
                response = self.processor.dispatch(message)

                # 4. Transmit Response
                if response:
                    if self.debug: 
                        print(f"[{time.strftime('%H:%M:%S')}] SEND: {response}")
                    
                    # Ensure the response is encoded back for SLIP
                    self.slip.send_packet(response.encode('utf-8'))

            except KeyboardInterrupt:
                print("\n[*] Worker shutting down...")
                break
            except Exception as e:
                # Inform the Master that a loop-level error occurred
                err_msg = f"ERROR:Worker_MainLoop_{str(e)[:50]}"
                print(f"[CRITICAL] {err_msg}")
                try:
                    self.slip.send_packet(err_msg.encode('utf-8'))
                except:
                    pass

if __name__ == "__main__":
    # Standard Pynq-Z2 UART is usually /dev/ttyPS1
    node = WorkerNode("/dev/ttyPS1", 115200, debug=True)
    node.start()