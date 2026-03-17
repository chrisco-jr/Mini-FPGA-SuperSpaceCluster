# main_worker_linux.py
import time
from dual_core_linux import DualCoreExecutor
from task_executor import TaskExecutor
from canvas import create_canvas_api
from slip_protocol_linux import SLIPProtocol
from worker_commands import WorkerProcessor

class WorkerNode:
    def __init__(self, uart_device="/dev/ttyPS1", baudrate=115200, debug=True):
        self.debug = debug
        print("[WorkerNode] Initializing Transport...")
        self.slip = SLIPProtocol(uart_device, baudrate)

        # Initialize Execution Stack
        self.dual_core = DualCoreExecutor()
        self.task_executor = TaskExecutor(self.dual_core, global_scope=globals())
        self.canvas = create_canvas_api(self.task_executor)

        # Initialize the Brain (Command Processor)
        self.processor = WorkerProcessor(self.task_executor, self.canvas, self.dual_core)
        print("[WorkerNode] Ready")

    def start(self):
        print("[WorkerNode] Listening for Master commands...")
        while True:
            try:
                packet = self.slip.receive_packet_blocking(timeout_ms=1000)
                if not packet: continue

                # Decoding logic
                try:
                    message = packet.decode("utf-8").strip()
                except Exception:
                    message = packet # Fallback for non-UTF8

                if self.debug: print(f"[DEBUG] RECV: {message}")

                # Process through the new module
                response = self.processor.dispatch(message)

                if response:
                    if self.debug: print(f"[DEBUG] SEND: {response}")
                    self.slip.send_packet(response)

            except Exception as e:
                self.slip.send_packet(f"ERROR:MainLoop_{e}")

if __name__ == "__main__":
    node = WorkerNode("/dev/ttyPS1", 115200, debug=True)
    node.start()
