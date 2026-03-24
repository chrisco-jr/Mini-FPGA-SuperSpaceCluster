import time

def benchmarked_execute(cluster, mgr, category, task_name, *args, worker=0, retries=0, delay=0.5):
    """
    Executes a task with optional retries and timing telemetry.
    
    :param retries: Number of times to re-attempt on failure (default 0).
    :param delay: Seconds to wait between retries.
    """
    bm = mgr.get_tracker(category)
    attempt = 0
    
    while attempt <= retries:
        start = time.perf_counter()
        try:
            # 1. Submission (RTT)
            tid = cluster.execute(task_name, *args, worker=worker)
            bm.record_tx(start)
            
            # 2. Result (TTR)
            # wait=True handles the internal timeout of the SDK
            result = cluster.get_result(tid, wait=True)
            
            if result is not None and not str(result).startswith("ERROR"):
                bm.record_result(start)
                return result
            
            # If we reach here, the task returned None or ERROR
            print(f"  [!] Attempt {attempt+1}/{retries+1} failed for '{task_name}' on W{worker}")
            
        except Exception as e:
            print(f"  [!] Attempt {attempt+1}/{retries+1} exception on W{worker}: {e}")

        # If we failed, increment attempt and wait before trying again
        attempt += 1
        if attempt <= retries:
            time.sleep(delay)
    
    # If all retries exhausted, log the final failure
    bm.fail_count += 1
    return None