import time
import sys
import socket
import argparse
from slip_protocol_linux import SLIPProtocol

class MasterNode:
    def __init__(self, worker_configs):
        self.workers = {}
        for w_id, device_path in worker_configs:
            try:
                # Initializing the SLIP connection to the ESP32/Worker hardware
                self.workers[w_id] = SLIPProtocol(device_path, 115200)
            except Exception as e:
                print(f"[ERROR] Failed to init Worker {w_id} on {device_path}: {e}")

        self.num_workers = len(self.workers)
        self.next_task_id = 1
        self.show_welcome_screen()

    def show_welcome_screen(self):
        print("\n\n=================================")
        print("PYNQ-Z2 / PetaLinux Broccoli Master Node")
        print(f"NUM_WORKERS: {self.num_workers}")
        print("=================================")
        print("\nMaster node ready!")
        print(f"Waiting for {self.num_workers} worker connection(s)...")

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
        
        # Feedback loop for execution tasks
        if "EXEC" in payload:
            print(f"OK:SUBMITTED:{self.next_task_id}:WORKER{w_id}")
            self.next_task_id += 1

        # Wait for worker response over UART (ttyPS1)
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

# --- CONTEXT HANDLER FOR MODES ---

def run_serial_mode(master_node):
    print("[*] Entering Interactive Serial Mode (Local Terminal Control)")
    while True:
        try:
            line = input("\nMaster > ")
            master_node.process_command(line)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Serial Mode.")
            break

def run_network_mode(master_node):
    HOST = '0.0.0.0' # Accept connections on Ethernet (end0)
    PORT = 5000
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[*] Network Mode Online: {HOST}:{PORT}")
        print("[*] Listening for connection from PC...")
        
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"[*] Connected by {addr}")
                # Create a file-like object for reading from the socket
                sock_file = conn.makefile('r', encoding='utf-8')
                while True:
                    line = sock_file.readline()
                    if not line: break # PC Disconnected
                    
                    # Capture all 'print' output to send back to the PC socket
                    original_stdout = sys.stdout
                    sys.stdout = conn.makefile('w', encoding='utf-8')
                    try:
                        master_node.process_command(line.strip())
                    finally:
                        sys.stdout.flush()
                        sys.stdout.close()
                        sys.stdout = original_stdout

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broccoli Cluster Master Node")
    parser.add_argument('--mode', choices=['network', 'serial'], default='network',
                        help="Mode: 'network' for Ethernet control, 'serial' for local terminal.")
    
    args = parser.parse_args()

    # Hardware Config: Worker 0 is on the secondary UART (/dev/ttyPS1)
    cluster_config = [(0, "/dev/ttyPS1")]
    master = MasterNode(cluster_config)

    if args.mode == 'network':
        run_network_mode(master)
    else:
        run_serial_mode(master)
