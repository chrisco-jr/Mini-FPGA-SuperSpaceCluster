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

        # --- [5a/7] Basic Orchestration (Group, Chain, Chord) ---
        time.sleep(0.5)
        section = "[5a/7] BASIC ORCHESTRATION (Group, Chain, Chord)"
        print(f"\n{section}")
        try:
            # A. Sequential Chain: (10 + 20) * 2 = 60
            print("  > Testing Chain Logic (W0 -> W1)...")
            pipe = [
                cluster.sig("legacy_add", 10, 20, worker=0),
                cluster.sig("legacy_multiply", 2, worker=1)
            ]
            res_chain = benchmarked_chain(cluster, mgr, "orch_chain", pipe)

            # B. Parallel Group: Same task on both workers
            print("  > Testing Group Logic (Parallel Broadcast)...")
            sigs = [
                cluster.sig("legacy_add", 5, 5, worker=0),
                cluster.sig("legacy_add", 10, 10, worker=1)
            ]
            res_group = benchmarked_group(cluster, mgr, "orch_group", sigs)

            # C. Simple Chord: Parallel multiply, then sum
            print("  > Testing Chord Logic (Barrier Sync)...")
            cluster.define_task("fuse_simple", "lambda results: sum(r for r in results)", worker=0)
            chord_header = [
                cluster.sig("legacy_multiply", 10, 2, worker=0), # 20
                cluster.sig("legacy_multiply", 5, 2, worker=1)   # 10
            ]
            chord_cb = cluster.sig("fuse_simple", worker=0)
            res_chord = benchmarked_chord(cluster, mgr, "orch_chord", chord_header, chord_cb)

            # Validation
            success = (int(res_chain) == 60 and 
                       res_group == [10, 20] and 
                       int(res_chord) == 30)
            
            mgr.log_suite_result(section, success)
            if success: print(f"[OK] {section} passed.")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)

        # --- [5b/7] ADVANCED DATA-FLOW (Smart Pipe) ---
        time.sleep(0.5)
        section_adv = "[5b/7] ADVANCED ORCHESTRATION (Unpack & Select)"
        print(f"\n{section_adv}")
        try:
            # Setup Tasks for complex data handling
            cluster.define_task("gen_tel", "lambda: (0, 100, 200)", worker=0)
            cluster.define_task("pick_xy", "lambda d: (d[1], d[2])", worker=0)
            cluster.define_task("scale", "lambda x, y, s: (x*s, y*s)", worker=1)
            cluster.define_task("sum_vals", "lambda results: sum(r[1] for r in results)", worker=0)

            # A. Unpacking Chain: (0, 100, 200) -> select -> scale
            print("  > Testing Multi-Return Unpacking...")
            adv_pipe = [
                cluster.sig("gen_tel", worker=0),
                cluster.sig("pick_xy", worker=0),
                cluster.sig("scale", 0.5, worker=1)
            ]
            res_unpack = benchmarked_chain(cluster, mgr, "orch_chain_adv", adv_pipe)

            # B. Structured Chord: Map node results, then reduce specific field
            print("  > Testing Zipped/Structured Chord...")
            adv_header = [
                cluster.sig("get_node_data", "Node0", 50, worker=0), # (ID, Val, RSSI)
                cluster.sig("get_node_data", "Node1", 75, worker=1)
            ]
            adv_cb = cluster.sig("sum_vals", worker=0)
            res_struct = benchmarked_chord(cluster, mgr, "orch_chord_adv", adv_header, adv_cb)

            # Validation
            valid = (list(res_unpack) == [50.0, 100.0] and int(res_struct) == 125)
            mgr.log_suite_result(section_adv, valid)
            if valid: print(f"[OK] {section_adv} passed.")
        except Exception as e:
            print(f"[FAIL] {section_adv}: {e}")
            mgr.log_suite_result(section_adv, False)
    
        # --- [6a/7] RESILIENCY: TIMEOUT RECOVERY ---
        section = "[6a/7] RESILIENCY (TIMEOUT & RETRY)"
        print(f"\n{section}")
        try:
            # Define a task that ignores its arguments and just sleeps
            cluster.define_task("slow_task", "lambda x: __import__('time').sleep(x) or x", worker=1)
            
            print("  > Testing individual task timeout (Expected Failure)...")
            # We set a low timeout in get_result or wait for the default 15s
            res = benchmarked_execute(cluster, mgr, "resiliency", "slow_task", 20, worker=1, retries=0)
            
            if res is None:
                print("  [OK] Master correctly identified and recovered from worker timeout.")
                mgr.log_suite_result(section, True)
            else:
                print("  [FAIL] Master waited too long or returned ghost data.")
                mgr.log_suite_result(section, False)
        except Exception as e:
            print(f"  [OK] Caught expected timeout exception: {e}")
            mgr.log_suite_result(section, True)
        
        # --- [6b/7] ROBUSTNESS: ORCHESTRATION BREAKAGE ---
        section = "[6b/7] ROBUSTNESS (PARTIAL CHORD FAILURE)"
        print(f"\n{section}")
        try:
            print("  > Testing Chord with poisoned callback...")
            # Header is fine
            header = [cluster.sig("legacy_add", 1, 1, worker=0), cluster.sig("legacy_add", 2, 2, worker=1)]
            
            # Callback is broken (Division by zero)
            cluster.define_task("broken_reducer", "lambda results: results[0] / 0", worker=0)
            callback = cluster.sig("broken_reducer", worker=0)
            
            try:
                cluster.chord(header, callback)
                print("  [FAIL] Chord should have raised an exception.")
                mgr.log_suite_result(section, False)
            except RuntimeError as e:
                print(f"  [OK] Caught expected reduction error: {e}")
                mgr.log_suite_result(section, True)
                
        except Exception as e:
            print(f"  [FAIL] Unexpected robustness error: {e}")
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
        run_functional_test(args.ip, args.workers)
    except Exception as e:
        print(f"\n[FATAL] Script crashed: {e}")
        traceback.print_exc()
        sys.exit(1)