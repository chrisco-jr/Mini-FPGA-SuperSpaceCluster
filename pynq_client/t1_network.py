import time
import statistics

class Benchmark:
    def __init__(self, category: str = "General"):
        self.category = category
        self.rtts = []        # Round Trip Time (Submission)
        self.ttrs = []        # Total Time to Result (End-to-End)
        self.poll_counts = [] 
        self.success_count = 0
        self.fail_count = 0

    def record_tx(self, start_time):
        self.rtts.append(time.perf_counter() - start_time)

    def record_result(self, start_time, polls=0):
        self.ttrs.append(time.perf_counter() - start_time)
        self.poll_counts.append(polls)
        self.success_count += 1

    def get_stats(self):
        total_attempts = self.success_count + self.fail_count
        avg_rtt = sum(self.rtts) / len(self.rtts) if self.rtts else 0
        avg_ttr = sum(self.ttrs) / len(self.ttrs) if self.ttrs else 0
        
        # Throughput: Tasks Per Second (TPS)
        # We calculate this based on the sum of execution times
        total_exec_time = sum(self.ttrs)
        tps = self.success_count / total_exec_time if total_exec_time > 0 else 0
        
        raw_jitter = statistics.stdev(self.ttrs) if len(self.ttrs) > 1 else 0
        norm_jitter = (raw_jitter / avg_ttr) if avg_ttr > 0 else 0
        
        return {
            "category": self.category,
            "avg_rtt_ms": avg_rtt * 1000,
            "avg_ttr_ms": avg_ttr * 1000,
            "tps": tps,
            "normalized_jitter": norm_jitter, 
            "total_attempts": total_attempts,
            "avg_polls": sum(self.poll_counts) / len(self.poll_counts) if self.poll_counts else 0
        }

class BenchmarkManager:
    def __init__(self):
        self.trackers = {}
        self.suites = []

    def get_tracker(self, category: str):
        if category not in self.trackers:
            self.trackers[category] = Benchmark(category)
        return self.trackers[category]

    def log_suite_result(self, name, passed):
        self.suites.append((name, passed))

    def report(self):
        # Updated header to include TPS
        header = f"\n{'CATEGORY':<18} | {'SUBMIT (ms)':>11} | {'TTR (ms)':>9} | {'TPS':>8} | {'JITTER (cv)':>11} | {'POLLS'}"
        print(header)
        print("-" * len(header))
        
        for cat in sorted(self.trackers.keys()):
            stats = self.trackers[cat].get_stats()
            if stats['total_attempts'] > 0:
                print(f"{cat:<18} | {stats['avg_rtt_ms']:>11.1f} | {stats['avg_ttr_ms']:>7.1f}ms | {stats['tps']:>8.2f} | {stats['normalized_jitter']:>11.2f} | {stats['avg_polls']:>5.1f}")

        print(f"\n{'TEST SECTION':<63} | {'STATUS'}")
        print("-" * 80)
        passed_count = sum(1 for _, p in self.suites if p)
        for name, passed in self.suites:
            print(f"{name:<63} | {'[PASS]' if passed else '[FAIL]'}")
        
        print("-" * 80)
        if self.suites:
            print(f"TOTAL TEST SUITES: {passed_count}/{len(self.suites)} Passed")