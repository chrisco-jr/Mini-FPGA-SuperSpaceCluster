import os
import time
import platform
from datetime import datetime

# ============================================================
# SYSTEM IDENTITY
# ============================================================

def get_system_info():
    """Returns kernel release, version, and architecture."""
    try:
        return {
            "kernel": platform.release(),
            "version": platform.version().split()[0],
            "arch": platform.machine()
        }
    except:
        return {"error": "Could not retrieve system info"}

def get_system_time():
    """Returns the date and time recorded on the target board"""
    try:
        now = datetime.now()
        return {
            "date": now.strftime('%Y-%m-%d'),
            "time": now.strftime('%H_%M_%S')
        }
    except: 
        return {"error": "Could not retrieve system time"}

# ============================================================
# HARDWARE HEALTH
# ============================================================

def get_temp():
    """Reads Zynq SoC temperature via IIO (XADC)."""
    try:
        with open("/sys/bus/iio/devices/iio:device0/in_temp0_raw", "r") as f:
            raw = float(f.read().strip())
            # Formula: (Raw * 503.975 / 4096.0) - 273.15
            return round((raw * 503.975 / 4096.0) - 273.15, 1)
    except:
        return -1.0

def get_cpu_usage(sample_time=0.1):
    """Calculates CPU usage % over a short sample window."""
    def _read_stat():
        with open("/proc/stat", "r") as f:
            fields = [float(column) for column in f.readline().strip().split()[1:]]
        return sum(fields), fields[3] # Total, Idle

    try:
        t1_t, t1_i = _read_stat()
        time.sleep(sample_time)
        t2_t, t2_i = _read_stat()
        return round(100 * (1 - (t2_i - t1_i) / (t2_t - t1_t)), 1)
    except:
        return 0.0

def get_mem_info():
    """Returns memory usage statistics in MB and percentage."""
    try:
        with open("/proc/meminfo", "r") as f:
            mem = {line.split()[0]: int(line.split()[1]) for line in f}
        total = mem['MemTotal:']
        free = mem['MemFree:'] + mem['Buffers:'] + mem['Cached:']
        used = total - free
        return {
            "used_mb": round(used / 1024, 1),
            "total_mb": round(total / 1024, 1),
            "pct": round((used / total) * 100, 1)
        }
    except:
        return {"used_mb": 0, "total_mb": 0, "pct": 0}

def get_uptime():
    """Reads system uptime in seconds from /proc/uptime."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            
        # Optional: Return as a dictionary with formatted string
        # Useful for quick checks on the Master side
        m, s = divmod(int(uptime_seconds), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        
        return {
            "seconds": round(uptime_seconds, 1),
            "formatted": f"{d}d {h}h {m}m {s}s"
        }
    except:
        return {"seconds": 0.0, "formatted": "unknown"}

def get_storage_info(path="/"):
    """Returns disk usage statistics in GB and percentage."""
    try:
        st = os.statvfs(path)
        # Block size * total blocks
        total = (st.f_blocks * st.f_frsize)
        # Block size * free blocks available to user
        free = (st.f_bavail * st.f_frsize)
        used = total - free
        
        return {
            "used_gb": round(used / (1024**3), 2),
            "total_gb": round(total / (1024**3), 2),
            "pct": round((used / total) * 100, 1)
        }
    except:
        return {"used_gb": 0, "total_gb": 0, "pct": 0}

# ============================================================
# AGGREGATE (Optional)
# ============================================================

def get_all_telemetry():
    """Utility to grab everything at once if needed."""
    return {
        "info": get_system_info(),
        "cpu_temp": get_temp(),
        "cpu": get_cpu_usage(),
        "mem": get_mem_info(),
        "uptime": get_uptime(),
        "storage": get_storage_info(),
        "sys_time": get_system_time()
    }
