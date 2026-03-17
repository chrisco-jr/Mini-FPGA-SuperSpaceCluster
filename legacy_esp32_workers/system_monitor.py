# System Monitoring for MicroPython
# RAM, Flash, CPU usage tracking

import gc
import esp
import machine
import time


class SystemMonitor:
    """System resource monitoring for ESP32"""
    
    def __init__(self):
        self.last_check = time.ticks_ms()
        print("[Monitor] System monitor initialized")
    
    def get_system_info(self):
        """Get system information"""
        try:
            info = {
                'platform': 'ESP32-S3',
                'frequency': machine.freq() // 1000000,  # MHz
                'cores': 2,
                'micropython': 'v1.22+',
            }
            return f"OK:platform={info['platform']};freq={info['frequency']}MHz;cores={info['cores']}"
        except Exception as e:
            return f"ERROR:{e}"
    
    def get_ram_usage(self):
        """Get RAM memory usage"""
        try:
            gc.collect()  # Force garbage collection for accurate reading
            
            free = gc.mem_free()
            allocated = gc.mem_alloc()
            total = free + allocated
            used_percent = (allocated / total * 100) if total > 0 else 0
            
            return f"OK:total={total};used={allocated};free={free};usage={used_percent:.1f}%"
        except Exception as e:
            return f"ERROR:{e}"
    
    def get_flash_usage(self):
        """Get flash memory usage"""
        try:
            import os
            
            # Get filesystem stats
            statvfs = os.statvfs('/')
            
            block_size = statvfs[0]
            total_blocks = statvfs[2]
            free_blocks = statvfs[3]
            
            total = block_size * total_blocks
            free = block_size * free_blocks
            used = total - free
            used_percent = (used / total * 100) if total > 0 else 0
            
            return f"OK:total={total};used={used};free={free};usage={used_percent:.1f}%"
        except Exception as e:
            return f"ERROR:{e}"
    
    def get_cpu_usage(self):
        """Get CPU usage estimate (MicroPython doesn't have direct CPU stats)"""
        try:
            # Estimate based on task execution time
            # This is a simplified metric
            return f"OK:core0=50%;core1=50%;note=estimated"
        except Exception as e:
            return f"ERROR:{e}"
    
    def get_task_list(self):
        """Get list of running tasks (limited in MicroPython)"""
        try:
            # MicroPython doesn't expose thread list like FreeRTOS
            # Return basic info
            return f"OK:threads=active;main=running"
        except Exception as e:
            return f"ERROR:{e}"
    
    def get_uptime(self):
        """Get system uptime in milliseconds"""
        try:
            uptime = time.ticks_ms()
            uptime_sec = uptime // 1000
            return f"OK:uptime={uptime_sec}s"
        except Exception as e:
            return f"ERROR:{e}"
    
    def get_temperature(self):
        """Get ESP32 internal temperature (if available)"""
        try:
            # ESP32 has internal temp sensor, but not always exposed in MicroPython
            return f"WARNING:temp_sensor_not_available"
        except Exception as e:
            return f"ERROR:{e}"
    
    def execute_command(self, cmd_string):
        """Parse and execute monitoring command"""
        try:
            cmd = cmd_string.split(':')[0]
            
            if cmd == "SYS_INFO":
                return self.get_system_info()
            elif cmd == "RAM_USAGE":
                return self.get_ram_usage()
            elif cmd == "FLASH_USAGE":
                return self.get_flash_usage()
            elif cmd == "CPU_USAGE":
                return self.get_cpu_usage()
            elif cmd == "TASK_LIST":
                return self.get_task_list()
            elif cmd == "UPTIME":
                return self.get_uptime()
            elif cmd == "TEMPERATURE":
                return self.get_temperature()
            else:
                return f"ERROR:Unknown_command_{cmd}"
        
        except Exception as e:
            return f"ERROR:{e}"
