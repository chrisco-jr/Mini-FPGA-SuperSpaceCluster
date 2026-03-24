import time
import statistics

class Benchmark:
    def __init__(self, category: str = "General"):
        self.category = category
        self.rtts = [] # rtts = round trip time
        self.ttrs = [] # ttrs = time to result
        self.success_count = 0
        self.fail_count = 0

    def record_tx(self, start_time):
        """Records Round Trip Time (Client -> Master -> Client)."""
        self.rtts.append(time.perf_counter() - start_time)

    def record_result(self, start_time):
        """Records total Time to Result (Submission + Execution + Polling)."""
        self.ttrs.append(time.perf_counter() - start_time)
        self.success_count += 1

    def get_stats(self):
        total_attempts = self.success_count + self.fail_count
        avg_rtt = sum(self.rtts) / len(self.rtts) if self.rtts else 0
        avg_ttr = sum(self.ttrs) / len(self.ttrs) if self.ttrs else 0
        raw_jitter = statistics.stdev(self.ttrs) if len(self.ttrs) > 1 else 0
        
        # Normalized Jitter (Coefficient of Variation)
        # CV = (StdDev / Mean). Lower is more stable.
        norm_jitter = (raw_jitter / avg_ttr) if avg_ttr > 0 else 0
        
        success_ratio = self.success_count / total_attempts if total_attempts > 0 else 0
        return {
            "category": self.category,
            "avg_rtt_ms": avg_rtt * 1000,
            "avg_ttr_ms": avg_ttr * 1000,
            "raw_jitter_ms": raw_jitter * 1000,
            "normalized_jitter": norm_jitter, 
            "success_ratio": success_ratio,
            "total_attempts": total_attempts
        }

class BenchmarkManager:
    def __init__(self):
        # Dictionary to hold Benchmark objects: { "category_name": Benchmark() }
        self.trackers = {}
        self.suites = []

    def get_tracker(self, category: str):
        """Returns an existing tracker or creates a new one on the fly."""
        if category not in self.trackers:
            self.trackers[category] = Benchmark(category)
        return self.trackers[category]

    def log_suite_result(self, name, passed):
        """Logs the result of a high-level test section."""
        self.suites.append((name, passed))

    def report(self):
        """Prints a consolidated table and a final pass/fail count."""

        print(f"\n{'CATEGORY':<20} | {'AVG TTR':<10} | {'NORM JITTER':<12} | {'SUCCESS'}")
        print("-" * 65)
        
        for cat in sorted(self.trackers.keys()):
            stats = self.trackers[cat].get_stats()
            if stats['total_attempts'] > 0:
                print(f"{cat:<20} | {stats['avg_ttr_ms']:>7.1f}ms | {stats['normalized_jitter']:>12.3f} | {stats['success_ratio']*100:>6.1f}%")

        print(f"\n{'TEST SECTION':<40} | {'STATUS'}")
        print("-" * 65)
        passed_count = 0
        for name, passed in self.suites:
            status = "[PASS]" if passed else "[FAIL]"
            if passed: 
                passed_count += 1
            print(f"{name:<40} | {status}")
        
        total_suites = len(self.suites)
        print("-" * 65)
        if total_suites > 0:
            print(f"TOTAL TEST SUITES: {passed_count}/{total_suites} Passed")
        else:
            print("TOTAL TEST SUITES: No test suites defined.")
        print("-" * 65)