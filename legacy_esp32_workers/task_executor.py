# Dynamic Task Execution Engine for MicroPython
# Allows defining and executing Python code on-the-fly

import time


class TaskRegistry:
    """Registry for dynamically defined tasks"""
    
    def __init__(self, global_scope=None):
        self.tasks = {}
        self.task_metadata = {}
        self.global_scope = global_scope if global_scope is not None else globals()
        print("[TaskRegistry] Initialized")
    
    def define(self, name, code):
        """
        Define a new task from Python code string
        
        Args:
            name: Task name
            code: Python code as string
        
        Returns:
            Success/error message
        """
        try:
            # Create function from code
            # Check if it's a lambda expression
            if code.strip().startswith('lambda'):
                # Store lambda directly
                local_scope = {}
                exec(f"{name} = {code}", self.global_scope, local_scope)
                self.tasks[name] = local_scope[name]
                self.task_metadata[name] = {
                    'defined_at': time.time(),
                    'code': code
                }
                return f"OK:Task_{name}_defined"
            
            # Wrap code in function definition if not already a function
            if not code.strip().startswith('def '):
                # Detect common parameter names in expression (a, b, c, n, x, y, z)
                import re
                params = []
                for var in ['a', 'b', 'c', 'n', 'x', 'y', 'z']:
                    # Check if variable is used in code (as whole word)
                    if re.search(r'\b' + var + r'\b', code):
                        params.append(var)
                
                if params:
                    # Create function with detected parameters
                    param_list = ', '.join(params)
                    func_code = f"def {name}({param_list}):\n    return {code}\n"
                else:
                    # No parameters detected - use *args
                    func_code = f"def {name}(*args, **kwargs):\n    return {code}\n"
                code = func_code
            
            # Compile and execute to create function
            local_scope = {}
            exec(code, self.global_scope, local_scope)
            
            if name in local_scope:
                self.tasks[name] = local_scope[name]
                # Also add to globals so recursive functions can call themselves
                self.global_scope[name] = local_scope[name]
            else:
                # Extract function name from def statement
                func_name = code.split('def ')[1].split('(')[0].strip()
                self.tasks[name] = local_scope[func_name]
                # Also add to globals for recursion
                self.global_scope[name] = local_scope[func_name]
            
            self.task_metadata[name] = {
                'defined_at': time.time(),
                'code': code
            }
            
            return f"OK:Task_{name}_defined"
        
        except SyntaxError as e:
            return f"ERROR:SyntaxError_{e}"
        except Exception as e:
            return f"ERROR:{e}"
    
    def execute(self, name, *args, **kwargs):
        """
        Execute a defined task
        
        Args:
            name: Task name
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Tuple of (status, result)
        """
        if name not in self.tasks:
            return ('error', f'task_{name}_not_defined')
        
        try:
            result = self.tasks[name](*args, **kwargs)
            return ('success', result)
        except Exception as e:
            return ('error', str(e))
    
    def list_tasks(self):
        """Get list of all defined tasks"""
        return list(self.tasks.keys())
    
    def get_task_info(self, name):
        """Get metadata for a task"""
        if name in self.task_metadata:
            return self.task_metadata[name]
        return None
    
    def delete_task(self, name):
        """Remove a task from registry"""
        if name in self.tasks:
            del self.tasks[name]
            if name in self.task_metadata:
                del self.task_metadata[name]
            return f"OK:Task_{name}_deleted"
        return f"ERROR:Task_{name}_not_found"
    
    def clear_all(self):
        """Clear all tasks"""
        count = len(self.tasks)
        self.tasks.clear()
        self.task_metadata.clear()
        return f"OK:Cleared_{count}_tasks"


class TaskExecutor:
    """Main task execution engine combining registry and dual-core execution"""
    
    def __init__(self, dual_core_executor, global_scope=None):
        self.registry = TaskRegistry(global_scope)
        self.dual_core = dual_core_executor
        self.task_counter = 0
        print("[TaskExecutor] Initialized")
    
    def define_task(self, name, code):
        """Define a new task"""
        return self.registry.define(name, code)
    
    def execute_task(self, name, args=(), kwargs=None, core=None):
        """
        Execute task with optional core selection
        
        Args:
            name: Task name
            args: Positional arguments (tuple)
            kwargs: Keyword arguments (dict)
            core: 0, 1, or None for auto
        
        Returns:
            Result of task execution
        """
        if kwargs is None:
            kwargs = {}
        
        # Get task function from registry
        if name not in self.registry.tasks:
            return f"ERROR:Task_{name}_not_defined"
        
        task_func = self.registry.tasks[name]
        
        # Generate unique task ID
        self.task_counter += 1
        task_id = f"{name}_{self.task_counter}"
        
        # Execute on specified core
        status, result = self.dual_core.execute(task_id, task_func, args, kwargs, core)
        
        if status == 'success':
            return f"OK:{result}"
        else:
            return f"ERROR:{result}"
    
    def execute_task_async(self, name, args=(), kwargs=None, core=1):
        """Execute task asynchronously"""
        if kwargs is None:
            kwargs = {}
        
        if name not in self.registry.tasks:
            return f"ERROR:Task_{name}_not_defined"
        
        task_func = self.registry.tasks[name]
        self.task_counter += 1
        task_id = f"{name}_{self.task_counter}"
        
        self.dual_core.execute_async(task_id, task_func, args, kwargs, core)
        return f"OK:TaskID_{task_id}"
    
    def get_result(self, task_id, timeout_ms=5000):
        """Get result of async task"""
        status, result = self.dual_core.get_result(task_id, timeout_ms)
        if status == 'success':
            return f"OK:{result}"
        else:
            return f"ERROR:{result}"
    
    def list_tasks(self):
        """List all defined tasks"""
        tasks = self.registry.list_tasks()
        return f"OK:{','.join(tasks)}"
    
    def get_stats(self):
        """Get execution statistics"""
        queue_sizes = self.dual_core.get_queue_size()
        task_count = len(self.registry.tasks)
        
        return f"OK:tasks={task_count};core0_queue={queue_sizes['core0']};core1_queue={queue_sizes['core1']}"
