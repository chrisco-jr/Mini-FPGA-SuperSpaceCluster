import serial
import socket
import time
import json
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

    def submit(self, name: str, *args, worker: int = 0) -> str:
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
            task_id (str): The ID returned by submit().
            wait (bool): If True, blocks until the result is ready.
            timeout (float): Maximum time to wait if wait=True.

        Returns:
            Any: The task result (JSON decoded if applicable), or None if pending.
        """
        start_time = time.time()
        while True:
            response = self._send_raw(f"GET_RES:{task_id}")
            if response.startswith("OK:RESULT:"):
                data = response.split(':', 2)[-1]
                try: return json.loads(data)
                except: return data
            
            if not wait or (time.time() - start_time > timeout):
                return None
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
        tids = [self.submit(s.task, *s.args, worker=s.worker) for s in signatures]
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
            tid = self.submit(s.task, *args, worker=s.worker)
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
    # FILE & SYSTEM MANAGEMENT
    # ============================================================

    def upload_code(self, filename: str, code: str, worker: int = 0) -> str:
        """
        Uploads source code or data to a specific worker's filesystem.

        Args:
            filename (str): The remote filename.
            code (str): The raw string content of the file.
            worker (int): Target worker ID.

        Returns:
            str: Master node status response.
        """
        return self._send_raw(f"UPLOADW:{worker}:{filename}:{code}")

    def list_tasks(self, worker: int = 0) -> List[str]:
        """Returns a list of available tasks/files on a specific worker."""
        res = self._send_raw(f"LISTW:{worker}")
        return res.replace("OK:FILES:", "").split(",") if "OK:FILES:" in res else []


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
