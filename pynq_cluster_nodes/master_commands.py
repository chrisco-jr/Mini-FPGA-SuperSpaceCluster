# master_commands.py (Simplified Version)

class CommandProcessor:
    def __init__(self, master_node):
        self.master = master_node
        # The Registry: Maps command prefixes to handler methods
        self.handlers = {
            "STATS":       self._handle_stats,
            "GET_RES":     self._handle_get_res,
            "DEFINEW":     self._handle_forward,
            "EXECW":       self._handle_forward,
            "UPLOADW":     self._handle_forward,
            "DELETEW":     self._handle_forward,
            "CLEARW":      self._handle_forward,
            "LISTW":       self._handle_forward,
            "SYS_INFOW":   self._handle_forward,
            "RECONFIGW":   self._handle_forward,
            "RESET_STATS": self._handle_reset,
            "HELP":        self._handle_help,
        }

    def dispatch(self, raw_line, output_stream=None):
        cmd_line = raw_line.strip()
        if not cmd_line: return

        # 1. Parse the command and parts
        parts = cmd_line.split(':')
        base_cmd = parts[0]

        # 2. Handle "Legacy" shortcuts (e.g., DEFINE -> DEFINEW:0)
        if base_cmd in ["DEFINE", "EXEC", "UPLOAD", "DELETE", "CLEAR", "LIST", "SYS_INFO, RECONFIG"]:
            # Reconstruct the line as a 'W' command and re-dispatch
            target_w = f"{base_cmd}W:0:{':'.join(parts[1:])}"
            return self.dispatch(target_w, output_stream)

        # 3. Lookup and Execute
        handler = self.handlers.get(base_cmd)
        
        if handler:
            response = handler(parts, output_stream)
            if output_stream and response:
                output_stream.write(f"{response}\n")
                output_stream.flush()
            else:
                # If we are in Serial Mode, print the result of the command
                if response: print(f"[MASTER] {response}")
        else:
            print(f"ERROR:UNKNOWN_COMMAND:{base_cmd}")

    # --- Specific Handlers ---

    def _handle_stats(self, parts, output_stream):
        return self.master.get_stats(silent=(output_stream is not None))

    def _handle_get_res(self, parts, output_stream):
        if len(parts) < 2: return "ERR:MISSING_ID"
        task_id = parts[1]
        w_id = self.master.task_map.get(task_id)
        if w_id is None: return "ERR:UNKNOWN_TASK_ID"
        return self.master.forward_to_worker(w_id, f"GET_RES:{task_id}")

    def _handle_forward(self, parts, output_stream):
        """Generic handler for any command formatted as CMDW:ID:ARGS"""
        if len(parts) < 2: return "ERR:MISSING_WORKER_ID"
        w_id = int(parts[1])
        # Strip the 'W' from DEFINEW to send DEFINE to the worker
        worker_cmd = parts[0][:-1] 
        payload = f"{worker_cmd}:{':'.join(parts[2:])}"
        return self.master.forward_to_worker(w_id, payload)

    def _handle_reset(self, parts, output_stream):
        self.master.reset_stats()
        return "OK:STATS_RESET"

    def _handle_help(self, parts, output_stream):
        self.master.show_welcome_screen()
        return "OK:HELP_DISPLAYED"