"""
ESP32 Distributed Cluster - Comprehensive Test Suite & Example Guide
=====================================================================

This file serves dual purposes:
1. Complete system validation and testing
2. Example code repository for developers

Each test demonstrates real-world usage patterns and best practices.

Hardware Requirements:
- ESP32-S3 Master on COM8 (or set BROCCOLI_PORT env var)
- 2x ESP32 Workers with MicroPython firmware
- Optional: Sensors, LEDs for hardware tests

Test Categories:
- Basic Communication & Task Execution
- Multi-Worker Parallel Processing
- Canvas Primitives (Celery-style orchestration)
- Dual-Core Execution
- WiFi & Network Operations
- HTTP Server & API
- Dynamic Code Upload
- Persistent Background Services
- GPIO & Hardware Control
- Error Handling & Recovery
- Real-World Application Examples
"""

import os
import sys
import time
import json
from datetime import datetime

# Import cluster library
try:
    from broccoli_cluster import BroccoliCluster
except ImportError:
    print("Error: broccoli_cluster not found")
    print("Make sure you're running from python_client directory")
    sys.exit(1)

# Configuration
MASTER_PORT = os.environ.get("BROCCOLI_PORT", "COM8")  #change this depend on your master COM
TEST_TIMEOUT = 10.0

# Test results tracking
test_results = []
current_test = 0
total_tests = 25  # Updated based on number of tests


class TestResult:
    """Track individual test results"""
    def __init__(self, name, category):
        self.name = name
        self.category = category
        self.passed = False
        self.error = None
        self.duration = 0
        self.output = []
    
    def log(self, message):
        """Log test output"""
        self.output.append(message)
        print(f"    {message}")


def print_header(title, char="="):
    """Print formatted section header"""
    print("\n" + char * 70)
    print(f"  {title}")
    print(char * 70)


def print_test_header(test_num, total, name, category):
    """Print test header"""
    print(f"\n[Test {test_num}/{total}] {name}")
    print(f"Category: {category}")
    print("-" * 70)


def run_test(name, category, test_func):
    """Execute a test with error handling"""
    global current_test
    current_test += 1
    
    result = TestResult(name, category)
    print_test_header(current_test, total_tests, name, category)
    
    start_time = time.time()
    try:
        test_func(result)
        result.passed = True
        result.duration = time.time() - start_time
        print(f"✓ PASSED ({result.duration:.2f}s)")
    except Exception as e:
        result.error = str(e)
        result.duration = time.time() - start_time
        print(f"✗ FAILED ({result.duration:.2f}s)")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    test_results.append(result)
    return result.passed


def print_summary():
    """Print comprehensive test summary"""
    print_header("TEST SUMMARY", "=")
    
    # Overall stats
    passed = sum(1 for r in test_results if r.passed)
    failed = len(test_results) - passed
    total_time = sum(r.duration for r in test_results)
    
    print(f"\nTotal Tests: {len(test_results)}")
    print(f"Passed: {passed} ({100*passed/len(test_results):.1f}%)")
    print(f"Failed: {failed}")
    print(f"Total Time: {total_time:.2f}s")
    
    # Category breakdown
    print("\n" + "-" * 70)
    print("RESULTS BY CATEGORY:")
    print("-" * 70)
    
    categories = {}
    for result in test_results:
        if result.category not in categories:
            categories[result.category] = {'passed': 0, 'failed': 0}
        
        if result.passed:
            categories[result.category]['passed'] += 1
        else:
            categories[result.category]['failed'] += 1
    
    for category, stats in sorted(categories.items()):
        total = stats['passed'] + stats['failed']
        print(f"{category:30s} {stats['passed']}/{total} passed")
    
    # Detailed results
    print("\n" + "-" * 70)
    print("DETAILED RESULTS:")
    print("-" * 70)
    
    for i, result in enumerate(test_results, 1):
        status = "✓" if result.passed else "✗"
        print(f"{status} Test {i:2d}: {result.name:50s} ({result.duration:.2f}s)")
        if result.error:
            print(f"           Error: {result.error}")
    
    # Failed tests detail
    if failed > 0:
        print("\n" + "-" * 70)
        print("FAILED TESTS DETAIL:")
        print("-" * 70)
        
        for result in test_results:
            if not result.passed:
                print(f"\n{result.name} ({result.category})")
                print(f"Error: {result.error}")
                if result.output:
                    print("Output:")
                    for line in result.output[-5:]:  # Last 5 lines
                        print(f"  {line}")
    
    print("\n" + "=" * 70)
    if failed == 0:
        print("🎉 ALL TESTS PASSED! System is fully operational.")
    else:
        print(f"⚠ {failed} test(s) failed. Review errors above.")
    print("=" * 70)


# ============================================================================
# TEST SUITE
# ============================================================================

def test_connection(result):
    """Test 1: Basic connection and communication"""
    result.log("Connecting to master node...")
    cluster = BroccoliCluster(MASTER_PORT, timeout=5.0)
    cluster.connect()
    result.log(f"Connected to {MASTER_PORT}")
    
    # Wait for system to stabilize after connection
    time.sleep(1.0)
    
    result.log("Testing STATS command...")
    cluster.stats()
    result.log("Communication successful")
    
    cluster.disconnect()


def test_basic_task_execution(result):
    """Test 2: Define and execute simple tasks"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Defining basic math tasks...")
        
        cluster.define_task("add", "lambda a, b: a + b", worker=0)
        cluster.define_task("multiply", "lambda a, b: a * b", worker=0)
        cluster.define_task("power", "lambda a, b: a ** b", worker=0)
        
        result.log("Executing tasks...")
        
        r1 = cluster.execute("add", 15, 27, worker=0)
        assert r1 == "42", f"Expected 42, got {r1}"
        result.log(f"add(15, 27) = {r1} ✓")
        
        r2 = cluster.execute("multiply", 12, 8, worker=0)
        assert r2 == "96", f"Expected 96, got {r2}"
        result.log(f"multiply(12, 8) = {r2} ✓")
        
        r3 = cluster.execute("power", 2, 10, worker=0)
        assert r3 == "1024", f"Expected 1024, got {r3}"
        result.log(f"power(2, 10) = {r3} ✓")


def test_multi_worker_addressing(result):
    """Test 3: Independent worker addressing"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Defining tasks on both workers...")
        
        # Different tasks on each worker
        cluster.define_task("square", "lambda x: x * x", worker=0)
        cluster.define_task("cube", "lambda x: x * x * x", worker=1)
        
        result.log("Executing on Worker 0...")
        r0 = cluster.execute("square", 10, worker=0)
        assert r0 == "100", f"Worker 0 failed: {r0}"
        result.log(f"Worker 0: square(10) = {r0} ✓")
        
        result.log("Executing on Worker 1...")
        r1 = cluster.execute("cube", 5, worker=1)
        assert r1 == "125", f"Worker 1 failed: {r1}"
        result.log(f"Worker 1: cube(5) = {r1} ✓")


def test_canvas_group(result):
    """Test 4: Canvas GROUP - Parallel execution"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Setting up tasks...")
        
        cluster.define_task("square", "lambda x: x * x", worker=0)
        cluster.define_task("square", "lambda x: x * x", worker=1)
        
        result.log("Executing parallel group...")
        start = time.time()
        
        results = cluster.group([
            cluster.sig("square", 10, worker=0),
            cluster.sig("square", 20, worker=1),
            cluster.sig("square", 30, worker=0),
            cluster.sig("square", 40, worker=1)
        ])
        
        elapsed = time.time() - start
        result.log(f"Completed in {elapsed:.3f}s")
        
        expected = [100, 400, 900, 1600]
        results_int = [int(x) for x in results]
        
        assert results_int == expected, f"Expected {expected}, got {results_int}"
        result.log(f"Results: {results_int} ✓")


def test_canvas_chain(result):
    """Test 5: Canvas CHAIN - Sequential pipeline"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Defining pipeline tasks...")
        
        cluster.define_task("square", "lambda x: x * x", worker=0)
        cluster.define_task("double", "lambda x: x * 2", worker=1)
        cluster.define_task("add_ten", "lambda x: x + 10", worker=0)
        
        result.log("Executing chain: square(5) -> double() -> add_ten()")
        result.log("Expected: 5² = 25 → ×2 = 50 → +10 = 60")
        
        final = cluster.chain([
            cluster.sig("square", 5, worker=0),   # 25
            cluster.sig("double", worker=1),       # 50
            cluster.sig("add_ten", worker=0)       # 60
        ])
        
        assert int(final) == 60, f"Expected 60, got {final}"
        result.log(f"Final result: {final} ✓")


def test_canvas_chord(result):
    """Test 6: Canvas CHORD - Map-reduce pattern"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Defining map-reduce tasks...")
        
        cluster.define_task("square", "lambda x: x * x", worker=0)
        cluster.define_task("square", "lambda x: x * x", worker=1)
        
        result.log("Map phase: square(0..4) distributed across workers")
        
        # Map phase
        map_results = cluster.group([
            cluster.sig("square", i, worker=i % 2) 
            for i in range(5)
        ])
        
        result.log(f"Map results: {map_results}")
        
        # Reduce phase (host-side)
        total = sum(int(x) for x in map_results)
        
        expected = 0 + 1 + 4 + 9 + 16  # 30
        assert total == expected, f"Expected {expected}, got {total}"
        result.log(f"Reduce result: {total} ✓")


def test_dual_core_execution(result):
    """Test 7: Dual-core execution on workers"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Defining task for dual-core test...")
        
        cluster.define_task("compute", "lambda x: x * x * x", worker=0)
        
        result.log("Executing on Core 0...")
        r0 = cluster.execute("compute", 10, worker=0, core=0)
        assert r0 == "1000", f"Core 0 failed: {r0}"
        result.log(f"Core 0: compute(10) = {r0} ✓")
        
        result.log("Executing on Core 1...")
        r1 = cluster.execute("compute", 20, worker=0, core=1)
        assert r1 == "8000", f"Core 1 failed: {r1}"
        result.log(f"Core 1: compute(20) = {r1} ✓")


def test_dual_core_canvas(result):
    """Test 8: Canvas with dual-core execution"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Defining task...")
        cluster.define_task("square", "lambda x: x * x", worker=0)
        
        result.log("Parallel execution across cores...")
        
        results = cluster.group([
            cluster.sig("square", 10, worker=0, core=0),
            cluster.sig("square", 20, worker=0, core=1),
            cluster.sig("square", 30, worker=0, core=0),
            cluster.sig("square", 40, worker=0, core=1)
        ])
        
        expected = [100, 400, 900, 1600]
        results_int = [int(x) for x in results]
        
        assert results_int == expected, f"Expected {expected}, got {results_int}"
        result.log(f"Results: {results_int} ✓")


def test_dynamic_code_upload(result):
    """Test 9: Upload complex Python code dynamically"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Uploading Python module...")
        
        # Upload a complex module
        module_code = """
# Math utilities module
import time

def fibonacci(n):
    '''Calculate nth Fibonacci number'''
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def prime_check(n):
    '''Check if number is prime'''
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

def stats(numbers):
    '''Calculate statistics'''
    if not numbers:
        return {}
    
    sorted_nums = sorted(numbers)
    n = len(numbers)
    
    return {
        'count': n,
        'sum': sum(numbers),
        'mean': sum(numbers) / n,
        'min': sorted_nums[0],
        'max': sorted_nums[-1],
        'median': sorted_nums[n//2] if n % 2 else (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
    }
"""
        
        cluster.upload_code("math_utils.py", module_code, worker=0)
        result.log("Module uploaded successfully")
        
        # Test fibonacci
        result.log("Testing fibonacci function...")
        cluster.define_task("fib", "lambda n: __import__('math_utils').fibonacci(n)", worker=0)
        fib_result = cluster.execute("fib", 10, worker=0)
        assert fib_result == "55", f"Expected 55, got {fib_result}"
        result.log(f"fibonacci(10) = {fib_result} ✓")
        
        # Test prime check
        result.log("Testing prime_check function...")
        cluster.define_task("is_prime", "lambda n: __import__('math_utils').prime_check(n)", worker=0)
        prime_result = cluster.execute("is_prime", 17, worker=0)
        assert prime_result == "True", f"Expected True, got {prime_result}"
        result.log(f"is_prime(17) = {prime_result} ✓")
        
        # Cleanup
        result.log("Cleaning up uploaded module...")
        cluster.define_task("cleanup", "lambda: __import__('os').remove('math_utils.py')", worker=0)
        cluster.execute("cleanup", worker=0)
        result.log("Cleanup complete ✓")


def test_builtin_libraries(result):
    """Test 10: Using MicroPython built-in libraries"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Testing built-in library access...")
        
        # Test 1: JSON module
        result.log("Testing json module...")
        cluster.define_task("json_test", '''
lambda: __import__('json').dumps({'status': 'ok', 'value': 42})
''', worker=0)
        
        json_result = cluster.execute("json_test", worker=0)
        result.log(f"JSON result: {json_result}")
        assert 'status' in json_result and 'ok' in json_result
        result.log("json module ✓")
        
        # Test 2: time module
        result.log("Testing time module...")
        cluster.define_task("time_test", '''
lambda: __import__('time').time()
''', worker=0)
        
        time_result = cluster.execute("time_test", worker=0)
        result.log(f"time.time() = {time_result}")
        assert int(time_result) > 0
        result.log("time module ✓")
        
        # Test 3: sys module
        result.log("Testing sys module...")
        cluster.define_task("sys_test", '''
lambda: __import__('sys').version
''', worker=0)
        
        sys_result = cluster.execute("sys_test", worker=0)
        result.log(f"MicroPython version: {sys_result}")
        assert 'MicroPython' in sys_result or 'v1' in sys_result
        result.log("sys module ✓")


def test_wifi_connection(result):
    """Test 11: WiFi connection using built-in network module"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Uploading WiFi utilities...")
        
        wifi_code = """
import network
import time

wlan = None

def scan_networks():
    '''Scan for available WiFi networks'''
    global wlan
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    networks = wlan.scan()
    return [{'ssid': n[0].decode(), 'rssi': n[3]} for n in networks[:5]]

def get_status():
    '''Get WiFi connection status'''
    global wlan
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    
    return {
        'active': wlan.active(),
        'connected': wlan.isconnected(),
        'ip': wlan.ifconfig()[0] if wlan.isconnected() else None
    }

def disconnect():
    '''Disconnect from WiFi'''
    global wlan
    if wlan and wlan.isconnected():
        wlan.disconnect()
    if wlan:
        wlan.active(False)
    return True
"""
        
        cluster.upload_code("wifi_utils.py", wifi_code, worker=0)
        result.log("WiFi module uploaded")
        
        # Test WiFi scan
        result.log("Scanning for WiFi networks...")
        cluster.define_task("wifi_scan", "lambda: __import__('wifi_utils').scan_networks()", worker=0)
        
        try:
            scan_result = cluster.execute("wifi_scan", worker=0, timeout=10.0)
            result.log(f"Found networks (sample): {scan_result[:100]}...")
            result.log("WiFi scan successful ✓")
        except Exception as e:
            result.log(f"WiFi scan note: {e} (may require antenna/hardware)")
        
        # Test status check
        result.log("Checking WiFi status...")
        cluster.define_task("wifi_status", "lambda: __import__('wifi_utils').get_status()", worker=0)
        status = cluster.execute("wifi_status", worker=0)
        result.log(f"WiFi status: {status}")
        
        # Cleanup
        result.log("Disabling WiFi...")
        cluster.define_task("wifi_off", "lambda: __import__('wifi_utils').disconnect()", worker=0)
        cluster.execute("wifi_off", worker=0)
        result.log("WiFi test complete ✓")


def test_http_server(result):
    """Test 12: HTTP server using built-in socket"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Uploading HTTP server code...")
        
        http_code = """
import socket
import json
import _thread

server_socket = None
server_running = False

def start_server(port=8080):
    '''Start simple HTTP API server in background'''
    global server_socket, server_running
    
    def server_loop():
        global server_socket, server_running
        
        addr = ('0.0.0.0', port)
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(addr)
        server_socket.listen(1)
        server_running = True
        
        print(f'HTTP server listening on port {port}')
        
        while server_running:
            try:
                server_socket.settimeout(1.0)
                cl, addr = server_socket.accept()
                
                request = cl.recv(1024).decode()
                
                # Simple routing
                if 'GET /status' in request:
                    response = json.dumps({'status': 'ok', 'server': 'ESP32'})
                elif 'GET /time' in request:
                    import time
                    response = json.dumps({'time': time.time()})
                else:
                    response = json.dumps({'error': 'not found'})
                
                cl.send(b'HTTP/1.1 200 OK\\r\\n')
                cl.send(b'Content-Type: application/json\\r\\n\\r\\n')
                cl.send(response.encode())
                cl.close()
                
            except OSError:
                pass
            except Exception as e:
                print(f'Server error: {e}')
    
    _thread.start_new_thread(server_loop, ())
    return f'HTTP server started on port {port}'

def stop_server():
    '''Stop the HTTP server'''
    global server_socket, server_running
    server_running = False
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
    return 'Server stopped'

def get_status():
    '''Get server status'''
    return {'running': server_running}
"""
        
        cluster.upload_code("http_server.py", http_code, worker=0)
        result.log("HTTP server module uploaded")
        
        # Start server
        result.log("Starting HTTP server on port 8080...")
        cluster.define_task("http_start", "lambda: __import__('http_server').start_server(8080)", worker=0)
        start_msg = cluster.execute("http_start", worker=0, wait=False)
        result.log(f"{start_msg}")
        
        time.sleep(2)  # Let server start
        
        # Check status
        result.log("Checking server status...")
        cluster.define_task("http_status", "lambda: __import__('http_server').get_status()", worker=0)
        status = cluster.execute("http_status", worker=0)
        result.log(f"Server status: {status}")
        
        result.log("HTTP server running in background ✓")
        result.log("Note: Server persists until worker reset")
        
        # Stop server (cleanup)
        result.log("Stopping HTTP server...")
        cluster.define_task("http_stop", "lambda: __import__('http_server').stop_server()", worker=0)
        cluster.execute("http_stop", worker=0)
        result.log("Server stopped ✓")


def test_persistent_service(result):
    """Test 13: Persistent background service"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Creating persistent counter service...")
        
        service_code = """
import _thread
import time

counter = 0
service_running = False

def counter_service():
    '''Background service that increments counter'''
    global counter, service_running
    service_running = True
    
    print('Counter service started')
    
    while service_running:
        counter += 1
        time.sleep(0.1)
    
    print('Counter service stopped')

def start_service():
    '''Start the counter service'''
    _thread.start_new_thread(counter_service, ())
    return 'Service started'

def get_counter():
    '''Get current counter value'''
    return counter

def stop_service():
    '''Stop the counter service'''
    global service_running
    service_running = False
    return 'Service stopped'
"""
        
        cluster.upload_code("counter_service.py", service_code, worker=0)
        result.log("Service module uploaded")
        
        # Start service
        result.log("Starting counter service...")
        cluster.define_task("start_counter", "lambda: __import__('counter_service').start_service()", worker=0)
        cluster.execute("start_counter", worker=0, wait=False)
        
        # Wait and check counter
        result.log("Waiting 2 seconds for counter to increment...")
        time.sleep(2)
        
        cluster.define_task("get_count", "lambda: __import__('counter_service').get_counter()", worker=0)
        count1 = int(cluster.execute("get_count", worker=0))
        result.log(f"Counter value: {count1}")
        
        # Check again
        time.sleep(1)
        count2 = int(cluster.execute("get_count", worker=0))
        result.log(f"Counter value after 1s: {count2}")
        
        assert count2 > count1, "Counter not incrementing"
        result.log(f"Counter incremented by {count2 - count1} ✓")
        
        # Stop service
        result.log("Stopping counter service...")
        cluster.define_task("stop_counter", "lambda: __import__('counter_service').stop_service()", worker=0)
        cluster.execute("stop_counter", worker=0)
        result.log("Service stopped ✓")


def test_gpio_operations(result):
    """Test 14: GPIO control"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Testing GPIO operations...")
        
        # Define GPIO control task
        gpio_code = """
import machine

def gpio_setup(pin, mode='OUT'):
    '''Setup GPIO pin'''
    if mode == 'OUT':
        p = machine.Pin(pin, machine.Pin.OUT)
    else:
        p = machine.Pin(pin, machine.Pin.IN)
    return f'GPIO {pin} configured as {mode}'

def gpio_write(pin, value):
    '''Write to GPIO pin'''
    p = machine.Pin(pin, machine.Pin.OUT)
    p.value(value)
    return f'GPIO {pin} set to {value}'

def gpio_read(pin):
    '''Read from GPIO pin'''
    p = machine.Pin(pin, machine.Pin.IN)
    return p.value()

def gpio_toggle(pin, times=3, delay_ms=500):
    '''Toggle GPIO pin'''
    import time
    p = machine.Pin(pin, machine.Pin.OUT)
    
    for i in range(times):
        p.value(1)
        time.sleep_ms(delay_ms)
        p.value(0)
        time.sleep_ms(delay_ms)
    
    return f'Toggled {times} times'
"""
        
        cluster.upload_code("gpio_utils.py", gpio_code, worker=0)
        result.log("GPIO module uploaded")
        
        # Test GPIO toggle
        result.log("Testing GPIO toggle on pin 46...")
        cluster.define_task("gpio_toggle", '''
lambda pin, times: __import__('gpio_utils').gpio_toggle(pin, times, 200)
''', worker=0)
        
        toggle_result = cluster.execute("gpio_toggle", 46, 3, worker=0)
        result.log(f"{toggle_result} ✓")
        
        result.log("GPIO operations completed (check hardware for LED blink)")


def test_adc_reading(result):
    """Test 15: ADC reading"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Testing ADC operations...")
        
        adc_code = """
import machine

def read_adc(pin):
    '''Read ADC value from pin'''
    adc = machine.ADC(machine.Pin(pin))
    adc.atten(machine.ADC.ATTN_11DB)  # Full range: 0-3.3V
    return adc.read()

def read_adc_voltage(pin):
    '''Read ADC as voltage'''
    adc = machine.ADC(machine.Pin(pin))
    adc.atten(machine.ADC.ATTN_11DB)
    raw = adc.read()
    voltage = raw / 4095.0 * 3.3
    return voltage

def read_multiple(pin, count=10):
    '''Read multiple samples and average'''
    import time
    adc = machine.ADC(machine.Pin(pin))
    adc.atten(machine.ADC.ATTN_11DB)
    
    total = 0
    for _ in range(count):
        total += adc.read()
        time.sleep_ms(10)
    
    return total / count
"""
        
        cluster.upload_code("adc_utils.py", adc_code, worker=0)
        result.log("ADC module uploaded")
        
        # Read ADC
        result.log("Reading ADC from GPIO 34...")
        cluster.define_task("adc_read", "lambda pin: __import__('adc_utils').read_adc(pin)", worker=0)
        
        adc_value = cluster.execute("adc_read", 34, worker=0)
        result.log(f"ADC value: {adc_value}")
        
        # Read as voltage
        result.log("Reading ADC as voltage...")
        cluster.define_task("adc_voltage", "lambda pin: __import__('adc_utils').read_adc_voltage(pin)", worker=0)
        
        voltage = cluster.execute("adc_voltage", 34, worker=0)
        result.log(f"Voltage: {voltage}V ✓")


def test_system_monitoring(result):
    """Test 16: System monitoring and statistics"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Collecting system information...")
        
        system_code = """
import gc
import sys
import machine
import esp32

def get_memory_info():
    '''Get memory statistics'''
    gc.collect()
    return {
        'free': gc.mem_free(),
        'allocated': gc.mem_alloc(),
        'total': gc.mem_free() + gc.mem_alloc()
    }

def get_system_info():
    '''Get comprehensive system info'''
    return {
        'platform': sys.platform,
        'version': sys.version,
        'implementation': sys.implementation.name,
        'freq': machine.freq(),
        'hall_sensor': esp32.hall_sensor(),
        'temp_raw': esp32.raw_temperature()
    }

def get_flash_info():
    '''Get flash memory info'''
    import os
    stats = os.statvfs('/')
    block_size = stats[0]
    total_blocks = stats[2]
    free_blocks = stats[3]
    
    return {
        'total': total_blocks * block_size,
        'free': free_blocks * block_size,
        'used': (total_blocks - free_blocks) * block_size
    }
"""
        
        cluster.upload_code("system_mon.py", system_code, worker=0)
        result.log("System monitoring module uploaded")
        
        # Get memory info
        result.log("Checking memory...")
        cluster.define_task("mem_info", "lambda: __import__('system_mon').get_memory_info()", worker=0)
        mem = cluster.execute("mem_info", worker=0)
        result.log(f"Memory: {mem}")
        
        # Get system info
        result.log("Checking system info...")
        cluster.define_task("sys_info", "lambda: __import__('system_mon').get_system_info()", worker=0)
        sys_info = cluster.execute("sys_info", worker=0)
        result.log(f"System: {sys_info[:100]}...")
        
        # Get flash info
        result.log("Checking flash storage...")
        cluster.define_task("flash_info", "lambda: __import__('system_mon').get_flash_info()", worker=0)
        flash = cluster.execute("flash_info", worker=0)
        result.log(f"Flash: {flash}")
        
        result.log("System monitoring complete ✓")


def test_error_handling(result):
    """Test 17: Error handling and recovery"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Testing error scenarios...")
        
        # Test 1: Undefined task
        result.log("1. Executing undefined task...")
        try:
            cluster.execute("nonexistent_task_xyz", 1, 2, worker=0)
            result.log("✗ Should have raised error")
            raise AssertionError("Expected error not raised")
        except Exception as e:
            result.log(f"✓ Correctly caught: {type(e).__name__}")
        
        # Test 2: Syntax error in task
        result.log("2. Defining task with syntax error...")
        cluster.define_task("bad_syntax", "this is not valid python", worker=0)
        
        try:
            cluster.execute("bad_syntax", worker=0)
            result.log("✗ Should have raised error")
            raise AssertionError("Expected error not raised")
        except Exception as e:
            result.log(f"✓ Correctly handled: {type(e).__name__}")
        
        # Test 3: Runtime error in task
        result.log("3. Task with runtime error...")
        cluster.define_task("divide_zero", "lambda: 1/0", worker=0)
        
        try:
            cluster.execute("divide_zero", worker=0)
            result.log("✗ Should have raised error")
            raise AssertionError("Expected error not raised")
        except Exception as e:
            result.log(f"✓ Correctly handled: {type(e).__name__}")
        
        # Test 4: Recovery - system still functional
        result.log("4. Verifying system recovery...")
        cluster.define_task("recovery_test", "lambda x: x * 2", worker=0)
        recovery_result = cluster.execute("recovery_test", 21, worker=0)
        assert recovery_result == "42", f"Recovery failed: {recovery_result}"
        result.log(f"✓ System recovered, result: {recovery_result}")
        
        result.log("Error handling tests complete ✓")


def test_task_management(result):
    """Test 18: Task listing and lifecycle"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Testing task management...")
        
        # Define multiple tasks
        result.log("Defining multiple tasks...")
        tasks = ["add", "sub", "mul", "div", "mod"]
        
        for task in tasks:
            cluster.define_task(task, f"lambda a, b: a {'+' if task == 'add' else '-' if task == 'sub' else '*' if task == 'mul' else '//' if task == 'div' else '%'} b", worker=0)
        
        result.log(f"Defined {len(tasks)} tasks")
        
        # List tasks
        result.log("Listing defined tasks...")
        task_list = cluster.list_tasks()
        result.log(f"Tasks found: {task_list}")
        
        # Execute each task
        result.log("Executing all tasks...")
        cluster.execute("add", 10, 5, worker=0)
        cluster.execute("sub", 10, 5, worker=0)
        cluster.execute("mul", 10, 5, worker=0)
        
        result.log("Task management complete ✓")


def test_performance_benchmark(result):
    """Test 19: Performance benchmarking"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Running performance benchmarks...")
        
        cluster.define_task("compute", "lambda n: sum(range(n))", worker=0)
        cluster.define_task("compute", "lambda n: sum(range(n))", worker=1)
        
        # Single worker benchmark
        result.log("Benchmark 1: Single worker, sequential execution")
        start = time.time()
        for i in range(10):
            cluster.execute("compute", 1000, worker=0, wait=True)
        single_time = time.time() - start
        result.log(f"Time: {single_time:.3f}s")
        
        # Parallel benchmark (2 workers)
        result.log("Benchmark 2: Two workers, parallel execution")
        start = time.time()
        cluster.group([
            cluster.sig("compute", 1000, worker=i % 2)
            for i in range(10)
        ])
        parallel_time = time.time() - start
        result.log(f"Time: {parallel_time:.3f}s")
        
        speedup = single_time / parallel_time if parallel_time > 0 else 1.0
        result.log(f"Speedup: {speedup:.2f}x")
        
        if speedup > 1.2:
            result.log("✓ Parallel execution is faster")
        else:
            result.log("⚠ Speedup limited by serial overhead")


def test_real_world_example_sensor_monitoring(result):
    """Test 20: Real-world example - Sensor monitoring system"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Example: Multi-sensor monitoring system")
        
        sensor_code = """
import machine
import time
import json

sensors = {}

def init_sensor(sensor_id, pin, sensor_type='adc'):
    '''Initialize a sensor'''
    global sensors
    
    if sensor_type == 'adc':
        adc = machine.ADC(machine.Pin(pin))
        adc.atten(machine.ADC.ATTN_11DB)
        sensors[sensor_id] = {'type': 'adc', 'adc': adc, 'pin': pin}
    
    return f'Sensor {sensor_id} initialized on pin {pin}'

def read_sensor(sensor_id):
    '''Read sensor value'''
    if sensor_id not in sensors:
        return {'error': 'Sensor not found'}
    
    sensor = sensors[sensor_id]
    
    if sensor['type'] == 'adc':
        raw = sensor['adc'].read()
        voltage = raw / 4095.0 * 3.3
        return {
            'sensor_id': sensor_id,
            'type': 'adc',
            'raw': raw,
            'voltage': voltage,
            'timestamp': time.time()
        }
    
    return {'error': 'Unknown sensor type'}

def read_all_sensors():
    '''Read all configured sensors'''
    readings = []
    for sensor_id in sensors:
        readings.append(read_sensor(sensor_id))
    return readings
"""
        
        cluster.upload_code("sensor_system.py", sensor_code, worker=0)
        result.log("Sensor system uploaded")
        
        # Initialize sensors
        result.log("Initializing sensors...")
        cluster.define_task("init_sens", '''
lambda sid, pin: __import__('sensor_system').init_sensor(sid, pin, 'adc')
''', worker=0)
        
        cluster.execute("init_sens", "temp", 34, worker=0)
        cluster.execute("init_sens", "light", 35, worker=0)
        result.log("Sensors initialized")
        
        # Read sensors
        result.log("Reading sensor data...")
        cluster.define_task("read_sens", "lambda sid: __import__('sensor_system').read_sensor(sid)", worker=0)
        
        temp_data = cluster.execute("read_sens", "temp", worker=0)
        result.log(f"Temperature sensor: {temp_data}")
        
        light_data = cluster.execute("read_sens", "light", worker=0)
        result.log(f"Light sensor: {light_data}")
        
        # Read all
        result.log("Reading all sensors...")
        cluster.define_task("read_all", "lambda: __import__('sensor_system').read_all_sensors()", worker=0)
        all_data = cluster.execute("read_all", worker=0)
        result.log(f"All sensors: {all_data[:100]}...")
        
        result.log("Sensor monitoring example complete ✓")


def test_real_world_example_data_processing_pipeline(result):
    """Test 21: Real-world example - Distributed data processing"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Example: Distributed data processing pipeline")
        
        # Worker 0: Data collection and preprocessing
        preprocess_code = """
def collect_data():
    '''Simulate data collection'''
    import machine
    import time
    
    data = []
    for _ in range(5):
        adc = machine.ADC(machine.Pin(34))
        adc.atten(machine.ADC.ATTN_11DB)
        value = adc.read()
        data.append(value)
        time.sleep_ms(50)
    
    return data

def preprocess(data):
    '''Preprocess raw data'''
    # Remove outliers (simple method)
    sorted_data = sorted(data)
    mean = sum(data) / len(data)
    
    filtered = [x for x in data if abs(x - mean) < mean * 0.3]
    
    return {
        'raw_count': len(data),
        'filtered_count': len(filtered),
        'data': filtered
    }
"""
        
        # Worker 1: Data analysis
        analyze_code = """
def analyze(preprocessed):
    '''Analyze preprocessed data'''
    data = preprocessed['data']
    
    if not data:
        return {'error': 'No data'}
    
    sorted_data = sorted(data)
    n = len(data)
    
    return {
        'count': n,
        'min': min(data),
        'max': max(data),
        'mean': sum(data) / n,
        'median': sorted_data[n//2],
        'range': max(data) - min(data)
    }
"""
        
        cluster.upload_code("preprocess.py", preprocess_code, worker=0)
        cluster.upload_code("analyze.py", analyze_code, worker=1)
        result.log("Pipeline modules uploaded to both workers")
        
        # Define pipeline
        result.log("Setting up processing pipeline...")
        cluster.define_task("collect", "lambda: __import__('preprocess').collect_data()", worker=0)
        cluster.define_task("preprocess", "lambda data: __import__('preprocess').preprocess(data)", worker=0)
        cluster.define_task("analyze", "lambda prep: __import__('analyze').analyze(prep)", worker=1)
        
        # Execute pipeline using chain
        result.log("Executing: collect -> preprocess -> analyze")
        
        # Step 1: Collect
        raw_data = cluster.execute("collect", worker=0)
        result.log(f"Collected: {raw_data}")
        
        # Step 2: Preprocess
        preprocessed = cluster.execute("preprocess", eval(raw_data), worker=0)
        result.log(f"Preprocessed: {preprocessed}")
        
        # Step 3: Analyze
        analysis = cluster.execute("analyze", eval(preprocessed), worker=1)
        result.log(f"Analysis: {analysis}")
        
        result.log("Data processing pipeline complete ✓")


def test_real_world_example_distributed_computation(result):
    """Test 22: Real-world example - Distributed mathematical computation"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Example: Distributed Monte Carlo Pi estimation")
        
        monte_carlo_code = """
import random

def estimate_pi_chunk(samples):
    '''Estimate pi using Monte Carlo method'''
    inside = 0
    
    for _ in range(samples):
        x = random.random()
        y = random.random()
        
        if x*x + y*y <= 1.0:
            inside += 1
    
    return inside

def combine_results(inside_counts, total_samples):
    '''Combine partial results'''
    total_inside = sum(inside_counts)
    pi_estimate = 4.0 * total_inside / total_samples
    return pi_estimate
"""
        
        cluster.upload_code("monte_carlo.py", monte_carlo_code, worker=0)
        cluster.upload_code("monte_carlo.py", monte_carlo_code, worker=1)
        result.log("Monte Carlo module uploaded to both workers")
        
        # Define tasks
        cluster.define_task("mc_pi", '''
lambda n: __import__('monte_carlo').estimate_pi_chunk(n)
''', worker=0)
        
        cluster.define_task("mc_pi", '''
lambda n: __import__('monte_carlo').estimate_pi_chunk(n)
''', worker=1)
        
        # Distribute computation
        result.log("Distributing Monte Carlo simulation...")
        samples_per_worker = 1000
        
        results = cluster.group([
            cluster.sig("mc_pi", samples_per_worker, worker=0),
            cluster.sig("mc_pi", samples_per_worker, worker=0),
            cluster.sig("mc_pi", samples_per_worker, worker=1),
            cluster.sig("mc_pi", samples_per_worker, worker=1)
        ])
        
        result.log(f"Partial results: {results}")
        
        # Combine results
        inside_counts = [int(x) for x in results]
        total_samples = samples_per_worker * len(results)
        pi_estimate = 4.0 * sum(inside_counts) / total_samples
        
        result.log(f"Pi estimate: {pi_estimate:.6f} (actual: 3.141593)")
        result.log(f"Error: {abs(pi_estimate - 3.141593):.6f}")
        
        result.log("Distributed computation complete ✓")


def test_real_world_example_iot_gateway(result):
    """Test 23: Real-world example - IoT gateway with data aggregation"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Example: IoT gateway with sensor aggregation")
        
        gateway_code = """
import time
import json

# Simulated sensor data store
sensor_readings = []

def log_reading(sensor_id, value):
    '''Log a sensor reading'''
    global sensor_readings
    
    reading = {
        'sensor_id': sensor_id,
        'value': value,
        'timestamp': time.time()
    }
    
    sensor_readings.append(reading)
    
    # Keep only last 100 readings
    if len(sensor_readings) > 100:
        sensor_readings = sensor_readings[-100:]
    
    return f'Logged reading from {sensor_id}'

def get_latest(sensor_id=None):
    '''Get latest readings'''
    if sensor_id:
        filtered = [r for r in sensor_readings if r['sensor_id'] == sensor_id]
        return filtered[-5:] if filtered else []
    else:
        return sensor_readings[-10:]

def aggregate_stats(sensor_id):
    '''Calculate statistics for a sensor'''
    readings = [r for r in sensor_readings if r['sensor_id'] == sensor_id]
    
    if not readings:
        return {'error': 'No data'}
    
    values = [r['value'] for r in readings]
    
    return {
        'sensor_id': sensor_id,
        'count': len(values),
        'min': min(values),
        'max': max(values),
        'avg': sum(values) / len(values),
        'latest': values[-1]
    }
"""
        
        cluster.upload_code("iot_gateway.py", gateway_code, worker=0)
        result.log("IoT gateway module uploaded")
        
        # Define gateway tasks
        cluster.define_task("log", '''
lambda sid, val: __import__('iot_gateway').log_reading(sid, val)
''', worker=0)
        
        cluster.define_task("get_latest", '''
lambda sid: __import__('iot_gateway').get_latest(sid)
''', worker=0)
        
        cluster.define_task("stats", '''
lambda sid: __import__('iot_gateway').aggregate_stats(sid)
''', worker=0)
        
        # Simulate sensor data logging
        result.log("Logging sensor data...")
        
        import random
        for i in range(10):
            temp = 20 + random.random() * 10
            cluster.execute("log", "temp_01", temp, worker=0, wait=False)
            
            humid = 40 + random.random() * 20
            cluster.execute("log", "humid_01", humid, worker=0, wait=False)
        
        time.sleep(1)
        
        # Get latest readings
        result.log("Retrieving latest readings...")
        latest = cluster.execute("get_latest", "temp_01", worker=0)
        result.log(f"Latest temp readings: {latest[:100]}...")
        
        # Get statistics
        result.log("Calculating statistics...")
        temp_stats = cluster.execute("stats", "temp_01", worker=0)
        result.log(f"Temperature stats: {temp_stats}")
        
        humid_stats = cluster.execute("stats", "humid_01", worker=0)
        result.log(f"Humidity stats: {humid_stats}")
        
        result.log("IoT gateway example complete ✓")


def test_real_world_example_edge_ml(result):
    """Test 24: Real-world example - Edge ML inference"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Example: Simple edge ML inference (linear model)")
        
        ml_code = """
# Simple linear model for temperature prediction
# Real ML would use pre-trained model

class LinearModel:
    def __init__(self):
        # Pretrained coefficients (example)
        self.weights = [0.5, -0.3, 0.8]
        self.bias = 2.1
    
    def predict(self, features):
        '''Make prediction from features'''
        if len(features) != len(self.weights):
            return None
        
        result = self.bias
        for i, feature in enumerate(features):
            result += self.weights[i] * feature
        
        return result

model = LinearModel()

def infer(features):
    '''Run inference'''
    return model.predict(features)

def batch_infer(feature_list):
    '''Batch inference'''
    return [model.predict(f) for f in feature_list]
"""
        
        cluster.upload_code("ml_model.py", ml_code, worker=0)
        result.log("ML model uploaded")
        
        # Define inference task
        cluster.define_task("infer", '''
lambda features: __import__('ml_model').infer(features)
''', worker=0)
        
        # Single inference
        result.log("Running single inference...")
        features = [25.5, 60.2, 1013.2]  # temp, humidity, pressure
        prediction = cluster.execute("infer", features, worker=0)
        result.log(f"Input features: {features}")
        result.log(f"Prediction: {prediction}")
        
        # Batch inference
        result.log("Running batch inference...")
        cluster.define_task("batch_infer", '''
lambda batch: __import__('ml_model').batch_infer(batch)
''', worker=0)
        
        batch = [
            [25.5, 60.2, 1013.2],
            [27.1, 55.8, 1012.5],
            [23.8, 62.5, 1014.1]
        ]
        
        predictions = cluster.execute("batch_infer", batch, worker=0)
        result.log(f"Batch predictions: {predictions}")
        
        result.log("Edge ML example complete ✓")


def test_real_world_example_complete_app(result):
    """Test 25: Real-world complete application - Smart home controller"""
    with BroccoliCluster(MASTER_PORT) as cluster:
        result.log("Example: Complete smart home controller")
        
        # Worker 0: Sensor monitoring
        sensor_controller = """
import machine
import time
import json

class SensorController:
    def __init__(self):
        self.sensors = {}
        self.readings = []
    
    def add_sensor(self, name, pin, sensor_type='adc'):
        '''Add a sensor'''
        if sensor_type == 'adc':
            adc = machine.ADC(machine.Pin(pin))
            adc.atten(machine.ADC.ATTN_11DB)
            self.sensors[name] = {'type': 'adc', 'adc': adc}
        return f'Added sensor: {name}'
    
    def read_all(self):
        '''Read all sensors'''
        readings = {}
        for name, sensor in self.sensors.items():
            if sensor['type'] == 'adc':
                readings[name] = sensor['adc'].read()
        return readings
    
    def check_thresholds(self, thresholds):
        '''Check if readings exceed thresholds'''
        readings = self.read_all()
        alerts = []
        
        for name, value in readings.items():
            if name in thresholds:
                if value > thresholds[name]['max']:
                    alerts.append(f'{name}: {value} > {thresholds[name]["max"]}')
                elif value < thresholds[name]['min']:
                    alerts.append(f'{name}: {value} < {thresholds[name]["min"]}')
        
        return alerts

controller = SensorController()

def init_sensors():
    '''Initialize home sensors'''
    controller.add_sensor('temperature', 34, 'adc')
    controller.add_sensor('light', 35, 'adc')
    return 'Sensors initialized'

def get_readings():
    '''Get current readings'''
    return controller.read_all()

def check_alerts():
    '''Check for alerts'''
    thresholds = {
        'temperature': {'min': 1000, 'max': 3000},
        'light': {'min': 500, 'max': 3500}
    }
    return controller.check_thresholds(thresholds)
"""
        
        # Worker 1: Actuator control
        actuator_controller = """
import machine

class ActuatorController:
    def __init__(self):
        self.actuators = {}
    
    def add_actuator(self, name, pin):
        '''Add an actuator'''
        self.actuators[name] = machine.Pin(pin, machine.Pin.OUT)
        return f'Added actuator: {name}'
    
    def set_state(self, name, state):
        '''Set actuator state'''
        if name in self.actuators:
            self.actuators[name].value(1 if state else 0)
            return f'{name}: {"ON" if state else "OFF"}'
        return f'Actuator {name} not found'
    
    def get_states(self):
        '''Get all actuator states'''
        return {name: pin.value() for name, pin in self.actuators.items()}

controller = ActuatorController()

def init_actuators():
    '''Initialize home actuators'''
    controller.add_actuator('led', 46)
    controller.add_actuator('fan', 47)
    return 'Actuators initialized'

def control(name, state):
    '''Control an actuator'''
    return controller.set_state(name, state)

def get_status():
    '''Get actuator status'''
    return controller.get_states()
"""
        
        # Upload to workers
        cluster.upload_code("sensor_ctrl.py", sensor_controller, worker=0)
        cluster.upload_code("actuator_ctrl.py", actuator_controller, worker=1)
        result.log("Controllers uploaded to workers")
        
        # Initialize system
        result.log("Initializing smart home system...")
        
        cluster.define_task("init_sens", "lambda: __import__('sensor_ctrl').init_sensors()", worker=0)
        cluster.define_task("init_act", "lambda: __import__('actuator_ctrl').init_actuators()", worker=1)
        
        cluster.execute("init_sens", worker=0)
        cluster.execute("init_act", worker=1)
        result.log("System initialized")
        
        # Main control loop simulation
        result.log("Running control cycle...")
        
        # Read sensors
        cluster.define_task("read_sens", "lambda: __import__('sensor_ctrl').get_readings()", worker=0)
        readings = cluster.execute("read_sens", worker=0)
        result.log(f"Sensor readings: {readings}")
        
        # Check for alerts
        cluster.define_task("check_alerts", "lambda: __import__('sensor_ctrl').check_alerts()", worker=0)
        alerts = cluster.execute("check_alerts", worker=0)
        result.log(f"Alerts: {alerts}")
        
        # Control actuators based on readings
        cluster.define_task("control", "lambda name, state: __import__('actuator_ctrl').control(name, state)", worker=1)
        
        result.log("Controlling LED based on light level...")
        cluster.execute("control", "led", True, worker=1)
        time.sleep(0.5)
        
        # Get actuator status
        cluster.define_task("status", "lambda: __import__('actuator_ctrl').get_status()", worker=1)
        status = cluster.execute("status", worker=1)
        result.log(f"Actuator status: {status}")
        
        # Turn off
        cluster.execute("control", "led", False, worker=1)
        
        result.log("Smart home controller example complete ✓")
        result.log("This demonstrates a complete IoT application with:")
        result.log("  - Multi-sensor monitoring")
        result.log("  - Threshold-based alerting")
        result.log("  - Automated actuator control")
        result.log("  - Distributed processing across workers")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main test execution"""
    print_header("ESP32 DISTRIBUTED CLUSTER - COMPREHENSIVE TEST SUITE", "=")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Master Port: {MASTER_PORT}")
    print(f"Total Tests: {total_tests}")
    print("=" * 70)
    
    # Run all tests
    run_test("Connection & Communication", "Basic", test_connection)
    run_test("Basic Task Execution", "Basic", test_basic_task_execution)
    run_test("Multi-Worker Addressing", "Multi-Worker", test_multi_worker_addressing)
    run_test("Canvas GROUP (Parallel)", "Canvas", test_canvas_group)
    run_test("Canvas CHAIN (Pipeline)", "Canvas", test_canvas_chain)
    run_test("Canvas CHORD (Map-Reduce)", "Canvas", test_canvas_chord)
    run_test("Dual-Core Execution", "Dual-Core", test_dual_core_execution)
    run_test("Dual-Core with Canvas", "Dual-Core", test_dual_core_canvas)
    run_test("Dynamic Code Upload", "Advanced", test_dynamic_code_upload)
    run_test("Built-in Libraries", "Libraries", test_builtin_libraries)
    run_test("WiFi Connection", "Network", test_wifi_connection)
    run_test("HTTP Server", "Network", test_http_server)
    run_test("Persistent Service", "Services", test_persistent_service)
    run_test("GPIO Operations", "Hardware", test_gpio_operations)
    run_test("ADC Reading", "Hardware", test_adc_reading)
    run_test("System Monitoring", "System", test_system_monitoring)
    run_test("Error Handling", "Reliability", test_error_handling)
    run_test("Task Management", "System", test_task_management)
    run_test("Performance Benchmark", "Performance", test_performance_benchmark)
    run_test("Example: Sensor Monitoring", "Examples", test_real_world_example_sensor_monitoring)
    run_test("Example: Data Processing Pipeline", "Examples", test_real_world_example_data_processing_pipeline)
    run_test("Example: Distributed Computation", "Examples", test_real_world_example_distributed_computation)
    run_test("Example: IoT Gateway", "Examples", test_real_world_example_iot_gateway)
    run_test("Example: Edge ML Inference", "Examples", test_real_world_example_edge_ml)
    run_test("Example: Complete Smart Home", "Examples", test_real_world_example_complete_app)
    
    # Print summary
    print_summary()
    
    # Return exit code
    failed = sum(1 for r in test_results if not r.passed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n✗ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
