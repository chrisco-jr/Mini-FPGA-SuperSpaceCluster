import sys
import time
import argparse
import traceback
from broccoli_cluster import BroccoliCluster # Ensure naming matches your saved file
from benchmarks import BenchmarkManager
# Ensure test_utils is updated to handle polling!
from test_utils import benchmarked_execute 

# Configuration - Pynq Cluster IP
MASTER_IP = "192.168.1.50" 

def run_network_test(target_ip, num_workers=2):
    mgr = BenchmarkManager()
    
    print("=" * 70)
    print("NETWORK CONNECTIVITY & ASYNC TASK TEST - PYNQ-Z2 Cluster")
    print(f"Target Master: {target_ip}")
    print(f"Active Workers: {num_workers}")
    print("=" * 70)
    
    with BroccoliCluster(target_ip, timeout=5.0) as cluster:
        
        # --- [1/7] Master Handshake ---
        section = "[1/7] Master Node Stats Test"
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

        # --- [2/7] Legacy Lambda Support Test ---
        # Testing if the Registry wraps strings correctly
        time.sleep(0.5)
        section = "[2/7] Legacy Lambda Test"
        print(f"\n{section}")
        try:
            cluster.define_task("legacy_add", "lambda a, b: a + b", worker=0)
            res = benchmarked_execute(cluster, mgr, "light_legacy", "legacy_add", 10, 5, worker=0)
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
            for w in range(num_workers):
                logic = "def result(a, b):\n    return a + b"
                # This tests the Worker's handle_upload -> TaskRegistry.define pipeline
                cluster.upload_python_as_task("add", logic, worker=w)
                print(f"[OK] Worker {w}: 'add' uploaded.")
            mgr.log_suite_result(section, True)
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)

        # --- [4/7] Single-Worker Async Execution ---
        time.sleep(0.5)
        section = "[4/7] Single-Worker Execution"
        print(f"\n{section}")
        try:
            # benchmarked_execute must call get_result() internally now
            res = benchmarked_execute(cluster, mgr, "light_base64", "add", 10, 32, worker=0)
            if res is not None and int(res) == 42:
                print(f"[OK] add(10, 32) on W0 = {res}")
                mgr.log_suite_result(section, True)
            else:
                raise ValueError(f"Expected 42, got {res}")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)

        # --- [5/7] Group Orchestration Test ---
        # This confirms that firing multiple tasks doesn't jam the Worker UART
        time.sleep(0.5)
        section = "[5/7] Simple Orchestration (Group Test)"
        print(f"\n{section}")
        try:
            sigs = []
            expected = []
            for i in range(num_workers):
                cluster.define_task("multiply", "lambda a, b: a * b", worker=i)
                val1, val2 = (i + 2), (i + 3)
                sigs.append(cluster.sig("multiply", val1, val2, worker=i))
                expected.append(int(val1 * val2))

            start_orch = time.perf_counter()
            # .group() handles multiple execute() then multiple get_result()
            results = cluster.group(sigs)
            results = [int(r) for r in results] if results else []

            if results == expected:
                mgr.get_tracker("orch").record_result(start_orch)
                print(f"[OK] Group execution success: {results}")
                mgr.log_suite_result(section, True)
            else:
                raise ValueError(f"Got {results}, expected {expected}")
        except Exception as e:
            print(f"[FAIL] {section}: {e}")
            mgr.log_suite_result(section, False)
    
        # --- [6/7] Global Cleanup ---
        time.sleep(0.5)
        section = "[6/7] Global Cleanup"
        print(f"\n{section}")
        try:
            for w in range(num_workers):
                # Uses the simplified DELETEW protocol
                response = cluster.clear_all_tasks(worker=w)
                print(f"[OK] Worker {w} sweep initiated.")
            mgr.log_suite_result(section, True)
        except Exception as e:
            print(f"[!] Cleanup failed: {e}")
            mgr.log_suite_result(section, False)
        
        # --- [7/7] SoC Telemetry Audit ---
        time.sleep(0.5)
        section = "[7/7] SoC Telemetry Audit"
        print(f"\n{section}")
        try:
            for w in range(num_workers):
                response = cluster.get_system_info(worker=w)
                print(f"[OK] Worker {w} Health: {response}")
            mgr.log_suite_result(section, True)
        except Exception as e:
            print(f"[!] Telemetry Audit Failed: {e}")
            mgr.log_suite_result(section, False)
    
    # --- FINAL BENCHMARK REPORT ---
    print("\n" + "=" * 70)
    print("CONNECTIVITY BENCHMARK SUMMARY")
    mgr.report()
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broccoli Cluster Tier 1 Test")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--ip", type=str, default=MASTER_IP)
    args = parser.parse_args()
    
    run_network_test(args.ip, args.workers)