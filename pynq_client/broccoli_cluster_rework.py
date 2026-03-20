import serial
import socket
import time
import json
import base64
from typing import Any, Optional, List, Tuple, Dict, Union
from dataclasses import dataclass

@dataclass
class Sig:
    """
    Task Signature (Sig) object.
    
    Encapsulates a task name and its associated arguments for delayed 
    or orchestrated execution within the cluster.
    
    Attributes:
        task (str): The name of the registered task on the worker.
        args (tuple): Positional arguments to pass to the task.
        worker (int): The target worker ID (default is 0).
    """
    task: str
    args: Tuple[Any, ...] = ()
    worker: int = 0

class BroccoliCluster:
    """
    The BroccoliCluster SDK for PYNQ-Z2 SoC Clusters.
    
    This client manages communication between a PC (Client) and a PetaLinux 
    Master node. It supports asynchronous task submission, results polling, 
    and complex orchestration patterns like groups, chains, and chords.
    """

    def __init__(self, target: str, mode: str = 'network', port: int = 5000, timeout: float = 2.0):
        """
        Initializes the cluster client.

        Args:
            target (str): IP address (network mode) or COM/tty port (serial mode).
            mode (str): Transport layer, either 'network' or 'serial'.
            port (int): TCP port for the Master node (default 5000).
            timeout (float): Response timeout in seconds.
        """
        self.target = target
        self.mode = mode
        self.port = port
        self.timeout = timeout
        self.conn = None
        self.connected = False

    def connect(self):
        """
        Establishes a connection to the Master Node.
        
        Raises:
            ConnectionError: If the target is unreachable.
        """
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
            raise ConnectionError(f"Failed to connect to cluster: {e}")

    def _send_raw(self, cmd: str) -> str:
        """
        Internal method to transmit strings and receive line-buffered responses.
        
        Args:
            cmd (str): The raw command string.
            
        Returns:
            str: The stripped response line from the Master.
        """
        if not self.connected: 
            raise RuntimeError("Cluster not connected. Call connect() first.")
        
        if self.mode == 'network':
            self.conn_file.write(f"{cmd}\n")
            self.conn_file.flush()
            return self.conn_file.readline().strip()
        else:
            self.conn.write(f"{cmd}\n".encode())
            return self.conn.readline().decode().strip()

    # ============================================================
    # CORE TASK OPERATIONS
    # ============================================================
    def define_task(self, name: str, code: str, worker: int = 0):
        """
        Define a new task on the cluster.
    
        Args:
            name: Task name (e.g., 'add', 'multiply')
            code: Python-like expression (e.g., 'x + y', 'x * y')
            worker: Which worker to define on (0, 1, or None for worker 0)
    
        Example:
            cluster.define_task('add', 'x + y')
            cluster.define_task('square', 'x * x', worker=1)
        """
        # Using DEFINEW:{worker} consistently across all worker IDs
        command = f"DEFINEW:{worker}:{name}:{code}"
        response = self._send_raw(command)
    
        if not response.startswith('OK:DEFINED:'):
            print(f"✗ Failed to define task: {response}")
            raise RuntimeError(f"Task definition failed: {response}")

        print(f">> Task '{name}' defined on Worker {worker}")
    
    def execute(self, name: str, *args, worker: int = 0) -> str:
        """
        Asynchronously submits a task to a worker.
        
        Args:
            name (str): The task name to execute.
            *args: Variable arguments for the task.
            worker (int): Target worker ID.

        Returns:
            str: A unique Task ID for polling results.
            
        Example:
            task_id = cluster.submit("add", 5, 10, worker=1)
        """
        args_str = ",".join(map(str, args))
        response = self._send_raw(f"EXECW:{worker}:{name}:{args_str}")
        
        if response.startswith("OK:SUBMITTED:"):
            return response.split(':')[-1]
        raise RuntimeError(f"Task submission failed: {response}")
              
    def get_result(self, task_id: str, wait: bool = True, timeout: float = 10.0) -> Optional[Any]:
        """
        Polls for the result of a submitted task.

        Args:
            task_id (str): The ID returned by execute() or submit().
            wait (bool): If True, blocks until the result is ready.
            timeout (float): Maximum time to wait if wait=True.

        Returns:
            Any: The task result (JSON decoded if applicable), or None if pending/timeout.
        
        Raises:
            RuntimeError: If the Master node returns an explicit error for the task.
        """
        start_time = time.time()
        
        while True:
            response = self._send_raw(f"GET_RES:{task_id}")
            
            # Case 1: Task completed successfully
            if response.startswith("OK:RESULT:"):
                # Use maxsplit=2 to protect colons within the JSON data
                _, _, data = response.split(':', 2)
                
                if not data:
                    return None
                
                try:
                    # Attempt to parse structured data (lists, dicts, etc.)
                    return json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    # Fallback: Return as raw string if not valid JSON
                    return data

            # Case 2: Remote execution failed
            if response.startswith("ERR:"):
                raise RuntimeError(f"Remote execution failed for Task {task_id}: {response}")

            # Case 3: Task is still running or pending
            if not wait or (time.time() - start_time > timeout):
                return None
            
            # Prevent CPU pegging during polling
            time.sleep(0.1)

    # ============================================================
    # ORCHESTRATION (GROUP, CHAIN, CHORD)
    # ============================================================

    def sig(self, task: str, *args, worker: int = 0) -> Sig:
        """Creates a task signature for orchestration."""
        return Sig(task=task, args=args, worker=worker)

    def group(self, signatures: List[Sig]) -> List[Any]:
        """
        Executes a collection of tasks in parallel across workers.

        Args:
            signatures (list): A list of Sig objects.

        Returns:
            list: The aggregated results of all tasks in the group.
        """
        tids = [self.execute(s.task, *s.args, worker=s.worker) for s in signatures]
        return [self.get_result(tid) for tid in tids]

    def chain(self, signatures: List[Sig]) -> Any:
        """
        Executes tasks sequentially, passing the result of one as the 
        input to the next.

        Args:
            signatures (list): List of Sig objects to pipeline.

        Returns:
            Any: The final result of the last task in the chain.
        """
        res = None
        for s in signatures:
            args = (res,) + s.args if res is not None else s.args
            tid = self.execute(s.task, *args, worker=s.worker)
            res = self.get_result(tid)
        return res

    def chord(self, header_sigs: List[Sig], callback_sig: Sig) -> Any:
        """
        Executes a group of tasks (header) and passes the result list 
        to a final task (callback).

        Args:
            header_sigs (list): List of tasks to run in parallel.
            callback_sig (Sig): The task that reduces the results.

        Returns:
            Any: The output of the callback task.
        """
        results = self.group(header_sigs)
        return self.chain([self.sig(callback_sig.task, results, worker=callback_sig.worker)])

    # ============================================================
    # FILE & TASK MANAGEMENT
    # ============================================================

    def upload_file(self, filename: str, data: str, worker: int = 0) -> str:
        """
        Uploads source code or data to a specific worker's filesystem.

        Args:
            filename (str): The remote filename.
            code (str): The raw string content of the file.
            worker (int): Target worker ID.

        Returns:
            str: Master node status response.
        """
        encoded_data = base64.b64encode(code.encode("utf-8")).decode("ascii")
        
        return self._send_raw(f"UPLOADW:{worker}:{filename}:{encoded_data}")
    
    def upload_python_as_task(self, task_name, python_code, worker=0):
        """
        Uses EXISTING commands to handle multiline code.
        No firmware changes required.
        """
        filename = f"{task_name}.py"
    
        # 1. Use your existing UPLOAD command
        # This puts the file on the PetaLinux Worker's disk
        self.upload_file(filename, python_code, worker=worker)
    
        # 2. Use your existing DEFINE command
        # We send a "side-effect" string. 
        # The Worker's TaskRegistry sees a string and stores it.
        # We use 'importlib' to ensure it refreshes even if the file changed.
        import_logic = f"getattr(__import__('importlib').import_module('{task_name}'), 'result', 1)"    

        return self.define_task(task_name, import_logic, worker=worker)

    def remove_file(self, filename: str, worker: int = 0):
        """
        FORCE REMOVE FILE:
        Directly deletes a file from the Worker's PetaLinux filesystem.
        Note: Use with caution!
        """
        temp_janitor = f"force_del_{int(time.time())}"
        
        print(f"[SDK] Force deleting '{filename}' from Worker {worker}...")

        # Construct the raw OS removal string
        # We use a f-string inside the logic to pass the filename
        cleanup_logic = f"__import__('os').remove('{filename}')"
        
        try:
            # 1. Define the temporary deletion task
            self.define_task(temp_janitor, cleanup_logic, worker=worker)
            
            # 2. Execute it (this performs the actual 'rm' on PetaLinux)
            result = self.execute(temp_janitor, worker=worker)
            
            # 3. Clean up the evidence from the Task Registry
            self._send_raw(f"DELETEW:{worker}:{temp_janitor}")
            
            return result
        except Exception as e:
            return f"ERROR:Cleanup_Failed_{e}"

    
    def list_tasks(self, worker: int = 0) -> List[str]:
        """Returns a list of available tasks/files on a specific worker."""
        res = self._send_raw(f"LISTW:{worker}")
        return res.replace("OK:FILES:", "").split(",") if "OK:FILES:" in res else []

    def remove_task(self, name: str, worker: int = 0):
        """
        Full Cleanup: Removes task from RAM and deletes file from Disk.
        Uses existing infrastructure (no firmware changes).
        """
        filename = f"{name}.py"
        janitor_name = f"janitor_{name}"

        print(f"[SDK] Cleaning up task '{name}' on Worker {worker}...")

        # 1. Disk Cleanup: Create a one-time task to delete the file
        # We use 'os.path.exists' to prevent an error if the file was already gone
        cleanup_logic = (
            f"__import__('os').remove('{filename}') "
            f"if __import__('os').path.exists('{filename}') else 'Already_Gone'"
        )
        
        # Define and run the Janitor
        self.define_task(janitor_name, cleanup_logic, worker=worker)
        self.execute(janitor_name, worker=worker)

        # 2. RAM Cleanup: Remove the actual task and the Janitor from the Registry
        # These call the 'delete_task' method already in your TaskRegistry
        self._send_raw(f"DELETEW:{worker}:{name}")
        self._send_raw(f"DELETEW:{worker}:{janitor_name}")

        return f"OK:Task_{name}_and_file_{filename}_removed"

    def clear_all_tasks(self, worker: int = 0):
        """
        Clears all tasks for a specific Worker by delegating to list_tasks 
        and remove_task for a thorough cleanup.
        """
        print(f"[SDK] Initiating Full Task Registry Clear on Worker {worker}...")
        
        # 1. Get the parsed list using our existing method
        tasks = self.list_tasks(worker=worker)

        if not tasks:
            print(f"[SDK] Worker {worker} Task Registry Already Clean.")
            # Still call CLEARW just to be safe/reset metadata on the Master
            self._send_raw(f"CLEARW:{worker}")
            return "OK:Already_Empty"

        # 2. Loop and Purge
        for task_name in tasks:
            # Reusing remove_task ensures disk + RAM are both cleaned
            self.remove_task(task_name, worker=worker)
            print(f"  - Purged: {task_name}")

        # 3. Final sweep for any metadata or non-file tasks
        self._send_raw(f"CLEARW:{worker}")

        return f"OK:Worker_{worker}_Task_Registry_Clear_complete"

    # ============================================================
    # UTILITY & TELEMETRY
    # ============================================================

    def stats(self):
        """
        Retrieves packet telemetry and health status from the Master Node.

        Returns:
            str: A formatted string containing TX/RX counts and worker status.
        """
        return self._send_raw("STATS")

    def reset_stats(self) -> str:
        """
        Resets the Master Node's packet counters and timing logs.
        Useful for clearing state before starting a new benchmark or mission.

        Returns:
            str: Master node confirmation ("OK:STATS_RESET").
        """
        response = self._send_raw("RESET_STATS")
        print(">> Cluster statistics have been zeroed out.")
        return response

    def help(self):
        """
        Triggers the interactive help menu on the Master Node.
        Useful for reminding the user of raw command syntax during 
        interactive sessions.
        """
        print(self._send_raw("HELP"))

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
