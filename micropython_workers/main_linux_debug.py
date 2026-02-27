## main_linux.py
# PYNQ / PetaLinux Worker Node
# Uses SLIP protocol for reliable communication
# Includes debug info for incoming/outgoing packets

import threading
import json
import os
import time

from dual_core_linux import DualCoreExecutor
from task_executor import TaskExecutor
from canvas import create_canvas_api
from slip_protocol_linux import SLIPProtocol  # <-- Updated import


class WorkerNode:
    """Worker node communicating over SLIP with debug"""

    def __init__(self, uart_device="/dev/ttyPS1", baudrate=115200, debug=True):
        self.debug = debug
        print("[WorkerNode] Initializing...")

        # Use SLIP protocol wrapper
        self.slip = SLIPProtocol(uart_device, baudrate)

        # Execution stack
        self.dual_core = DualCoreExecutor()
        self.task_executor = TaskExecutor(self.dual_core, global_scope=globals())
        self.canvas = create_canvas_api(self.task_executor)

        print("[WorkerNode] Ready")

    # ==========================================================
    # Main Loop
    # ==========================================================
    def start(self):
        print("[WorkerNode] Listening for commands...")

        while True:
            try:
                # Receive a full SLIP packet (blocking)
                packet = self.slip.receive_packet_blocking(timeout_ms=1000)
                if not packet:
                    continue

                if self.debug:
                    print(f"[DEBUG] Raw packet bytes: {packet}")

                try:
                    message = packet.decode("utf-8").strip()
                    if self.debug:
                        print(f"[DEBUG] Decoded message: {message}")
                except Exception:
                    message = packet
                    if self.debug:
                        print(f"[DEBUG] Non-UTF8 packet received: {packet}")

                response = self.process_message(message)

                if response:
                    self.send(response)

            except Exception as e:
                self.send(f"ERROR:MainLoop_{e}")

    # ==========================================================
    # Message Processing
    # ==========================================================
    def process_message(self, message):
        if ':' in message:
            command, params = message.split(':', 1)
        else:
            command = message
            params = ""

        return self.handle_command(command.strip(), params.strip())

    # ==========================================================
    # Command Handler
    # ==========================================================
    def handle_command(self, command, params):
        try:
            # -------------------------------
            # Task Management
            # -------------------------------
            if command == "DEFINE":
                parts = params.split(':', 1)
                if len(parts) == 2:
                    task_name, code = parts
                    return self.task_executor.define_task(task_name, code)
                return "ERROR:Invalid_DEFINE_format"

            elif command == "EXEC":
                parts = params.split(':')
                task_name = parts[0]
                core = None
                args = ()
                kwargs = {}
                if len(parts) > 1:
                    if parts[1] == "CORE" and len(parts) > 2:
                        core = int(parts[2])
                        if len(parts) > 3 and parts[3]:
                            args = eval(f"({parts[3]},)")
                    elif parts[1]:
                        args = eval(f"({parts[1]},)")
                return self.task_executor.execute_task(task_name, args, kwargs, core)

            elif command == "LIST":
                return self.task_executor.list_tasks()

            elif command == "STATS":
                return self.task_executor.get_stats()

            # -------------------------------
            # Canvas Primitives
            # -------------------------------
            elif command == "CANVAS":
                parts = params.split(':', 1)
                if len(parts) == 2:
                    primitive_type, data_json = parts
                    try:
                        data = json.loads(data_json)
                        status, result = self.canvas.execute_primitive(primitive_type, data)
                        if status == "success":
                            return f"OK:{json.dumps(result)}"
                        else:
                            return f"ERROR:{result}"
                    except Exception as e:
                        return f"ERROR:Canvas_{primitive_type}_{e}"
                return "ERROR:Invalid_CANVAS_format"

            # -------------------------------
            # Peripheral Commands (Stubbed)
            # -------------------------------
            elif command.startswith(("GPIO", "PWM", "ADC", "DAC",
                                     "I2C", "SPI", "UART", "CAN")):
                return "ERROR:Peripheral_not_implemented_on_PYNQ"

            # -------------------------------
            # System Monitoring
            # -------------------------------
            elif command == "SYS_INFO":
                return f"OK:uname={os.uname().sysname}"

            elif command == "RAM_USAGE":
                with open("/proc/meminfo") as f:
                    return f"OK:{f.readline().strip()}"

            elif command == "CPU_USAGE":
                with open("/proc/loadavg") as f:
                    return f"OK:{f.read().strip()}"

            elif command == "UPTIME":
                with open("/proc/uptime") as f:
                    return f"OK:{f.read().strip()}"

            elif command == "TASK_LIST":
                return self.task_executor.list_tasks()

            # -------------------------------
            # File Upload
            # -------------------------------
            elif command == "UPLOAD":
                parts = params.split(':', 1)
                if len(parts) == 2:
                    filename, content = parts
                    try:
                        with open(filename, 'w') as f:
                            f.write(content)
                        return f"OK:Uploaded_{filename}"
                    except Exception as e:
                        return f"ERROR:{e}"
                return "ERROR:Invalid_UPLOAD_format"

            # -------------------------------
            # Reset
            # -------------------------------
            elif command == "RESET":
                self.send("OK:RESETTING")
                time.sleep(0.2)
                os.system("reboot")
                return None

            # -------------------------------
            # Ping
            # -------------------------------
            elif command == "PING":
                return "PONG"

            else:
                return f"ERROR:Unknown_command_{command}"

        except Exception as e:
            return f"ERROR:Handler_exception_{e}"

    # ==========================================================
    # Send over SLIP
    # ==========================================================
    def send(self, message):
        """Send a message via SLIP with debug output"""
        try:
            print(f"[WorkerNode] Sending message: {message}")
            # Use the public SLIPProtocol method
            self.slip.send_packet(message)
            time.sleep(0.001)
        except Exception as e:
            print(f"[WorkerNode] Send failed: {e}")

# ==============================================================
# Entry Point
# ==============================================================
if __name__ == "__main__":
    node = WorkerNode("/dev/ttyPS1", 115200, debug=True)
    node.start()
