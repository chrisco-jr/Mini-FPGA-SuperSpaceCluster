import time

def benchmarked_execute(cluster, mgr, category, task_name, *args, worker=0, retries=0, delay=0.5):
    """
    Wraps single task execution with RTT/TTR timing and informative console logs.
    """
    bm = mgr.get_tracker(category)
    attempt = 0
    
    while attempt <= retries:
        start = time.perf_counter()
        try:
            # 1. Submission Phase (Measures Master-to-Worker Latency)
            tid = cluster.execute(task_name, *args, worker=worker)
            
            if tid:
                # Record RTT (Acknowledge from Master)
                bm.record_tx(start)
                
                # 2. Polling Phase (Measures Worker Processing Time)
                # SDK get_result now returns (data, poll_count)
                result, polls = cluster.get_result(tid, wait=True)
                
                if result is not None:
                    # Record end-to-end Total Time to Result
                    if isinstance(result, str) and result.startswith("ExecError"):
                        # Raise a RuntimeError so the test suite's 'except' blocks catch it
                        raise RuntimeError(result)
                    bm.record_result(start, polls=polls)
                    return result
                
                print(f"  [!] W{worker} Timeout: Task {task_name} (ID:{tid})")
            else:
                print(f"  [!] W{worker} Rejected: Task {task_name} (No TID)")
                
        except Exception as e:
            print(f"  [!] W{worker} Exception during '{task_name}': {e}")
        
        attempt += 1
        if attempt <= retries:
            print(f"  [>] Retrying {task_name} on W{worker} ({attempt}/{retries})...")
            time.sleep(delay)

    # Log total failure for the Benchmark report
    bm.fail_count += 1
    return None

def benchmarked_group(cluster, mgr, category, signatures):
    """
    Measures a parallel broadcast. 
    Note: Polls is recorded as 1 representing the 'batch' check.
    """
    bm = mgr.get_tracker(category)
    start = time.perf_counter()
    try:
        # Calls SDK's new group() method which handles multi-execute + multi-poll
        results = cluster.group(signatures)
        bm.record_result(start, polls=1)
        return results
    except Exception as e:
        bm.fail_count += 1
        if "ExecError" in str(e):
            raise RuntimeError(e)
        print(f"  [!] Group Execution Failure: {e}")
        return None

def benchmarked_chain(cluster, mgr, category, signatures):
    """
    Measures a sequential pipeline.
    Polls is recorded as the number of stages in the chain.
    """
    bm = mgr.get_tracker(category)
    start = time.perf_counter()
    try:
        # Calls SDK's chain() method which handles data unpacking between stages
        res = cluster.chain(signatures)
        bm.record_result(start, polls=len(signatures))
        return res
    except Exception as e:
        bm.fail_count += 1
        if "ExecError" in str(e):
            raise RuntimeError(e)
        print(f"  [!] Chain Execution Failure: {e}")
        return None

def benchmarked_chord(cluster, mgr, category, header, callback):
    """
    Measures a Barrier (Map-Reduce) operation.
    """
    bm = mgr.get_tracker(category)
    start = time.perf_counter()
    try:
        # Calls SDK's chord() which executes header (group) then callback
        res = cluster.chord(header, callback)
        # Polls recorded as header count + callback
        bm.record_result(start, polls=len(header) + 1)
        return res
    except Exception as e:
        bm.fail_count += 1
        if "ExecError" in str(e):
            raise RuntimeError(e)
        print(f"  [!] Chord Execution Failure: {e}")
        return None