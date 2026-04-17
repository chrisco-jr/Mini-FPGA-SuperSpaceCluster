# worker_commands.py
import json
import os
import time
import base64
import sys

class WorkerProcessor:
    def __init__(self, task_executor, canvas, dual_core):
        self.task_executor = task_executor
        self.canvas = canvas
        self.dual_core = dual_core
        
        # The Registry: Maps Master commands to local handler methods
        self.handlers = {
            "DEFINE":    self._handle_define,
            "EXEC":      self._handle_exec,
            "GET_RES":   self._handle_get_res,
            "LIST":      self._handle_list,
            "TASK_LIST": self._handle_list,
            "CANVAS":    self._handle_canvas,
            "STATS":     self._handle_stats,
            "PING":      lambda p: "PONG",
            "SYS_INFO":  self._handle_sys_info,
            "UPLOAD":    self._handle_upload,
            "DELETE":    self._handle_delete,
            "CLEAR":     self._handle_clear,
            "RECONFIG":  self._handle_reconfig,
            "RESET":     self._handle_reset
        }

    def dispatch(self, message):
        """Primary entry point for messages from Master"""
        if not message: return None
        
        # Split command from parameters
        parts = message.split(':', 1)
        command = parts[0].strip()
        params = parts[1].strip() if len(parts) > 1 else ""
            
        handler = self.handlers.get(command)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                return f"ERROR:Handler_{command}_{str(e)[:50]}"
        return f"ERROR:Unknown_command_{command}"

    # --- Command Handlers ---

    def _handle_define(self, params):
        parts = params.split(':', 1)
        if len(parts) != 2: return "ERROR:Format_Name:Code"
        name, code = parts[0], parts[1]
        
        # Strip potential wrapping quotes that come from Serial/Master
        code = code.strip("'\"")
        
        # If the code looks like a lambda, we ensure the executor 
        # treats it as a function object, not a string.
        return self.task_executor.define_task(name, code)
        

    def _handle_exec(self, params):
        """
        Handles execution and returns a TASK_ID immediately.
        Format: task_name:args OR task_name:CORE:0:args
        """
        try:
            parts = params.split(':')
            task_name = parts[0]
            core = None
            args_str = ""

            # Routing to specific ARM Core
            if len(parts) > 1:
                if parts[1] == "CORE" and len(parts) > 3:
                    core = int(parts[2])
                    args_str = parts[3]
                else:
                    args_str = parts[1]

            # Parse arguments (int, float, or string)
            args = []
            if args_str:
                for a in args_str.split(','):
                    a = a.strip()
                    try:
                        args.append(float(a) if '.' in a else int(a))
                    except ValueError:
                        args.append(a.strip("'\""))

            # INTEGRATION: execute() now returns a Task ID for the SDK to poll
            # status will be 'OK:SUBMITTED', result will be the ID
            status, result = self.task_executor.execute(task_name, *args, core=core)
            
            if status == 'success':
                return f"OK:SUBMITTED:{result}"
            else:
                return f"ERROR:{result}"
        except Exception as e:
            return f"ERROR:Exec_Fault_{str(e)}"

    def _handle_get_res(self, params):
        """Used by the SDK to poll for a result using a Task ID"""
        if not params: return "ERROR:Missing_ID"
    
        status, result = self.task_executor.get_result(params)
        
        if status.upper() == 'SUCCESS':
            # FIX: Explicitly cast to string to avoid any remaining 
            # object representation issues
            return f"OK:RESULT:{str(result)}"
        
        # Handle the 'WAIT' state for the SDK
        if status.upper() == 'WAIT' or status.upper() == 'PENDING':
            return "WAIT:TASK_STILL_RUNNING"
            
        return f"ERROR:{result}"

    def _handle_list(self, params):
        return self.task_executor.list_tasks()

    def _handle_canvas(self, params):
        parts = params.split(':', 1)
        if len(parts) != 2: return "ERROR:Format"
        p_type, data_json = parts
        status, result = self.canvas.execute_primitive(p_type, json.loads(data_json))
        return f"OK:{json.dumps(result)}" if status == "success" else f"ERROR:{result}"

    def _handle_stats(self, params):
        return self.task_executor.get_stats()

    def _handle_sys_info(self, params):
        """Zynq XADC and PetaLinux Health Telemetry"""
        try:
            import sys_mon # Assumes your sys_mon.py is in the path
            health = sys_mon.get_all_telemetry()
            info = health['info']
            
            # Formatted for the Master Node's terminal display
            report = (
                f"[{info['kernel']}] "
                f"TEMP:{health['cpu_temp']}C | "
                f"CPU:{health['cpu']}% | "
                f"RAM:{health['mem']['used_mb']}/{health['mem']['total_mb']}MB | "
                f"UP:{health['uptime']['formatted']}"
            )
            return f"OK:{report}"
        except Exception as e:
            # Fallback if sys_mon isn't available
            return f"OK:Zynq_ARM_Active_UP:{int(time.clock_gettime(time.CLOCK_BOOTTIME))}s"

    def _handle_upload(self, params):
        parts = params.split(':', 1)
        if len(parts) != 2: return "ERROR:Format"
        filename, encoded_content = parts
        try:
            decoded_bytes = base64.b64decode(encoded_content)
            with open(filename, 'wb') as f: 
                f.write(decoded_bytes)
            return f"OK:Uploaded_{filename}"
        except Exception as e:
            return f"ERROR:Upload_Failed_{str(e)}"

    def _handle_delete(self, params):
        if not params: return "ERROR:Missing_Task_Name" 
        return self.task_executor.registry.delete_task(params.strip())

    def _handle_clear(self, params):
        return self.task_executor.registry.clear_all()

    def _handle_reconfig(self, params):
        """
        Handles FPGA Partial Reconfiguration from the firmware directory.
        Format: RECONFIG:bitstream_name.bin
        """
        if not params: 
            return "ERROR:Missing_Bitstream_Name"
        
        bitstream = params.strip()
        # Define the path relative to current worker_commands.py
        script_path = os.path.join("..", "firmware", "load_bistream_partial.sh")
        
        if not os.path.exists(script_path):
            return f"ERROR:Script_not_found_at_{script_path}"

        try:
            import subprocess
            # Execute the script
            result = subprocess.run(
                ['sudo', script_path, bitstream],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"OK:FPGA_Reconfigured_{bitstream}"
            else:
                return f"ERROR:Config_Failed_{result.stderr[:50]}"
                
        except subprocess.TimeoutExpired:
            return "ERROR:PCAP_Timeout_System_Stalled"
        except Exception as e:
            return f"ERROR:Internal_{str(e)[:50]}"

    def _handle_reset(self, params):
        # Safety flush before reboot
        sys.stdout.flush()
        os.system("reboot")
        return "OK:RESETTING"