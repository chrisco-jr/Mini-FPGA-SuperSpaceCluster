import sys
import time
import argparse
import traceback
from broccoli_cluster_rework import BroccoliCluster
from benchmarks import BenchmarkManager
from test_utils import benchmarked_execute

# Configuration - Update with PetaLinux IP
MASTER_IP = "192.168.1.50" 

def run_functional_test(target_ip, num_workers=2):
    mgr = BenchmarkManager()
    
    print("=" * 70)
    print("FUNCTIONAL TEST (FULL BROCCOLI API CHECKOUT) - PYNQ-Z2 Cluster")
    print(f"Target Master: {target_ip}")
    print(f"Active Workers: {num_workers}")
    print("=" * 70)
    
    with BroccoliCluster(target_ip, timeout=5.0) as cluster:
        
        # --- [1/7] Master Handshake ---
        section = "[1/7] Master Node Connection Test"
        print(f"\n{section}")
        start_stats = time.perf_counter()
        try:
            stats = cluster.stats()
            mgr.get_tracker("handshake").record_result(start_stats)
            print(f"[OK] Network Stats: {stats}")
            mgr.log_suite_result(section, True)
        except Exception as e:
            print(f"[FAIL] Could not reach Master: {e}")
            mgr.log_suite_result(section, False)
            return # If Master is down, cannot proceed at all

        # --- [2/7] CORE TASK OPERATIONS ---
        time.sleep(0.5)
        section = "[2/7] CORE TASK OPERATIONS PER WORKER (LEGACY)"
        print(f"\n{section}")
        try:
            for w in range(num_workers):
                cluster.define_task("legacy_fac", "lambda a: a * a", worker=w)
                cluster.define_task("legacy_add", "lambda a, b: a + b", worker=w)
                cluster.define_task("legacy_sub", "lambda a, b: a - b", worker=w)
                cluster.define_task("legacy_div", "lambda a, b: a / b", worker=w)
                cluster.define_task("legacy_dis", "lambda a: f'Hello from PYNQ Z2, {a}!'", worker=w)
            
            res = benchmarked_execute(cluster, mgr, "light_legacy", "add", 10, 5, worker=0, retries=1)
            
            if res is not None and int(res) == 15:
                print(f"[OK] Lambda execution successful: {res}")
                mgr.log_suite_result(section, True)
            else:
                raise ValueError(f"Unexpected return: {res}")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)
        
        # --- [3/7] Per-Worker Base64 Upload Test ---
        time.sleep(0.5)
        section = "[3/7] Base64 Task Uploads"
        print(f"\n{section}")
        try:
            success = True
            for w in range(num_workers):
                logic = "def result(a, b):\n    return a + b"
                cluster.upload_python_as_task("add", logic, worker=w)
                print(f"[OK] Worker {w}: 'add' uploaded.")
            mgr.log_suite_result(section, True)
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)

        # --- [4/7] Single-Worker Execution ---
        time.sleep(0.5)
        section = "[4/7] Single-Worker Execution"
        print(f"\n{section}")
        try:
            res = benchmarked_execute(cluster, mgr, "light_base64", "add", 10, 32, worker=0, retries=1)
            if res is not None and int(res) == 42:
                print(f"[OK] add(10, 32) on W0 = {res}")
                mgr.log_suite_result(section, True)
            else:
                raise ValueError(f"Expected 42, got {res}")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)

        # --- [5/7] Group Orchestration Test ---
        time.sleep(0.5)
        section = "[5/7] Simple Orchestration (Group Test)"
        print(f"\n{section}")
        try:
            sigs = []
            expected = []
            for i in range(num_workers):
                cluster.define_task("multiply", "lambda a, b: a * b", worker=i)
                # Define signatures
                val1, val2 = (i + 2), (i * i)
                val3, val4 = (4 - i), (2 * i)
                
                sigs.append(cluster.sig("multiply", val1, val2, worker=i))
                sigs.append(cluster.sig("add", val3, val4, worker=i))
                
                expected.append(int(val1 * val2))
                expected.append(int(val3 + val4))

            start_orch = time.perf_counter()
            results = cluster.group(sigs)
            results = [int(r) for r in results] if results else []

            if results == expected:
                mgr.get_tracker("orch").record_result(start_orch)
                print(f"[OK] Group execution success: {results}")
                mgr.log_suite_result(section, True)
            else:
                mgr.get_tracker("orch").fail_count += 1
                raise ValueError(f"Got {results}, expected {expected}")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)
    
        # --- [6/7] Cleanup Phase ---
        time.sleep(0.5)
        section = "[6/7] Global Cleanup"
        print(f"\n{section}")
        start_sys = time.perf_counter()
        try:
            for w in range(num_workers):
                response = cluster.clear_all_tasks(worker=w)
                if response[:2].upper() == "OK":
                    print(f"[OK] Worker {w} confirmed clear: {response}")
                else:
                    print(f"[FAIL] Worker {w} registry error: {response}")
                    raise ValueError(f"Registry mismatch on Worker {w}")
            mgr.get_tracker("system").record_result(start_sys)
            mgr.log_suite_result(section, True)
        except Exception as e:
            print(f"[!] Cleanup failed: {e}")
            mgr.log_suite_result(section, False)
        
        # --- [7/7] SoC Telemetry Audit ---
        time.sleep(0.5)
        section = "[7/7] SoC Telemetry Audit"
        print(f"\n{section}")
        start_telemetry = time.perf_counter()
        
        try:
            for w in range(num_workers):
                response = cluster.get_system_info(worker=w)
                
                if response[:2].upper() == "OK":
                    print(f"[OK] Worker {w} Health: {response[3:]}")
                else:
                    print(f"[FAIL] Worker {w} Telemetry Error: {response}")
                    raise ValueError(f"Telemetry failed on Worker {w}")

            mgr.get_tracker("telemetry").record_result(start_telemetry)
            mgr.log_suite_result(section, True)
            
        except Exception as e:
            print(f"[!] Telemetry Section Failed: {e}")
            mgr.log_suite_result(section, False)
    
    # --- FINAL BENCHMARK REPORT ---
    print("\n" + "=" * 70)
    print("CONNECTIVITY BENCHMARK SUMMARY")
    mgr.report()
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broccoli Cluster Tier 2 Test")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--ip", type=str, default=MASTER_IP)
    args = parser.parse_args()
    
    try:
        run_network_test(args.ip, args.workers)
    except Exception as e:
        print(f"\n[FATAL] Script crashed: {e}")
        traceback.print_exc()
        sys.exit(1)