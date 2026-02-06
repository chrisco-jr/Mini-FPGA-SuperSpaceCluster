"""
Quick Test Suite - Verify Basic Cluster Functionality
ASCII-only output for Windows compatibility
"""

import os
import sys
import time
from broccoli_cluster import BroccoliCluster

MASTER_PORT = os.environ.get("BROCCOLI_PORT", "COM8")

def test_basic():
    """Test basic operations"""
    print("=" * 70)
    print("QUICK TEST SUITE - ESP32 Broccoli Cluster")
    print("=" * 70)
    
    with BroccoliCluster(MASTER_PORT, timeout=5.0) as cluster:
        print("\n[1/5] Connection Test")
        time.sleep(1)  # Let system stabilize
        print("[OK] Connected")
        
        print("\n[2/5] Stats Test")
        cluster.stats()
        print("[OK] Stats retrieved")
        
        print("\n[3/5] Task Definition Test")
        cluster.define_task("add", "lambda a, b: a + b", worker=0)
        print("[OK] Task defined")
        
        print("\n[4/5] Task Execution Test")
        result = cluster.execute("add", 10, 32, worker=0)
        print(f"[OK] add(10, 32) = {result}")
        assert result == "42", f"Expected 42, got {result}"
        
        print("\n[5/5] Multi-Worker Test")
        cluster.define_task("multiply", "lambda a, b: a * b", worker=0)
        cluster.define_task("multiply", "lambda a, b: a * b", worker=1)
        
        results = cluster.group([
            cluster.sig("multiply", 2, 3, worker=0),
            cluster.sig("multiply", 4, 5, worker=1)
        ])
        print(f"[OK] Parallel execution: {results}")
        
        print("\n" + "=" * 70)
        print("[SUCCESS] ALL TESTS PASSED")
        print("=" * 70)

if __name__ == "__main__":
    try:
        test_basic()
    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
