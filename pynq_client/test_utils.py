import time

def benchmarked_execute(cluster, mgr, category, task_name, *args, worker=0, retries=0, delay=0.5):
    bm = mgr.get_tracker(category)
    attempt = 0
    
    while attempt <= retries:
        start = time.perf_counter()
        try:
            # 1. Submission (RTT)
            tid = cluster.execute(task_name, *args, worker=worker)
            bm.record_tx(start)
            
            # 2. Result (TTR) - Now capturing poll count
            result, polls = cluster.get_result(tid, wait=True)
            
            if result is not None:
                bm.record_result(start, polls=polls)
                return result
            
            print(f"  [!] Attempt {attempt+1} failed (Timeout) on W{worker}")
        except Exception as e:
            print(f"  [!] Attempt {attempt+1} exception: {e}")

        attempt += 1
        if attempt <= retries:
            time.sleep(delay)
    
    bm.fail_count += 1
    return None