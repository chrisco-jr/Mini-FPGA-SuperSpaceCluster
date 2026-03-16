import os
import time
import platform

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

# ============================================================
# AGGREGATE (Optional)
# ============================================================

def get_all_telemetry():
    """Utility to grab everything at once if needed."""
    return {
        "info": get_system_info(),
        "cpu_temp": get_temp(),
        "cpu": get_cpu_usage(),
        "mem": get_mem_info()
    }
