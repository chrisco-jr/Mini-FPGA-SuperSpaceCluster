import serial
import socket
import time
import json
import base64
import ast
from typing import Any, Optional, List, Tuple, Dict, Union
from dataclasses import dataclass

@dataclass
class Sig:
    """
    Task Signature (Sig) object for orchestration.
    """
    task: str
    args: Tuple[Any, ...] = ()
    worker: int = 0

class BroccoliCluster:
    """
    The BroccoliCluster SDK for PYNQ-Z2 SoC Clusters.
    Compatible with Tier 1 Network & Benchmark Suites.
    """

    def __init__(self, target: str, mode: str = 'network', port: int = 5000, timeout: float = 5.0):
        self.target = target
        self.mode = mode
        self.port = port
        self.timeout = timeout
        self.conn = None
        self.connected = False

    def connect(self):
        """Establishes connection to the PetaLinux Master Node."""
        try:
            if self.mode == 'network':
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.settimeout(self.timeout)
                self.conn.connect((self.target, self.port))
                self.conn_file = self.conn.makefile('rw', encoding='utf-8')
            else:
                self.conn = serial.Serial(self.target, 115200, timeout=self.timeout)
            
            self.connected = True
            print(f">> Connected to Broccoli Master ({self.mode}) at {self.target}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

    def _send_raw(self, cmd: str) -> str:
        """Internal transport method."""
        if not self.connected: raise RuntimeError("Connect first.")
        if self.mode == 'network':
            self.conn_file.write(f"{cmd}\n")
            self.conn_file.flush()
            return self.conn_file.readline().strip()
        else:
            self.conn.write(f"{cmd}\n".encode())
            return self.conn.readline().decode().strip()
    
    def __getattr__(self, name):
        """Sugar: cluster.my_task(arg1, worker=0) -> returns data only."""
        def wrapper(*args, **kwargs):
            worker = kwargs.pop('worker', 0)
            # Uses the helper to return clean data
            return self.execute_and_wait(name, *args, worker=worker)
        return wrapper

    # ============================================================
    # CORE ASYNC OPERATIONS
    # ============================================================
    
    def define_task(self, name: str, code: str, worker: int = 0):
        """Registers a Python expression or lambda in the Worker's TaskRegistry."""
        command = f"DEFINEW:{worker}:{name}:{code}"
        response = self._send_raw(command)
        if not response.startswith('OK:'):
            raise RuntimeError(f"Task definition failed: {response}")
        print(f">> Task '{name}' defined on Worker {worker}")
    
    def execute(self, name: str, *args, worker: int = 0) -> str:
        """Submits task and returns a unique Task ID (TID)."""
        args_str = ",".join(map(str, args))
        response = self._send_raw(f"EXECW:{worker}:{name}:{args_str}")
        if response.startswith("OK:SUBMITTED:"):
            return int(response.split(':')[-1].strip())
        raise RuntimeError(f"Task submission failed: {response}")
    
    def execute_and_wait(self, name: str, *args, worker: int = 0, timeout: float = 15.0) -> Any:
        """Helper: Combined Execute + Poll. Returns DATA only."""
        tid = self.execute(name, *args, worker=worker)
        result, _ = self.get_result(tid, wait=True, timeout=timeout)
        return result

    def get_result(self, task_id: str, wait: bool = True, timeout: float = 15.0) -> Tuple[Optional[Any], int]:
        """Polls for result and returns (data, poll_count)."""
        start_time = time.time()
        polls = 0
        while True:
            polls += 1
            response = self._send_raw(f"GET_RES:{task_id}")
            
            if response.startswith("OK:RESULT:"):
                # Extract everything after "OK:RESULT:"
                data_str = response.replace("OK:RESULT:", "", 1)
                
                # Try JSON first (standard)
                try:
                    return json.loads(data_str), polls
                except:
                    # Fallback to AST (preserves Tuples and Python types)
                    try:
                        return ast.literal_eval(data_str), polls
                    except:
                        # Final fallback: raw string
                        return data_str, polls

            if response.startswith("ERROR:"):
                err_msg = response.replace("ERROR:", "", 1)
        
                # Check if it's just a transient timeout
                if "timeout" in err_msg.lower():
                    if not wait or (time.time() - start_time > timeout):
                        return None, polls
                    # If we are waiting, we just continue the loop and sleep
                else:
                    # HARD FAILURE: Raise immediately to stop the polling spam!
                    raise RuntimeError(err_msg)
            
            time.sleep(0.15)

    # ============================================================
    # ORCHESTRATION (Sigs, Groups, Chains)
    # ============================================================

    def sig(self, task: str, *args, worker: int = 0) -> Sig:
        return Sig(task, args, worker)

    def group(self, signatures: List[Sig]) -> List[Any]:
        tids = [self.execute(s.task, *s.args, worker=s.worker) for s in signatures]
        return [self.get_result(tid, wait=True)[0] for tid in tids]

    def chain(self, signatures: List[Sig]) -> Any:
        """Sequential pipeline: Handles single values and multi-value unpacking."""
        res = None
        for i, s in enumerate(signatures):
            if i == 0:
                current_args = s.args
            else:
                # SMART UNPACK: If previous task returned (A, B), 
                # next task gets A, B as separate positional args.
                if isinstance(res, (tuple, list)):
                    current_args = tuple(res) + s.args
                else:
                    current_args = (res,) + s.args
            
            tid = self.execute(s.task, *current_args, worker=s.worker)
            res, _ = self.get_result(tid, wait=True)
        return res

    def chord(self, header: List[Sig], callback: Sig) -> Any:
        """
        Barrier: Executes a group, then 'Zips' the results into a 
        structured list for the final callback.
        """
        # 1. Map Phase (Parallel)
        results = self.group(header)
        
        # 2. Reduce Phase (The Finalizer)
        # We pass the 'results' list (the zip of all worker outputs) 
        # as the first argument to the callback.
        callback_args = (results,) + callback.args
        tid = self.execute(callback.task, *callback_args, worker=callback.worker)
        
        final_res, _ = self.get_result(tid, wait=True)
        return final_res

    # ============================================================
    # CONCISE FILE & TASK MANAGEMENT
    # ============================================================

    def upload_file(self, filename: str, code: str, worker: int = 0) -> str:
        """Transfers raw data to PetaLinux via Base64."""
        encoded_data = base64.b64encode(code.encode("utf-8")).decode("ascii")
        return self._send_raw(f"UPLOADW:{worker}:{filename}:{encoded_data}")
    
    def upload_python_as_task(self, task_name, python_code, worker=0):
        """Uploads .py file and registers its 'result' function as a task."""
        self.upload_file(f"{task_name}.py", python_code, worker=worker)
        logic = f"getattr(__import__('importlib').import_module('{task_name}'), 'result')"
        return self.define_task(task_name, logic, worker=worker)

    def remove_task(self, name: str, worker: int = 0):
        """Purges task from RAM and deletes associated .py file from disk."""
        # Use a one-off expression to delete the file
        cleanup_expr = f"__import__('os').remove('{name}.py') if __import__('os').path.exists('{name}.py') else 'OK'"
        self.define_task("_tmp_del", cleanup_expr, worker=worker)
        tid = self.execute("_tmp_del", worker=worker)
        self.get_result(tid, timeout=2.0) # Confirm disk write

        # Remove both from registry
        self._send_raw(f"DELETEW:{worker}:{name}")
        self._send_raw(f"DELETEW:{worker}:_tmp_del")
        return f"OK:Purged_{name}"

    def list_tasks(self, worker: int = 0) -> List[str]:
        """Returns list of registered tasks on a specific worker."""
        res = self._send_raw(f"LISTW:{worker}")
        if "OK:FILES:" in res:
            return [t for t in res.replace("OK:FILES:", "").split(",") if t.strip()]
        return []

    def clear_all_tasks(self, worker: int = 0):
        """Resets a worker to a factory-clean state."""
        tasks = self.list_tasks(worker=worker)
        for task_name in tasks:
            self.remove_task(task_name, worker=worker)
        self._send_raw(f"CLEARW:{worker}")
        return f"OK:Worker_{worker}_Clear_Complete"

    # ============================================================
    # UTILITY & TELEMETRY
    # ============================================================

    def stats(self):
        """Master node network/packet stats."""
        return self._send_raw("STATS")

    def reset_stats(self) -> str:
        """Zeroes out Master node packet counters."""
        return self._send_raw("RESET_STATS")
    
    def get_system_info(self, worker: int = 0):
        """Pulls SoC health (XADC Temp/Voltages) and PetaLinux status."""
        return self._send_raw(f"SYS_INFOW:{worker}")
    
    def broadcast_action(self, action_type: str, num_workers: int):
        """
        Uses existing SDK logic to perform cluster-wide operations.
        """
        results = []
        for w in range(num_workers):
            if action_type == "clear":
                # Leverages your logic: list_tasks -> remove_task -> CLEARW
                resp = self.clear_all_tasks(worker=w)
            elif action_type == "telemetry":
                # Leverages your direct SYS_INFOW call
                resp = self.get_system_info(worker=w)
            else:
                resp = "ERROR:Unknown_Broadcast_Action"
            
            results.append(resp)
        return results    
    
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn: self.conn.close()
      