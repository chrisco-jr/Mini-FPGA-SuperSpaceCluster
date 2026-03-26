# main_master.py
import socket
import argparse
import sys
import time
from slip_protocol_linux import SLIPProtocol
from master_commands import CommandProcessor
from datetime import datetime

class MasterNode:
    def __init__(self, worker_configs):
        self.workers = {}
        # Track packet counts for each worker ID
        self.stats = {}
        # CRITICAL: Maps Task IDs to Worker IDs so the SDK can poll results
        self.task_map = {} 
        
        for w_id, device_path in worker_configs:
            try:
                self.workers[w_id] = SLIPProtocol(device_path, 115200)
                self.stats[w_id] = {"tx": 0, "rx": 0}
            except Exception as e:
                print(f"[ERROR] Worker {w_id} initialization failed: {e}")
        
        self.next_task_id = 1

    def show_welcome_screen(self):
        now = datetime.now()
        menu = (
            "\n" + "="*45 +
            "\n  PYNQ-Z2 BROCCOLI CLUSTER MASTER NODE" +
            f"\n  System Date/Time : {now.strftime('%Y-%m-%d %H:%M:%S')} | Status: READY" +
            "\n" + "="*45 +
            "\n[AVAILABLE COMMANDS]" +
            "\n" + "-" * 45 +
            "\n  STATS           - Active health (Ping/Pong/Loss)" +
            "\n  SYS_INFO        - Detailed Hardware Telemetry (Zynq XADC)" +
            "\n  RESET_STATS     - Zero out TX/RX packet counters" +
            "\n  LIST            - List tasks defined on Worker 0" +
            "\n  DEFINE:[N]:[C]  - Define task [N] with code [C]" +
            "\n  EXEC:[N]:[A]    - Execute task [N] with args [A]" +
            "\n  GET_RES:[ID]    - Retrieve result for specific Task ID" +
            "\n  DELETE:[N]      - Delete task [N] from Task List" +
            "\n  CLEAR           - Delete all tasks from from Task List" +
            "\n  HELP            - Show this menu" +
            "\n" + "-" * 45 +
            "\n  * Use prefix 'W' (e.g., LISTW:1) for specific workers" +
            "\n" + "="*45 + "\n"
        )
        print(menu)
        return menu

    def reset_stats(self):
        """Zeroes out the TX/RX counters for all workers."""
        for w_id in self.stats:
            self.stats[w_id] = {"tx": 0, "rx": 0}
        print("[*] Statistics counters reset.")
        return "OK:STATS_RESET"

    def get_stats(self, silent=False):
        """Active health check with packet throughput tracking."""
        if not silent:
            header = f"\n{'ID':<4} | {'STATUS':<12} | {'TX':<6} | {'RX':<6} | {'LATENCY'}"
            print(header)
            print("-" * len(header))
        
        results = [] 
        
        for w_id, proto in self.workers.items():
            status_str = "OFFLINE"
            latency_str = "---"
            
            if proto.slip.serial.is_open:
                try:
                    proto.slip.serial.reset_input_buffer()
                    start_time = time.time()
                    proto.send_packet("PING".encode('utf-8'))
                    self.stats[w_id]["tx"] += 1
                    
                    response = proto.receive_packet_blocking(timeout_ms=1000)
                    if response and response.decode('utf-8', errors='replace').strip() == "PONG":
                        self.stats[w_id]["rx"] += 1
                        status_str = "ONLINE"
                        latency_str = f"{(time.time() - start_time)*1000:.1f}ms"
                    else:
                        status_str = "UNRESPONSIVE"
                except Exception:
                    status_str = "COMM_ERROR"

            tx = self.stats[w_id]["tx"]
            rx = self.stats[w_id]["rx"]
            
            if not silent:
                print(f"{w_id:<4} | {status_str:<12} | {tx:<6} | {rx:<6} | {latency_str}")
            else:
                results.append(f"W{w_id}:{status_str}:{tx}:{rx}:{latency_str}")

        if not silent:
            print("-" * 40 + "\n")
            return "OK:STATS_REPORTED"
        else:
            return "OK:STATS|" + "|".join(results)

    def forward_to_worker(self, w_id, payload, task_name=None):
        """Sends data to worker, tracks stats, and returns response."""
        if w_id not in self.workers:
            err = f"ERROR:WORKER_{w_id}_NOT_FOUND"
            print(err)
            return err

        worker = self.workers[w_id]
        
        # 1. Log Transmission
        worker.send_packet(payload.encode('utf-8'))
        self.stats[w_id]["tx"] += 1
        
        # 2. Wait for response (Blocking for SoC Serial timing)
        response = worker.receive_packet_blocking(timeout_ms=5000)
        
        if response:
            self.stats[w_id]["rx"] += 1
            resp_decoded = response.decode('utf-8', errors='replace').strip()
            
            # INTEGRATION FIX: 
            # If the worker confirms a task submission, we must map the 
            # returned Task ID to this worker ID. This allows GET_RES:[ID] 
            # to work without the SDK needing to specify the worker.
            if "OK:SUBMITTED" in resp_decoded:
                parts = resp_decoded.split(':')
                tid = parts[-1]
                self.task_map[tid] = w_id 
                
            print(f"[W{w_id} RECV] {resp_decoded}") 
            return resp_decoded 
        else:
            err = f"ERROR:WORKER_{w_id}_TIMEOUT"
            print(err)
            return err

# --- Interface Modes ---

def run_network_mode(processor):
    HOST, PORT = '0.0.0.0', 5000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[*] Network Mode: Listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"[*] PC Connected: {addr}")
                # Buffered read/write for socket stability
                sock_file = conn.makefile('r', encoding='utf-8')
                out_file = conn.makefile('w', encoding='utf-8')
                while True:
                    line = sock_file.readline()
                    if not line: break
                    processor.dispatch(line, output_stream=out_file)
                out_file.close()

def run_serial_mode(processor):
    print("[*] Serial Mode: Local Terminal Active")
    # Show welcome screen on local start
    processor.master.show_welcome_screen()
    while True:
        try:
            line = input("\nMaster > ")
            processor.dispatch(line)
        except (KeyboardInterrupt, EOFError): 
            print("\nExiting...")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broccoli Master Node")
    parser.add_argument('--mode', choices=['network', 'serial'], default='network')
    args = parser.parse_args()

    # Hardware Config: Worker 0 on UART1 (/dev/ttyPS1)
    # You can add more workers here: [(0, "/dev/ttyPS1"), (1, "/dev/ttyPS2")]
    master = MasterNode([(0, "/dev/ttyPS1"), (1, "/dev/ttyUL1")])
    processor = CommandProcessor(master)

    if args.mode == 'network':
        run_network_mode(processor)
    else:
        run_serial_mode(processor)