import time
import re
import importlib
import sys

class TaskRegistry:
    def __init__(self, global_scope=None):
        self.tasks = {}
        self.task_metadata = {}
        # Use provided scope or fallback to current globals
        self.global_scope = global_scope if global_scope is not None else globals()
        print("[TaskRegistry] Initialized")
    
    def define(self, name, code):
        try:
            code = code.strip()
            # Handle Lambda directly
            if code.startswith('lambda'):
                local_scope = {}
                exec(f"{name} = {code}", self.global_scope, local_scope)
                self.tasks[name] = local_scope[name]
            
            # Wrap raw expressions into functions
            elif not code.startswith('def '):
                params = []
                for var in ['a', 'b', 'c', 'n', 'x', 'y', 'z']:
                    if re.search(r'\b' + var + r'\b', code):
                        params.append(var)
                
                param_list = ', '.join(params) if params else "*args, **kwargs"
                func_code = f"def {name}({param_list}):\n    return {code}\n"
                
                local_scope = {}
                exec(func_code, self.global_scope, local_scope)
                self.tasks[name] = local_scope[name]
            
            # Handle full 'def' blocks
            else:
                local_scope = {}
                exec(code, self.global_scope, local_scope)
                # Find whatever function was just defined
                func_name = code.split('def ')[1].split('(')[0].strip()
                self.tasks[name] = local_scope[func_name]

            # Register globally for recursion support
            self.global_scope[name] = self.tasks[name]
            self.task_metadata[name] = {'defined_at': time.time()}
            return f"OK:Task_{name}_defined"
        
        except Exception as e:
            return f"ERROR:Define_Failed_{str(e)}"

    def delete_task(self, name):
        if name in self.tasks:
            del self.tasks[name]
            if name in self.task_metadata: del self.task_metadata[name]
            return f"OK:Task_{name}_deleted"
        return f"ERROR:Task_{name}_not_found"

    def clear_all(self):
        count = len(self.tasks)
        self.tasks.clear()
        self.task_metadata.clear()
        return f"OK:Cleared_{count}_tasks"


class TaskExecutor:
    def __init__(self, dual_core_executor, global_scope=None):
        self.registry = TaskRegistry(global_scope)
        self.dual_core = dual_core_executor
        self.task_counter = 0

    def define_task(self, name, code):
        return self.registry.define(name, code)

    def execute(self, name, *args, core=None, **kwargs):
        """
        Unified Execution Logic: Handles Lambdas, Raw Expressions, 
        and Dynamic Module Imports (Uploaded Files).
        """
        if name not in self.registry.tasks:
            return ('error', f'task_{name}_not_defined')
        
        # 1. Pull the entry from the registry (string or function object)
        task_entry = self.registry.tasks[name]

        try:
            # 2. Convert Strings to Callables
            if isinstance(task_entry, str):
                # Strip stray quotes often added by Serial/Network transports
                task_entry = task_entry.strip().strip("'\"")

                # --- CASE A: Uploaded File (import_module pattern) ---
                if "import_module" in task_entry:
                    try:
                        # Parse "import_module('module_name'), 'func_name')"
                        module_name = task_entry.split("import_module('")[1].split("'")[0]
                        func_name = task_entry.split(", '")[1].split("'")[0]

                        # Force reload to ensure we aren't using stale bytecode from a previous upload
                        if module_name in sys.modules:
                            importlib.reload(sys.modules[module_name])
                        
                        module = importlib.import_module(module_name)
                        func_ptr = getattr(module, func_name)

                        # WRAPPER: This is the "Secret Sauce." It ensures the shim
                        # calls a fresh lambda that points to the module's function.
                        prepared_task = lambda _f=func_ptr *a, **k: _f(*a, **k)
                    except Exception as e:
                        return ('error', f'import_resolution_failed_{str(e)}')
                
                # --- CASE B: Standard Lambda or Expression ---
                else:
                    prepared_task = eval(task_entry)
            
            else:
                # Case C: It's already a function object
                prepared_task = task_entry

            # 3. Final Validation: Ensure we are sending a "Recipe" to the Shim
            if not callable(prepared_task):
                # If it's just a value (like 42), wrap it so func(*args) works in the shim
                val = prepared_task
                prepared_task = lambda *a, **k: val

        except Exception as e:
            return ('error', f'preparation_failed_{str(e)}')

        # 4. Task Identification & Core Assignment
        self.task_counter += 1
        task_id = f"{self.task_counter}" 
        target_core = core if core is not None else 1
        
        # 5. Hand-off to the DualCoreExecutor Shim
        try:
            # We pass the FUNCTION, not the RESULT.
            # The shim's result = func(*args) will now correctly return a value.
            self.dual_core.execute_async(task_id, prepared_task, args, kwargs, target_core)
            return ('success', task_id)
        except Exception as e:
            return ('error', f'dispatch_failed_{str(e)}')

    def get_result(self, task_id, timeout_ms=10):
        """Non-blocking result check for polling"""
        status, result = self.dual_core.get_result(task_id, timeout_ms)
        # If dual_core returns 'pending', we tell the master to try again later
        if status == 'pending':
            return ('WAIT', 'TASK_STILL_RUNNING')
        return (status.upper(), result)

    def list_tasks(self):
        tasks = list(self.registry.tasks.keys())
        return f"OK:{','.join(tasks)}" if tasks else "OK:EMPTY"

    def get_stats(self):
        qs = self.dual_core.get_queue_size()
        return f"OK:tasks={len(self.registry.tasks)};C0_Q={qs['core0']};C1_Q={qs['core1']}"