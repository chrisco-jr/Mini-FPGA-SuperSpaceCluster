# dual_core_linux.py
# Linux-compatible DualCoreExecutor for PYNQ / PetaLinux
# API-compatible with ESP32 version

import threading
import time


class DualCoreExecutor:
    """Linux-compatible dual-core executor (shim for ESP32 version)"""

    def __init__(self):
        self.core0_queue = []
        self.core1_queue = []
        self.results = {}
        self.lock = threading.Lock()
        self.core1_running = False

        # Start worker thread to simulate "core1"
        self.start_core1_worker()

        print("[DualCore-Linux] Executor initialized")

    # ---------------------------------------------------------
    # Worker Thread (Simulated Core 1)
    # ---------------------------------------------------------

    def start_core1_worker(self):
        if not self.core1_running:
            t = threading.Thread(target=self._core1_worker, daemon=True)
            t.start()
            self.core1_running = True
            print("[DualCore-Linux] Core 1 worker started")

    def _core1_worker(self):
        while True:
            task = None

            with self.lock:
                if self.core1_queue:
                    task = self.core1_queue.pop(0)

            if task:
                task_id, func, args, kwargs = task
                try:
                    # 1. Primary Execution
                    result = func(*args, **kwargs)

                    # 2. THE FIX: Recursive Resolution
                    # If the result is still a function/method (and not a class type),
                    # call it again. This handles complex getattr/importlib wrappers.
                    # We use a loop in case there are multiple layers of wrapping.
                    max_depth = 5
                    while callable(result) and not isinstance(result, type) and max_depth > 0:
                        # If it's a zero-arg wrapper, call it. 
                        # If it needs the same args again, we pass them.
                        try:
                            result = result()
                        except TypeError:
                            result = result(*args, **kwargs)
                        max_depth -= 1

                    # 3. Store the final "unwrapped" value
                    with self.lock:
                        self.results[task_id] = ('success', result)
                        
                except Exception as e:
                    with self.lock:
                        # Provide more context in the error if execution fails
                        self.results[task_id] = ('error', f"ExecError: {str(e)}")
            else:
                # High-frequency polling for the Zynq's ARM cores
                time.sleep(0.001)

    # ---------------------------------------------------------
    # Synchronous Execution
    # ---------------------------------------------------------

    def execute(self, task_id, func, args=(), kwargs=None, core=None):
        """
        Execute function synchronously.
        core parameter is accepted for compatibility but not bound.
        """
        if kwargs is None:
            kwargs = {}

        # Simulate core selection behavior
        if core == 1:
            # Queue to simulated core1 worker and wait
            with self.lock:
                self.core1_queue.append((task_id, func, args, kwargs))

            return self._wait_for_result(task_id, timeout=5)

        else:
            # core == 0 or None → execute immediately
            try:
                result = func(*args, **kwargs)
                return ('success', result)
            except Exception as e:
                return ('error', str(e))

    # ---------------------------------------------------------
    # Asynchronous Execution
    # ---------------------------------------------------------

    def execute_async(self, task_id, func, args=(), kwargs=None, core=1):
        """
        Non-blocking execution.
        """
        if kwargs is None:
            kwargs = {}

        if core == 1:
            with self.lock:
                self.core1_queue.append((task_id, func, args, kwargs))
        else:
            t = threading.Thread(
                target=self._execute_and_store,
                args=(task_id, func, args, kwargs),
                daemon=True
            )
            t.start()

        return task_id

    def _execute_and_store(self, task_id, func, args, kwargs):
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.results[task_id] = ('success', result)
        except Exception as e:
            with self.lock:
                self.results[task_id] = ('error', str(e))

    # ---------------------------------------------------------
    # Result Handling
    # ---------------------------------------------------------

    def _wait_for_result(self, task_id, timeout=5):
        start = time.time()

        while (time.time() - start) < timeout:
            with self.lock:
                if task_id in self.results:
                    return self.results.pop(task_id)
            time.sleep(0.05)

        return ('error', 'timeout')

    def get_result(self, task_id, timeout_ms=5000):
        timeout = timeout_ms / 1000.0
        return self._wait_for_result(task_id, timeout)

    # ---------------------------------------------------------
    # Stats
    # ---------------------------------------------------------

    def get_queue_size(self):
        with self.lock:
            return {
                'core0': 0,  # Not actually queued in Linux
                'core1': len(self.core1_queue),
                'pending_results': len(self.results)
            }
