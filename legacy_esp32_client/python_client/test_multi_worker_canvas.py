"""
Multi-Worker Canvas Test
Demonstrates parallel execution across 2 workers using Canvas primitives.
"""

import sys
import time
from broccoli_cluster import BroccoliCluster

# Configuration
MASTER_PORT = "COM8"

def test_multi_worker_canvas():
    """Test Canvas primitives with 2 workers."""
    
    print("\n" + "="*70)
    print("  MULTI-WORKER CANVAS TEST")
    print("="*70)
    
    # Connect to cluster
    cluster = BroccoliCluster(MASTER_PORT)
    cluster.connect()
    
    try:
        # ======================================================================
        # 1. Define tasks on both workers
        # ======================================================================
        print("\n[1] Defining tasks on both workers...")
        
        # Mathematical operations on worker 0
        cluster.define_task("square", "lambda x: x * x", worker=0)
        cluster.define_task("double", "lambda x: x * 2", worker=0)
        cluster.define_task("increment", "lambda x: x + 1", worker=0)
        
        # Same tasks on worker 1 for parallel execution
        cluster.define_task("square", "lambda x: x * x", worker=1)
        cluster.define_task("double", "lambda x: x * 2", worker=1)
        cluster.define_task("increment", "lambda x: x + 1", worker=1)
        
        # Reduction tasks (sum expects individual arguments, not list)
        cluster.define_task("add", "lambda x, y: int(x) + int(y)", worker=0)
        
        time.sleep(0.5)
        
        # ======================================================================
        # 2. Test GROUP - Parallel execution across workers
        # ======================================================================
        print("\n[2] Testing GROUP (parallel execution)...")
        print("  Executing: square(10) on Worker 0 and square(20) on Worker 1")
        
        start_time = time.time()
        results = cluster.group([
            cluster.sig("square", 10, worker=0),
            cluster.sig("square", 20, worker=1)
        ])
        elapsed = time.time() - start_time
        
        print(f"  Results: {results}")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  ✓ Expected: ['100', '400']")
        
        # ======================================================================
        # 3. Test CHAIN - Sequential pipeline across workers
        # ======================================================================
        print("\n[3] Testing CHAIN (sequential pipeline)...")
        print("  Pipeline: square(5) -> double() -> increment()")
        print("  Workers:  Worker 0  -> Worker 1  -> Worker 0")
        
        start_time = time.time()
        result = cluster.chain([
            cluster.sig("square", 5, worker=0),      # 25
            cluster.sig("double", worker=1),          # 50
            cluster.sig("increment", worker=0)        # 51
        ])
        elapsed = time.time() - start_time
        
        print(f"  Result: {result}")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  ✓ Expected: '51' (5² = 25 → ×2 = 50 → +1 = 51)")
        
        # ======================================================================
        # 4. Test CHORD - Map-reduce across workers
        # ======================================================================
        print("\n[4] Testing CHORD (map-reduce)...")
        print("  Map: square(0..4) distributed across workers")
        print("  Reduce: sum results manually (0² + 1² + 2² + 3² + 4² = 30)")
        
        start_time = time.time()
        # Header: Map square across both workers
        header_results = cluster.group([
            cluster.sig("square", i, worker=i % 2) for i in range(5)
        ])
        elapsed = time.time() - start_time
        
        print(f"  Map results: {header_results}")
        print(f"  Time: {elapsed:.3f}s")
        
        # Manually reduce (sum) - since we don't have a proper reduce function yet
        total = sum(int(x) for x in header_results)
        print(f"  Final sum: {total}")
        print(f"  ✓ Expected: 30 (0 + 1 + 4 + 9 + 16 = 30)")
        
        # ======================================================================
        # 5. Performance comparison: 2-worker vs 1-worker
        # ======================================================================
        print("\n[5] Performance comparison...")
        
        # 2-worker parallel execution
        print("  Running 10 tasks across 2 workers (parallel)...")
        start_time = time.time()
        results_parallel = cluster.group([
            cluster.sig("square", i, worker=i % 2) for i in range(10)
        ])
        time_parallel = time.time() - start_time
        
        # 1-worker sequential execution
        print("  Running 10 tasks on 1 worker (sequential)...")
        start_time = time.time()
        results_sequential = cluster.group([
            cluster.sig("square", i, worker=0) for i in range(10)
        ])
        time_sequential = time.time() - start_time
        
        speedup = time_sequential / time_parallel if time_parallel > 0 else 1.0
        
        print(f"\n  2-worker time: {time_parallel:.3f}s")
        print(f"  1-worker time: {time_sequential:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")
        
        if speedup > 1.2:
            print(f"  ✓ Parallel execution is faster!")
        else:
            print(f"  ⚠ Speedup less than expected (overhead from serial communication)")
        
        # ======================================================================
        # 6. Complex workflow example
        # ======================================================================
        print("\n[6] Complex workflow: Multi-stage pipeline...")
        print("  Stage 1: Parallel square 1..5 on both workers")
        print("  Stage 2: Double all results")
        print("  Stage 3: Sum manually")
        
        # Stage 1: Parallel map
        stage1_results = cluster.group([
            cluster.sig("square", i, worker=i % 2) for i in range(1, 6)
        ])
        print(f"  Stage 1 results: {stage1_results}")  # [1, 4, 9, 16, 25]
        
        # Stage 2: Double each result
        stage2_results = []
        for i, val in enumerate(stage1_results):
            result = cluster.execute("double", int(val), worker=i % 2, wait=True)
            stage2_results.append(int(result))
        print(f"  Stage 2 results: {stage2_results}")  # [2, 8, 18, 32, 50]
        
        # Stage 3: Manual sum
        final_result = sum(stage2_results)
        print(f"  Final sum: {final_result}")  # 110
        print(f"  ✓ Expected: 110 (2+8+18+32+50)")
        
        # ======================================================================
        # Final stats
        # ======================================================================
        print("\n[7] Checking final SLIP statistics...")
        cluster.stats()
        
        print("\n" + "="*70)
        print("  TEST COMPLETE ✓")
        print("="*70)
        
    finally:
        cluster.disconnect()


if __name__ == "__main__":
    try:
        test_multi_worker_canvas()
    except KeyboardInterrupt:
        print("\n✗ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
