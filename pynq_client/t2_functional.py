import sys
import time
import argparse
import traceback
from broccoli_cluster import BroccoliCluster
from benchmarks import BenchmarkManager
from test_utils import (
    benchmarked_execute, 
    benchmarked_chain, 
    benchmarked_group, 
    benchmarked_chord
)

# Configuration - Update with PetaLinux IP
MASTER_IP = "192.168.1.50" 

def run_functional_test(target_ip, num_workers=2):
    mgr = BenchmarkManager()
    
    print("=" * 70)
    print("FUNCTIONAL TEST (FULL BROCCOLI API CHECKOUT) - PYNQ-Z2 Cluster")
    print(f"Target Master: {target_ip}")
    print(f"Active Workers: {num_workers}")
    print("=" * 70)
    
    with BroccoliCluster(target_ip, timeout=10.0) as cluster:
        
        # --- [1/9] Master Handshake ---
        section = "[1/9] Master Node Connection Test"
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
            return 

        # --- [2/9] Core Task Operations ---
        time.sleep(0.5)
        section = "[2/9] CORE TASK OPERATIONS PER WORKER (LEGACY)"
        print(f"\n{section}")
        try:
            for w in range(num_workers):
                cluster.define_task("legacy_add", "lambda a, b: a + b", worker=w)
                cluster.define_task("legacy_multiply", "lambda a, b: a * b", worker=w)
            
            res = benchmarked_execute(cluster, mgr, "light_legacy", "legacy_add", 10, 5, worker=0)
            if res == 15:
                print(f"[OK] Lambda execution successful: {res}")
                mgr.log_suite_result(section, True)
            else:
                raise ValueError(f"Unexpected return: {res}")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)

        # --- [3/9] ID Collision Check ---
        time.sleep(0.5)
        section = "[3/9] WORKER ID COLLISION CHECK"
        print(f"\n{section}")
        try:
            # Register same name, different logic
            cluster.define_task("id_test", "lambda: 'W0_UNIQUE'", worker=0)
            cluster.define_task("id_test", "lambda: 'W1_UNIQUE'", worker=1)
            
            # Execute through the new blocking helper 
            res0 = cluster.execute_and_wait("id_test", worker=0)
            res1 = cluster.execute_and_wait("id_test", worker=1)
            
            if res0 == "W0_UNIQUE" and res1 == "W1_UNIQUE":
                print(f"  [OK] Namespaces isolated: W0='{res0}', W1='{res1}'")
                mgr.log_suite_result(section, True)
            else:
                # Provide feedback on the collision
                print(f"  [FAIL] Data mismatch! Received: W0={res0}, W1={res1}")
                mgr.log_suite_result(section, False)
        except Exception as e:
            print(f"  [FAIL] ID Check crashed: {e}")
            mgr.log_suite_result(section, False)

        # --- [4/9] Base64 Task Uploads & Execution ---
        time.sleep(0.5)
        section = "[4/9] Base64 Task Uploads (Single-Worker Execution)"
        print(f"\n{section}")
        try:
            for w in range(num_workers):
                logic = "def result(a, b):\n    return a + b"
                cluster.upload_python_as_task("add_b64", logic, worker=w)
            
            res = benchmarked_execute(cluster, mgr, "light_base64", "add_b64", 10, 32, worker=0)
            if int(res) == 42:
                print(f"[OK] add_b64(10, 32) on W0 = {res}")
                mgr.log_suite_result(section, True)
            else:
                mgr.log_suite_result(section, False)
        except Exception as e:
            mgr.log_suite_result(section, False)

        # --- [5/9] ORCHESTRATION & SMART DATA-FLOW ---
        time.sleep(0.5)
        section = "[5/9] ORCHESTRATION (Basic & Advanced Patterns)"
        print(f"\n{section}")
        try:
            # 1. Setup Tasks
            for w in range(num_workers):
                cluster.define_task("multiply", "lambda a, b: a * b", worker=w)
            cluster.define_task("fuse_simple", "lambda results: sum(r for r in results)", worker=0)
            cluster.define_task("gen_tel", "lambda: (0, 100, 200)", worker=0)
            #cluster.define_task("pick_xy", "lambda d: (d[1], d[2])", worker=0)
            cluster.define_task("pick_xy", "lambda *d: (d[1], d[2]) if len(d) > 2 else (d[0][1], d[0][2])", worker=0)
            cluster.define_task("scale", "lambda x, y, s: (x*s, y*s)", worker=1)

            # Execution & Individual result tracking
            results_log = {}

            print("  > A. Testing Standard Chain...")
            res_chain = benchmarked_chain(cluster, mgr, "orch_chain", [
                cluster.sig("legacy_add", 10, 20, worker=0),
                cluster.sig("legacy_multiply", 2, worker=1)
            ])
            results_log['Chain'] = (int(res_chain) == 60)

            print("  > B. Testing Parallel Group...")
            res_group = benchmarked_group(cluster, mgr, "orch_group", [
                cluster.sig("legacy_add", 5, 5, worker=0),
                cluster.sig("legacy_add", 10, 10, worker=1)
            ])
            results_log['Group'] = (res_group == [10, 20])

            print("  > C. Testing Simple Chord...")
            res_chord = benchmarked_chord(cluster, mgr, "orch_chord", [
                cluster.sig("multiply", 10, 2, worker=0), 
                cluster.sig("multiply", 5, 2, worker=1)
            ], cluster.sig("fuse_simple", worker=0))
            results_log['Chord'] = (int(res_chord) == 30)

            print("  > D. Testing Multi-Return Unpacking...")
            res_unpack = benchmarked_chain(cluster, mgr, "orch_chain_adv", [
                cluster.sig("gen_tel", worker=0),
                cluster.sig("pick_xy", worker=0),
                cluster.sig("scale", 0.5, worker=1)
            ])
            results_log['Unpacking'] = (list(res_unpack) == [50.0, 100.0])

            # Check for any False values in our log
            failed_patterns = [name for name, passed in results_log.items() if not passed]
            
            if not failed_patterns:
                print(f"  [OK] {section} passed.")
                mgr.log_suite_result(section, True)
            else:
                print(f"  [FAIL] {section} failed patterns: {', '.join(failed_patterns)}")
                mgr.log_suite_result(section, False)

        except Exception as e:
            print(f"  [FAIL] {section} crashed: {e}")
            mgr.log_suite_result(section, False)

        # --- [6/9] Heavy Module Payload (Warm/Cold Check) ---
        time.sleep(0.5)
        section = "[6/9] Heavy Module (120-Line Edge-AI Pipeline)"
        print(f"\n{section}")
        try:
            heavy_logic = """
def result(pixel_buffer, width, height, kernel_type="blur"):
    import math
    if len(pixel_buffer) != (width * height): return {"err": "mismatch"}
    normalized = [round(p / 255.0, 4) for p in pixel_buffer]
    kernels = {"blur": [1/9]*9, "edge": [-1]*4 + [8] + [-1]*4}
    k = kernels.get(kernel_type, kernels["blur"])
    output = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            sum_val = 0
            for ky in range(3):
                for kx in range(3):
                    pixel = normalized[(y + ky - 1) * width + (x + kx - 1)]
                    sum_val += pixel * k[ky * 3 + kx]
            output.append(sum_val)
    return {"status": "SUCCESS", "avg": sum(normalized)/len(normalized)}
"""
            print("  > Cold Start: Uploading & Executing...")
            cluster.upload_python_as_task("edge_vision", heavy_logic, worker=0)
            dummy_img = [i % 256 for i in range(100)]
            res_cold = benchmarked_execute(cluster, mgr, "heavy_cold", "edge_vision", dummy_img, 10, 10, worker=0)
            
            print("  > Warm Start: Re-executing cached module...")
            res_warm = benchmarked_execute(cluster, mgr, "heavy_warm", "edge_vision", dummy_img, 10, 10, worker=0)
            
            mgr.log_suite_result(section, res_cold['status'] == "SUCCESS" and res_warm['status'] == "SUCCESS")
        except Exception:
            mgr.log_suite_result(section, False)

        # --- [7/9] RESILIENCY & ROBUSTNESS ---
        time.sleep(0.5)
        section = "[7/9] RESILIENCY (Timeout & Partial Failure)"
        print(f"\n{section}")
        try:
            # A. Timeout Recovery
            print("  > A. Testing Timeout Recovery (W1 Hang)...")
            cluster.define_task("slow_task", "lambda x: __import__('time').sleep(x) or x", worker=1)
            # 20s sleep on a 10s default SDK timeout
            res_to = benchmarked_execute(cluster, mgr, "resiliency", "slow_task", 20, worker=1, retries=0)
            
            print("  [#] Cooling down... allowing W1 to finish the sleep cycle.")
            time.sleep(10) # 10s here + the time already elapsed during polling ≈ 20s
            
            # B. Poisoned Chord (Reduction Failure)
            print("  > B. Testing Chord with Poisoned Callback...")
            cluster.define_task("broken_reducer", "lambda results: results[0] / 0", worker=0)
            header = [cluster.sig("legacy_add", 1, 1, worker=0), cluster.sig("legacy_add", 2, 2, worker=1)]
            callback = cluster.sig("broken_reducer", worker=0)
            
            chord_caught = False
            try:
                # We expect the worker to return a DivisionByZero error string
                benchmarked_chord(cluster, mgr, "resiliency_chord", header, callback)
            except RuntimeError as e:
                print(f"  [OK] Caught expected reduction error: {e}")
                chord_caught = True

            # Validation
            resiliency_pass = (res_to is None and chord_caught)
            if resiliency_pass:
                print("  [OK] System identified timeout and caught callback crash.")
            
            mgr.log_suite_result(section, resiliency_pass)
        except Exception as e:
            print(f"  [FAIL] Resiliency Audit: {e}")
            mgr.log_suite_result(section, False)

        # --- [8/9] GENERAL ERROR HANDLING & CORRUPTION ---
        time.sleep(0.5)
        section = "[8/9] GENERAL ERRORS & CORRUPTION"
        print(f"\n{section}")
        
        # Dictionary to track sub-test results for logging
        audit_results = {
            "Undefined Task": False,
            "Syntax Error": False,
            "Arg Mismatch": False,
            "B64 Corruption": False,
            "Serialization": False,
            "Dependencies": False
        }

        try:
            # A. Undefined Task
            try:
                tid = cluster.execute("nonexistent_task_xyz", worker=0)
                cluster.get_result(tid, wait=True, timeout=2.0)
                print("  [X] Undefined Task: FAILED (No exception raised)")
            except RuntimeError: 
                audit_results["Undefined Task"] = True
                print("  [OK] Undefined Task: PASSED (Caught RuntimeError)")

            # B. Syntax Error
            try:
                cluster.define_task("bad_syntax", "this is !!! not python", worker=1)
                tid = cluster.execute("bad_syntax", worker=1)
                cluster.get_result(tid, wait=True, timeout=2.0)
                print("  [X] Syntax Error: FAILED")
            except RuntimeError: 
                audit_results["Syntax Error"] = True
                print("  [OK] Syntax Error: PASSED")

            # C. Argument Mismatch
            try:
                # 'legacy_add' expects 2 args, we only give it 99
                tid = cluster.execute("legacy_add", 99, worker=0) 
                res, _ = cluster.get_result(tid, wait=True, timeout=2.0)
                
                # We check for the specific 'missing' or 'positional' keywords 
                # returned by the Python interpreter on the Zynq
                msg = str(res).lower()
                if "missing" in msg or "positional" in msg or "argument" in msg:
                    audit_results["Arg Mismatch"] = True
                    print(f"  [OK] Arg Mismatch: PASSED (Caught: {res})")
                else:
                    print(f"  [X] Arg Mismatch: FAILED (Unexpected response: {res})")
            except RuntimeError as e:
                # If SDK raises the error instead of returning it
                if "missing" in str(e).lower() or "argument" in str(e).lower():
                    audit_results["Arg Mismatch"] = True
                    print(f"  [OK] Arg Mismatch: PASSED (Caught via SDK Exception)")

            # D. Corrupted Base64 Payload
            try:
                # Direct injection of bad data to the UPLOAD handler
                resp = cluster._send_raw("UPLOAD:task_err:!!NOT_B64!!")
                if "ERROR" in resp:
                    audit_results["B64 Corruption"] = True
                    print("  [OK] B64 Corruption: PASSED")
            except Exception:
                audit_results["B64 Corruption"] = True
                print("  [OK] B64 Corruption: PASSED (Socket/Protocol catch)")

            # E. Non-Serializable Return (The io.TextIOWrapper test)
            try:
                cluster.define_task("poison_ret", "lambda: open('/proc/cpuinfo', 'r')", worker=0)
                tid = cluster.execute("poison_ret", worker=0)
                res, _ = cluster.get_result(tid, wait=True, timeout=3.0)
                # If SDK raises RuntimeError, this line is skipped
                print("  [X] Serialization: FAILED (Returned object instead of error)")
            except RuntimeError as e:
                if "serializable" in str(e).lower():
                    audit_results["Serialization"] = True
                    print("  [OK] Serialization: PASSED")
                else:
                    print(f"  [X] Serialization: FAILED (Wrong error: {e})")

            # F. Missing Dependency
            try:
                cluster.define_task("no_lib", "lambda: __import__('fake_lib_123')", worker=1)
                tid = cluster.execute("no_lib", worker=1)
                cluster.get_result(tid, wait=True, timeout=2.0)
                print("  [X] Dependencies: FAILED")
            except RuntimeError:
                audit_results["Dependencies"] = True
                print("  [OK] Dependencies: PASSED")

            # Final validation for the Manager
            all_passed = all(audit_results.values())
            mgr.log_suite_result(section, all_passed)

        except Exception as e:
            print(f"  [!] Critical Audit Failure: {e}")
            mgr.log_suite_result(section, False)
        
       # --- [9/9] CLUSTER-WIDE RESET & HEALTH AUDIT ---
        time.sleep(0.5)
        section = "[9/9] CLUSTER RESET & HEALTH AUDIT"
        print(f"\n{section}")
        
        try:
            print("  [>] Initiating broadcast to all nodes...")
            
            reset_responses = cluster.broadcast_action("clear", num_workers)
            health_reports = cluster.broadcast_action("telemetry", num_workers)
            
            all_passed = True
            for i, (resp, health) in enumerate(zip(reset_responses, health_reports)):
                # We check the raw string returned by broadcast_action
                success = resp and "OK" in str(resp)
                prefix = "[OK]" if success else "[!]"
                if not success: all_passed = False
                
                print(f"  {prefix} Node {i}: {resp} | Health: {health}")

            mgr.log_suite_result(section, all_passed)

        except Exception as e:
            print(f"  [FAIL] Critical failure during broadcast audit: {e}")
            mgr.log_suite_result(section, False)
    
    print("\n" + "=" * 70)
    print("FUNCTIONAL TEST BENCHMARK SUMMARY")
    mgr.report()
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broccoli Cluster T2 Functional Test")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--ip", type=str, default=MASTER_IP)
    args = parser.parse_args()
    
    try:
        run_functional_test(args.ip, args.workers)
    except Exception as e:
        print(f"\n[FATAL] Script crashed: {e}")
        traceback.print_exc()
        sys.exit(1)