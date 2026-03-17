# Dual-Core Task Execution for MicroPython
# Uses _thread module for parallel execution on ESP32 cores

import _thread
import time


class DualCoreExecutor:
    """Manages task execution across ESP32's two cores"""
    
    def __init__(self):
        self.core0_queue = []
        self.core1_queue = []
        self.results = {}
        self.lock = _thread.allocate_lock()
        self.core1_running = False
        print("[DualCore] Executor initialized")
    
    def start_core1_worker(self):
        """Start worker thread on Core 1"""
        if not self.core1_running:
            _thread.start_new_thread(self._core1_worker, ())
            self.core1_running = True
            print("[DualCore] Core 1 worker started")
    
    def _core1_worker(self):
        """Worker loop running on Core 1"""
        while True:
            task = None
            
            with self.lock:
                if self.core1_queue:
                    task = self.core1_queue.pop(0)
            
            if task:
                task_id, func, args, kwargs = task
                try:
                    result = func(*args, **kwargs)
                    with self.lock:
                        self.results[task_id] = ('success', result)
                except Exception as e:
                    with self.lock:
                        self.results[task_id] = ('error', str(e))
            else:
                time.sleep_ms(10)
    
    def execute(self, task_id, func, args=(), kwargs=None, core=None):
        """
        Execute function on specified core
        
        Args:
            task_id: Unique identifier for this task
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            core: 0 or 1 for specific core, None for auto
        
        Returns:
            Result of function execution
        """
        if kwargs is None:
            kwargs = {}
        
        # Core 0 (main thread) - execute directly
        if core == 0 or core is None:
            try:
                result = func(*args, **kwargs)
                return ('success', result)
            except Exception as e:
                return ('error', str(e))
        
        # Core 1 - queue for worker thread
        elif core == 1:
            with self.lock:
                self.core1_queue.append((task_id, func, args, kwargs))
            
            # Wait for result
            timeout = 50  # 5 seconds
            for _ in range(timeout):
                with self.lock:
                    if task_id in self.results:
                        result = self.results.pop(task_id)
                        return result
                time.sleep_ms(100)
            
            return ('error', 'timeout')
        
        else:
            return ('error', f'invalid_core_{core}')
    
    def execute_async(self, task_id, func, args=(), kwargs=None, core=1):
        """
        Execute function asynchronously on specified core (non-blocking)
        
        Returns:
            task_id for later result retrieval
        """
        if kwargs is None:
            kwargs = {}
        
        with self.lock:
            if core == 1:
                self.core1_queue.append((task_id, func, args, kwargs))
            else:
                # Core 0 async - execute in new thread
                _thread.start_new_thread(self._execute_and_store, 
                                        (task_id, func, args, kwargs))
        
        return task_id
    
    def _execute_and_store(self, task_id, func, args, kwargs):
        """Helper to execute and store result"""
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.results[task_id] = ('success', result)
        except Exception as e:
            with self.lock:
                self.results[task_id] = ('error', str(e))
    
    def get_result(self, task_id, timeout_ms=5000):
        """
        Get result for async task
        
        Args:
            task_id: Task identifier
            timeout_ms: Maximum wait time in milliseconds
        
        Returns:
            Tuple of (status, result) or None if timeout
        """
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            with self.lock:
                if task_id in self.results:
                    return self.results.pop(task_id)
            time.sleep_ms(100)
        
        return ('error', 'timeout')
    
    def get_queue_size(self):
        """Get current queue sizes for both cores"""
        with self.lock:
            return {
                'core0': len(self.core0_queue),
                'core1': len(self.core1_queue),
                'pending_results': len(self.results)
            }
