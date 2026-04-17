import time
import statistics

class Benchmark:
    def __init__(self, category: str = "General"):
        self.category = category
        self.rtts = []        # Round Trip Time (Submission Latency)
        self.ttrs = []        # Total Time to Result (End-to-End)
        self.poll_counts = [] # Number of polls per task
        self.success_count = 0
        self.fail_count = 0

    def record_tx(self, start_time):
        """Records the time it took just to get a Task ID back (Submission)."""
        self.rtts.append(time.perf_counter() - start_time)

    def record_result(self, start_time, polls=0):
        """Records the total time from submission to final result."""
        self.ttrs.append(time.perf_counter() - start_time)
        self.poll_counts.append(polls)
        self.success_count += 1

    def get_stats(self):
        total_attempts = self.success_count + self.fail_count
        avg_rtt = sum(self.rtts) / len(self.rtts) if self.rtts else 0
        avg_ttr = sum(self.ttrs) / len(self.ttrs) if self.ttrs else 0
        avg_polls = sum(self.poll_counts) / len(self.poll_counts) if self.poll_counts else 0
        
        raw_jitter = statistics.stdev(self.ttrs) if len(self.ttrs) > 1 else 0
        norm_jitter = (raw_jitter / avg_ttr) if avg_ttr > 0 else 0
        
        success_ratio = self.success_count / total_attempts if total_attempts > 0 else 0
        
        return {
            "category": self.category,
            "avg_rtt_ms": avg_rtt * 1000,       # Pure network submission
            "avg_ttr_ms": avg_ttr * 1000,       # End-to-end (includes polling)
            "avg_polls": avg_polls,            # How many times we checked
            "raw_jitter_ms": raw_jitter * 1000,
            "normalized_jitter": norm_jitter, 
            "success_ratio": success_ratio,
            "total_attempts": total_attempts
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
        """Prints a consolidated table with RTT vs TTR comparison."""
        # Adjusted headers for better spacing
        header = f"\n{'CATEGORY':<18} | {'SUBMIT (ms)':>12} | {'TTR (ms)':>10} | {'JITTER (cv)':>12} | {'POLLS':>6}"
        print(header)
        print("-" * len(header))
        
        for cat in sorted(self.trackers.keys()):
            stats = self.trackers[cat].get_stats()
            if stats['total_attempts'] > 0:
                # Calculate a 'Health' indicator based on jitter
                # cv < 0.1 is very stable; cv > 0.5 is jittery
                jitter_val = stats['normalized_jitter']
                jitter_label = "STABLE" if jitter_val < 0.2 else "VARIES"
                
                print(f"{cat:<18} | {stats['avg_rtt_ms']:>12.1f} | {stats['avg_ttr_ms']:>8.1f}ms | {jitter_val:>12.2f} | {stats['avg_polls']:>6.1f}")

        print(f"\n{'TEST SECTION':<58} | {'STATUS'}")
        print("-" * 75)
        passed_count = 0
        for name, passed in self.suites:
            status = "[PASS]" if passed else "[FAIL]"
            if passed: passed_count += 1
            print(f"{name:<58} | {status}")
        
        total_suites = len(self.suites)
        print("-" * 75)
        if total_suites > 0:
            print(f"TOTAL TEST SUITES: {passed_count}/{total_suites} Passed")
        print("-" * 75)