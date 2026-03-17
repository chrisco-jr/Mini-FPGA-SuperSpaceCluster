# worker_commands.py
import json
import os
import time

class WorkerProcessor:
    def __init__(self, task_executor, canvas, dual_core):
        self.task_executor = task_executor
        self.canvas = canvas
        self.dual_core = dual_core

    def dispatch(self, message):
        """Primary entry point for messages from Master"""
        if not message: return None
        
        if ':' in message:
            command, params = message.split(':', 1)
        else:
            command, params = message, ""
            
        return self.handle_command(command.strip(), params.strip())

    def handle_command(self, command, params):
        try:
            # --- Task Management ---
            if command == "DEFINE":
                parts = params.split(':', 1)
                return self.task_executor.define_task(parts[0], parts[1]) if len(parts) == 2 else "ERROR:Format"

            elif command == "EXEC":
                return self._handle_exec(params)

            elif command == "LIST" or command == "TASK_LIST":
                return self.task_executor.list_tasks()

            # --- Canvas Primitives ---
            elif command == "CANVAS":
                return self._handle_canvas(params)

            # --- System Monitoring ---
            elif command == "STATS":     return self.task_executor.get_stats()
            elif command == "SYS_INFO":  return f"OK:uname={os.uname().sysname}"
            elif command == "RAM_USAGE": return self._read_proc("/proc/meminfo")
            elif command == "CPU_USAGE": return self._read_proc("/proc/loadavg")
            elif command == "UPTIME":    return self._read_proc("/proc/uptime")
            elif command == "PING":      return "PONG"

            # --- File/System Operations ---
            elif command == "UPLOAD":
                return self._handle_upload(params)
            elif command == "RESET":
                os.system("reboot")
                return "OK:RESETTING"

            return f"ERROR:Unknown_command_{command}"

        except Exception as e:
            return f"ERROR:Processor_{e}"

    # --- Internal Helper Methods (Keep logic clean) ---
    def _handle_exec(self, params):
        try:
            parts = params.split(':')
            task_name = parts[0]
            core = None
            args_str = ""

            # 1. Routing & Argument Extraction
            # Format: EXEC:task_name:CORE:0:arg1,arg2
            if len(parts) > 1:
                if parts[1] == "CORE" and len(parts) > 2:
                    core = int(parts[2])
                    args_str = parts[3] if len(parts) > 3 else ""
                else:
                    # Format: EXEC:task_name:arg1,arg2
                    args_str = parts[1]

            # 2. Argument Parsing (Safe conversion)
            args = []
            if args_str:
                # Split by comma and attempt to convert to numeric types
                for a in args_str.split(','):
                    a = a.strip()
                    try:
                        # Convert to int or float if possible
                        if '.' in a:
                            args.append(float(a))
                        else:
                            args.append(int(a))
                    except ValueError:
                        # Keep as string if it's not a number
                        args.append(a.strip("'\""))

            # 3. Execution
            # Ensure we pass a tuple: tuple(args)
            result = self.task_executor.execute_task(task_name, tuple(args), {}, core)
            
            # Redundant check to prevent multiple prefixes
            str_res = str(result)
            # 1. If it's already an error, just pass it through
            if str_res.startswith("ERROR:"):
                return str_res
            
            # 2. If it's already an "OK:", don't add another one
            if str_res.startswith("OK:"):
                return str_res
            
            # 3. If it's a raw value (like 42), add the OK:
            return f"OK:{str_res}"

        except Exception as e:
            return f"ERROR:Exec_Handler_{e}"

    def _handle_canvas(self, params):
        parts = params.split(':', 1)
        if len(parts) != 2: return "ERROR:Format"
        p_type, data_json = parts
        status, result = self.canvas.execute_primitive(p_type, json.loads(data_json))
        return f"OK:{json.dumps(result)}" if status == "success" else f"ERROR:{result}"

    def _handle_upload(self, params):
        parts = params.split(':', 1)
        if len(parts) != 2: return "ERROR:Format"
        filename, content = parts
        with open(filename, 'w') as f: f.write(content)
        return f"OK:Uploaded_{filename}"

    def _read_proc(self, path):
        with open(path) as f: return f"OK:{f.read().strip()}"
