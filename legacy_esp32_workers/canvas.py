# Canvas Primitives for MicroPython
# group, chain, chord for task orchestration (Celery-like)

import time


class AsyncResult:
    """Async result handle for task execution"""
    
    def __init__(self, task_id, executor):
        self.task_id = task_id
        self.executor = executor
        self._result = None
        self._ready = False
    
    def get(self, timeout_ms=5000):
        """Block until result is ready"""
        if self._ready:
            return self._result
        
        status, result = self.executor.dual_core.get_result(self.task_id, timeout_ms)
        if status == 'success':
            self._result = result
            self._ready = True
            return result
        else:
            raise Exception(f"Task failed: {result}")
    
    def ready(self):
        """Check if result is ready"""
        return self._ready


class TaskSignature:
    """Task signature for deferred execution"""
    
    def __init__(self, executor, task_name, *args, **kwargs):
        self.executor = executor
        self.task_name = task_name
        self.args = args
        self.kwargs = kwargs
        self.core = kwargs.pop('core', None) if kwargs else None
    
    def apply_async(self, core=None):
        """Execute task asynchronously"""
        exec_core = core if core is not None else self.core
        
        # Generate task ID and execute
        self.executor.task_counter += 1
        task_id = f"{self.task_name}_{self.executor.task_counter}"
        
        task_func = self.executor.registry.tasks[self.task_name]
        self.executor.dual_core.execute_async(task_id, task_func, 
                                               self.args, self.kwargs, exec_core)
        
        return AsyncResult(task_id, self.executor)
    
    def delay(self, *args, **kwargs):
        """Shortcut for apply_async"""
        # Merge args
        final_args = self.args + args
        final_kwargs = dict(self.kwargs)
        final_kwargs.update(kwargs)
        
        sig = TaskSignature(self.executor, self.task_name, *final_args, **final_kwargs)
        return sig.apply_async()


class group:
    """Execute tasks in parallel"""
    
    def __init__(self, signatures):
        self.signatures = signatures
        self.async_results = None
    
    def apply_async(self):
        """Execute all tasks in parallel"""
        self.async_results = [sig.apply_async() for sig in self.signatures]
        return self
    
    def get(self, timeout_ms=5000):
        """Get all results"""
        if self.async_results is None:
            self.apply_async()
        
        return [ar.get(timeout_ms) for ar in self.async_results]


class chain:
    """Execute tasks sequentially, passing results"""
    
    def __init__(self, *signatures):
        self.signatures = signatures
    
    def apply_async(self):
        """Execute chain"""
        result = None
        
        for sig in self.signatures:
            if result is not None:
                # Pass previous result as first argument
                new_sig = TaskSignature(sig.executor, sig.task_name, 
                                       result, *sig.args, **sig.kwargs)
                ar = new_sig.apply_async(sig.core)
            else:
                ar = sig.apply_async()
            
            result = ar.get()
        
        # Return async result for last task
        class ChainResult:
            def __init__(self, result):
                self._result = result
            def get(self, timeout_ms=5000):
                return self._result
        
        return ChainResult(result)
    
    def get(self, timeout_ms=5000):
        """Execute and get final result"""
        ar = self.apply_async()
        return ar.get(timeout_ms)


class chord:
    """Execute group and pass results to callback"""
    
    def __init__(self, header_signatures):
        self.header = group(header_signatures)
    
    def __call__(self, callback_sig):
        """Execute header group and pass results to callback"""
        # Execute header group
        results = self.header.get()
        
        # Execute callback with results
        callback_sig.args = (results,) + callback_sig.args
        return callback_sig.apply_async()
    
    def get(self, callback_sig, timeout_ms=5000):
        """Execute and get result"""
        ar = self(callback_sig)
        return ar.get(timeout_ms)


class Task:
    """Task decorator for registering functions"""
    
    def __init__(self, executor):
        self.executor = executor
    
    def __call__(self, func):
        """Decorator to register function as task"""
        # Register function in task registry
        task_name = func.__name__
        
        # Get function source code
        import inspect
        try:
            source = inspect.getsource(func)
            self.executor.registry.define(task_name, source)
        except:
            # If can't get source, register directly
            self.executor.registry.tasks[task_name] = func
        
        # Return wrapper with task methods
        class TaskWrapper:
            def __init__(self, name, executor, func):
                self.name = name
                self.executor = executor
                self.func = func
            
            def __call__(self, *args, **kwargs):
                """Direct execution"""
                return self.func(*args, **kwargs)
            
            def s(self, *args, **kwargs):
                """Create signature"""
                return TaskSignature(self.executor, self.name, *args, **kwargs)
            
            def delay(self, *args, **kwargs):
                """Execute asynchronously"""
                return self.s(*args, **kwargs).apply_async()
            
            def apply_async(self, *args, **kwargs):
                """Execute asynchronously"""
                return self.s(*args, **kwargs).apply_async()
        
        return TaskWrapper(task_name, self.executor, func)


def create_canvas_api(task_executor):
    """Create Canvas API with task executor"""
    
    class CanvasAPI:
        def __init__(self, executor):
            self.executor = executor
            self.Task = Task(executor)
        
        def group(self, signatures):
            return group(signatures)
        
        def chain(self, *signatures):
            return chain(*signatures)
        
        def chord(self, header_signatures):
            return chord(header_signatures)
        
        def signature(self, task_name, *args, **kwargs):
            """Create task signature"""
            return TaskSignature(self.executor, task_name, *args, **kwargs)
        
        def execute_primitive(self, primitive_type, data):
            """Execute Canvas primitive (GROUP, CHAIN, CHORD) from JSON data"""
            try:
                if primitive_type == "GROUP":
                    # data = [{"task": "name", "args": [...], "kwargs": {...}, "core": N}, ...]
                    results = []
                    for sig_data in data:
                        task_name = sig_data["task"]
                        args = tuple(sig_data.get("args", []))
                        kwargs = sig_data.get("kwargs", {})
                        core = sig_data.get("core")
                        
                        result_str = self.executor.execute_task(task_name, args, kwargs, core)
                        # execute_task returns "OK:result" or "ERROR:msg"
                        if result_str.startswith("OK:"):
                            results.append(result_str[3:])  # Strip "OK:"
                        else:
                            results.append(result_str)  # Keep error as-is
                    return ("success", results)
                
                elif primitive_type == "CHAIN":
                    # data = [sig1, sig2, ...]
                    result = None
                    for sig_data in data:
                        task_name = sig_data["task"]
                        args = tuple(sig_data.get("args", []))
                        kwargs = sig_data.get("kwargs", {})
                        core = sig_data.get("core")
                        
                        # Pass previous result as first arg
                        if result is not None:
                            # Try to convert result to int/float if it's a number string
                            try:
                                if isinstance(result, str):
                                    if '.' in result:
                                        result = float(result)
                                    else:
                                        result = int(result)
                            except (ValueError, TypeError):
                                pass  # Keep as string if conversion fails
                            args = (result,) + args
                        
                        result_str = self.executor.execute_task(task_name, args, kwargs, core)
                        # execute_task returns "OK:result" or "ERROR:msg"
                        if result_str.startswith("OK:"):
                            result = result_str[3:]  # Strip "OK:" and use as next input
                        else:
                            return ("error", f"Chain failed at {task_name}: {result_str}")
                    return ("success", result)
                
                elif primitive_type == "CHORD":
                    # data = {"header": [sig1, sig2, ...], "callback": sig}
                    header_results = []
                    for sig_data in data["header"]:
                        task_name = sig_data["task"]
                        args = tuple(sig_data.get("args", []))
                        kwargs = sig_data.get("kwargs", {})
                        core = sig_data.get("core")
                        
                        result_str = self.executor.execute_task(task_name, args, kwargs, core)
                        # execute_task returns "OK:result" or "ERROR:msg"
                        if result_str.startswith("OK:"):
                            result = result_str[3:]
                            # Try to convert to int/float
                            try:
                                if isinstance(result, str):
                                    if '.' in result:
                                        result = float(result)
                                    else:
                                        result = int(result)
                            except (ValueError, TypeError):
                                pass
                            header_results.append(result)
                        else:
                            header_results.append(result_str)
                    
                    # Execute callback with results
                    callback = data["callback"]
                    callback_args = (header_results,)
                    callback_kwargs = callback.get("kwargs", {})
                    callback_core = callback.get("core")
                    
                    final_result_str = self.executor.execute_task(
                        callback["task"], callback_args, callback_kwargs, callback_core
                    )
                    
                    # Return the result
                    if final_result_str.startswith("OK:"):
                        return ("success", final_result_str[3:])
                    else:
                        return ("error", final_result_str)
                
                else:
                    return ("error", f"Unknown primitive: {primitive_type}")
            
            except Exception as e:
                return ("error", f"Canvas execution failed: {e}")
    
    return CanvasAPI(task_executor)
