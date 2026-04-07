import time

def benchmarked_execute(cluster, mgr, category, task_name, *args, worker=0, retries=0, delay=0.5):
    bm = mgr.get_tracker(category)
    attempt = 0
    while attempt <= retries:
        start = time.perf_counter()
        try:
            # 1. Submission Phase
            # We want to know how long the Master takes to acknowledge the request
            tid = cluster.execute(task_name, *args, worker=worker)
            if tid:
                # Record RTT only on successful submission
                bm.record_tx(start)
                # 2. Polling Phase (TTR)
                # Ensure cluster.get_result returns (result, poll_count)
                result, polls = cluster.get_result(tid, wait=True)
                if result is not None:
                    # Record the full end-to-end time
                    bm.record_result(start, polls=polls)
                    return result
                print(f"  [!] W{worker} Timeout: Task {task_name} (ID:{tid})")
            else:
                print(f"  [!] W{worker} Rejected: Task {task_name} (No TID)")
        except Exception as e:
            # Important for multi-worker: which worker crashed?
            print(f"  [!] W{worker} Exception during '{task_name}': {e}")
        attempt += 1
        if attempt <= retries:
            time.sleep(delay)
    # If we exhaust retries, log the failure for the jitter/success ratio
    bm.fail_count += 1
    return None

def benchmarked_group(cluster, mgr, category, signatures):
    bm = mgr.get_tracker(category)
    start = time.perf_counter()
    try:
        res = cluster.group(signatures)
        # For a group, we record one 'result' representing the batch
        bm.record_result(start, polls=1)
        return res
    except Exception as e:
        bm.fail_count += 1
        raise e

def benchmarked_chain(cluster, mgr, category, signatures):
    bm = mgr.get_tracker(category)
    start = time.perf_counter()
    try:
        res = cluster.chain(signatures)
        bm.record_result(start, polls=len(signatures))
        return res
    except Exception as e:
        bm.fail_count += 1