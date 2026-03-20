# master_commands.py
import sys
from io import StringIO

class CommandProcessor:
    def __init__(self, master_node):
        self.master = master_node

    def dispatch(self, raw_line, output_stream=None):
        """
        Routes string commands to MasterNode methods.
        Redirects stdout to output_stream if provided (for Network mode).
        """
        cmd = raw_line.strip()
        if not cmd: return

        # Redirect stdout if we are sending data back over a socket
        original_stdout = sys.stdout
        if output_stream:
            sys.stdout = output_stream

        try:
            # --- System Commands ---
            if cmd == "STATS":
                self.master.get_stats()

            # --- Multi-Worker Commands (Prefix:Suffix) ---
            elif ":" in cmd:
                parts = cmd.split(':', 3)
                prefix = parts[0]
                
                if prefix == "DEFINEW" and len(parts) == 4:
                    self.master.forward_to_worker(int(parts[1]), f"DEFINE:{parts[2]}:{parts[3]}", parts[2])
                elif prefix == "EXECW" and len(parts) == 4:
                    self.master.forward_to_worker(int(parts[1]), f"EXEC:{parts[2]}:{parts[3]}", parts[2])
                elif prefix == "LISTW":
                    w_id = int(parts[1]) if len(parts) > 1 else 0
                    self.master.forward_to_worker(w_id, "LIST")
                elif prefix == "UPLOADW" and len(parts) == 4:
                    self.master.forward_to_worker(int(parts[1]), f"UPLOAD:{parts[2]}:{parts[3]}")
                elif prefix == "SYS_INFOW":
                    w_id = int(parts[1]) if len(parts) > 1 else 0
                    self.master.forward_to_worker(w_id, "SYS_INFO")                
                elif prefix == "DELETEW" and len(parts) >= 3:
                    w_id = int(parts[1])
                    task_name = parts[2]
                    self.master.forward_to_worker(w_id, f"DELETE:{task_name}")
                elif prefix == "CLEARW" and len(parts) >= 2: 
                    w_id = int(parts[1]) # Forwards "CLEAR" to the worker 
                    self.master.forward_to_worker(w_id, "CLEAR")

                # --- Legacy Shortcuts ---
                elif prefix == "DEFINE": self.dispatch(f"DEFINEW:0:{cmd[7:]}", output_stream)
                elif prefix == "EXEC":   self.dispatch(f"EXECW:0:{cmd[5:]}", output_stream)
                elif prefix == "UPLOAD": self.dispatch(f"UPLOADW:0:{cmd[7:]}", output_stream)
                elif prefix == "DELETE": self.dispatch(f"DELETEW:0:{cmd[7:]}", output_stream)
                elif prefix == "CLEAR":  self.dispatch(f"CLEARW:0:{cmd[6:]}", output_stream)
                else: print(f"ERROR:UNKNOWN_PREFIX:{prefix}")
            
            # --- Utility Commands ---
            elif cmd == "LIST":
                self.dispatch("LISTW:0", output_stream)
            elif cmd == "RESET_STATS":
                self.master.reset_stats()
            elif cmd == "HELP":
                # Call the welcome screen method on the master object
                self.master.show_welcome_screen()
    
                # If we are in network mode, we might want to tell the PC it's done
                if output_stream:
                    output_stream.write("OK:HELP_DISPLAYED\n")
                    output_stream.flush()
                return
            elif cmd == "SYS_INFO":
                # Default to Worker 0
                self.master.forward_to_worker(0, "SYS_INFO")
            else:
                print("ERROR:UNKNOWN_COMMAND")

        except Exception as e:
            print(f"ERROR:PARSER_EXCEPTION: {e}")
        finally:
            if output_stream:
                sys.stdout.flush()
                sys.stdout = original_stdout
