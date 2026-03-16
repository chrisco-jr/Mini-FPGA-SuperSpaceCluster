import time
import sys
from slip_protocol_linux import SLIPProtocol

class MasterNode:
    def __init__(self, worker_configs):
        self.workers = {}
        for w_id, device_path in worker_configs:
            try:
                self.workers[w_id] = SLIPProtocol(device_path, 115200)
            except Exception as e:
                print(f"[ERROR] Failed to init Worker {w_id} on {device_path}: {e}")

        self.num_workers = len(self.workers)
        self.next_task_id = 1
        self.show_welcome_screen()

    def show_welcome_screen(self):
        print("\n\n=================================")
        print("PYNQ-Z2 / PetaLinux Broccoli Master Node")
        print("SLIP Network Configuration (Base Ver.)")
        print(f"NUM_WORKERS: {self.num_workers}")
        print("=================================")
        print("\nMaster node ready!")
        print(f"Waiting for {self.num_workers} worker connection(s)...")
        print("\nCommands:")
        print("  === Multi-Worker Commands ===")
        print("  DEFINEW:worker:task_name:code")
        print("  EXECW:worker:task_name:args")
        print("  LISTW:worker")
        print("  UPLOADW:worker:filename:code")
        print("  === Legacy Commands (Default Worker 0) ===")
        print("  DEFINE:task_name:code | EXEC:task_name:args | LIST")
        print("  === System Commands ===")
        print("  STATS (Basic Connection Check)")
        print("-" * 33)

    def process_command(self, cmd):
        cmd = cmd.strip()
        if not cmd: return

        if cmd == "STATS":
            print("\n--- SLIP Statistics ---")
            for w_id, proto in self.workers.items():
                status = "OPEN" if proto.slip.serial.is_open else "CLOSED"
                print(f"Worker {w_id}: {status} on {proto.slip.serial.port}")
            return

        try:
            if cmd.startswith("DEFINEW:"):
                parts = cmd.split(':', 3)
                if len(parts) == 4:
                    self.forward_to_worker(int(parts[1]), f"DEFINE:{parts[2]}:{parts[3]}", parts[2])
                else:
                    print("ERROR:INVALID_DEFINEW_FORMAT")

            elif cmd.startswith("EXECW:"):
                parts = cmd.split(':', 3)
                if len(parts) == 4:
                    self.forward_to_worker(int(parts[1]), f"EXEC:{parts[2]}:{parts[3]}", parts[2])
                else:
                    print("ERROR:INVALID_EXECW_FORMAT")

            elif cmd.startswith("LISTW"):
                # Handle both "LISTW:0" and "LISTW" (defaults to 0)
                w_id = 0
                if ":" in cmd:
                    w_id = int(cmd.split(':')[1])
                self.forward_to_worker(w_id, "LIST")

            elif cmd.startswith("UPLOADW:"):
                parts = cmd.split(':', 3)
                if len(parts) == 4:
                    self.forward_to_worker(int(parts[1]), f"UPLOAD:{parts[2]}:{parts[3]}")

            elif cmd.startswith("DEFINE:"):
                self.process_command(f"DEFINEW:0:{cmd[7:]}")
            elif cmd.startswith("EXEC:"):
                self.process_command(f"EXECW:0:{cmd[5:]}")
            elif cmd == "LIST":
                self.process_command("LISTW:0")
            elif cmd.startswith("UPLOAD:"):
                self.process_command(f"UPLOADW:0:{cmd[7:]}")
            else:
                print("ERROR:UNKNOWN_COMMAND")

        except Exception as e:
            print(f"ERROR:PARSER: {e}")

    def forward_to_worker(self, w_id, payload, task_name=None):
        if w_id not in self.workers:
            print(f"ERROR:WORKER_{w_id}_UNAVAILABLE")
            return

        worker = self.workers[w_id]
        p_bytes = payload.encode('utf-8') if isinstance(payload, str) else payload
        worker.send_packet(p_bytes)
        
        if any(kw in payload for kw in ["EXEC", "DEFINE", "LIST", "UPLOAD"]):
            if "EXEC" in payload:
                print(f"OK:SUBMITTED:{self.next_task_id}:WORKER{w_id}")
                self.next_task_id += 1

            response = worker.receive_packet_blocking(timeout_ms=5000)
            if response:
                resp_str = response.decode('utf-8', errors='replace').strip()
                if "EXEC" in payload and task_name:
                    val = resp_str[3:] if resp_str.startswith("OK:") else resp_str
                    print(f"RESULT:{task_name}:{val}")
                elif "LIST" in payload:
                    print(f"OK:TASKS:WORKER{w_id}\n{resp_str}")
                else:
                    print(resp_str)
            else:
                print(f"ERROR:WORKER_{w_id}_NO_RESPONSE")

if __name__ == "__main__":
    cluster_config = [(0, "/dev/ttyPS1")]
    master = MasterNode(cluster_config)
    while True:
        try:
            line = input("\nMaster > ")
            master.process_command(line)
        except (KeyboardInterrupt, EOFError):
            print("\nExit.")
            break
