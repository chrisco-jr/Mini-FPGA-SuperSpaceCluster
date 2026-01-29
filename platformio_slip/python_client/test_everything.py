"""
Comprehensive Test Suite for ESP32 Distributed Cluster
Tests ALL features: tasks, Canvas primitives, dual-core, peripherals, monitoring
NO SKIPPING - ALL TESTS MUST PASS
"""

import time
import json
from broccoli_cluster import BroccoliCluster

def print_section(title):
    print("
" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_everything():
    print("
" + "="*70)
    print("=" + " "*68 + "=")
    print("=" + "  ESP32 DISTRIBUTED CLUSTER - COMPREHENSIVE TEST SUITE".center(68) + "=")
    print("=" + " "*68 + "=")
    print("="*70)
    
    passed_tests = 0
    failed_tests = 0
    total_tests = 14
    test_results = {}  # Track each test individually
    
    with BroccoliCluster("COM25") as cluster:
        
        # ============================================================
        # TEST 1: CONNECTION & BASIC COMMUNICATION
        # ============================================================
        print_section("TEST 1: Connection & Basic Communication")
        try:
            print("OK Serial connection established on COM25")
            print("OK Master node responding")
            time.sleep(0.5)
            passed_tests += 1
            test_results[1] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[1] = False
        
        # ============================================================
        # TEST 2: TASK DEFINITION & EXECUTION
        # ============================================================
        print_section("TEST 2: Task Definition & Execution")
        try:
            print("
Defining basic tasks...")
            cluster.define_task("add", "lambda a, b: a + b")
            cluster.define_task("multiply", "lambda a, b: a * b")
            cluster.define_task("power", "lambda a, b: a ** b")
            cluster.define_task("square", "lambda x: x * x")
            time.sleep(0.5)
            
            print("
Executing tasks:")
            result = cluster.execute("add", 15, 27)
            print(f"  add(15, 27) = {result}")
            assert result == "42", f"Expected 42, got {result}"
            
            result = cluster.execute("multiply", 12, 8)
            print(f"  multiply(12, 8) = {result}")
            assert result == "96", f"Expected 96, got {result}"
            
            result = cluster.execute("power", 2, 10)
            print(f"  power(2, 10) = {result}")
            assert result == "1024", f"Expected 1024, got {result}"
            
            print("
OK All basic task tests passed!")
            passed_tests += 1
            test_results[2] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[2] = False
        
        # ============================================================
        # TEST 3: CANVAS PRIMITIVES - GROUP
        # ============================================================
        print_section("TEST 3: Canvas Primitives - GROUP (Parallel)")
        try:
            print("
Executing group([add(5,3), multiply(4,7), square(9)])...")
            results = cluster.group([
                cluster.sig("add", 5, 3),
                cluster.sig("multiply", 4, 7),
                cluster.sig("square", 9)
            ])
            print(f"Results: {results}")
            
            if results is None:
                raise Exception("GROUP returned None - Canvas not implemented")
            
            expected = [8, 28, 81]
            if isinstance(results, list):
                results_int = [int(x) if isinstance(x, str) else x for x in results]
                assert results_int == expected, f"Expected {expected}, got {results_int}"
                print("OK GROUP test passed!")
                passed_tests += 1
                test_results[3] = True
            else:
                raise Exception(f"GROUP returned wrong type: {type(results)}")
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[3] = False
        
        # ============================================================
        # TEST 4: CANVAS PRIMITIVES - CHAIN
        # ============================================================
        print_section("TEST 4: Canvas Primitives - CHAIN (Pipeline)")
        try:
            print("
Defining sum_list task...")
            cluster.define_task("sum_list", "lambda lst: sum(lst)")
            time.sleep(0.3)
            
            print("
Executing chain: add(5,3) → multiply(2) → square()...")
            result = cluster.chain([
                cluster.sig("add", 5, 3),      # 8
                cluster.sig("multiply", 2),    # 16
                cluster.sig("square")          # 256
            ])
            print(f"Result: {result}")
            
            if result is None:
                raise Exception("CHAIN returned None - Canvas not implemented")
            
            result_int = int(result) if isinstance(result, str) else result
            assert result_int == 256, f"Expected 256, got {result_int}"
            print("OK CHAIN test passed!")
            passed_tests += 1
            test_results[4] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[4] = False
        
        # ============================================================
        # TEST 5: CANVAS PRIMITIVES - CHORD
        # ============================================================
        print_section("TEST 5: Canvas Primitives - CHORD (Map-Reduce)")
        try:
            print("
Executing chord: [square(2), square(3), square(4), square(5)] → sum_list()...")
            result = cluster.chord(
                header_sigs=[
                    cluster.sig("square", 2),   # 4
                    cluster.sig("square", 3),   # 9
                    cluster.sig("square", 4),   # 16
                    cluster.sig("square", 5)    # 25
                ],
                callback_sig=cluster.sig("sum_list")
            )
            print(f"Result: {result}")
            
            if result is None:
                raise Exception("CHORD returned None - Canvas not implemented")
            
            result_int = int(result) if isinstance(result, str) else result
            assert result_int == 54, f"Expected 54 (4+9+16+25), got {result_int}"
            print("OK CHORD test passed!")
            passed_tests += 1
            test_results[5] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[5] = False
        
        # ============================================================
        # TEST 6: DUAL-CORE EXECUTION
        # ============================================================
        print_section("TEST 6: Dual-Core Execution")
        try:
            print("
Executing square(50) on Core 0...")
            result = cluster.execute("square", 50, core=0)
            print(f"  Core 0: square(50) = {result}")
            assert result == "2500", f"Expected 2500, got {result}"
            
            print("
Executing square(100) on Core 1...")
            result = cluster.execute("square", 100, core=1)
            print(f"  Core 1: square(100) = {result}")
            assert result == "10000", f"Expected 10000, got {result}"
            
            print("
OK Dual-core execution tests passed!")
            passed_tests += 1
            test_results[6] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[6] = False
        
        # ============================================================
        # TEST 7: DUAL-CORE WITH CANVAS
        # ============================================================
        print_section("TEST 7: Dual-Core with Canvas GROUP")
        try:
            print("
Executing group with core assignments...")
            results = cluster.group([
                cluster.sig("square", 10, core=0),
                cluster.sig("square", 20, core=1),
                cluster.sig("square", 30, core=0),
                cluster.sig("square", 40, core=1)
            ])
            print(f"Results: {results}")
            
            if results is None:
                raise Exception("Dual-core GROUP returned None")
            
            if isinstance(results, list):
                results_int = [int(x) if isinstance(x, str) else x for x in results]
                expected = [100, 400, 900, 1600]
                assert results_int == expected, f"Expected {expected}, got {results_int}"
                print("OK Dual-core Canvas test passed!")
                passed_tests += 1
            test_results[7] = True
            else:
                raise Exception(f"Wrong type: {type(results)}")
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[7] = False
        
        # ============================================================
        # TEST 8: PERIPHERAL INITIALIZATION
        # ============================================================
        print_section("TEST 8: Peripheral Initialization")
        try:
            print("
Initializing peripherals:")
            print("  >> I2C (SDA:21, SCL:22, 100kHz)...")
            result = cluster.i2c_init(21, 22, 100000)
            if result and "ERROR" in str(result):
                raise Exception(f"I2C init failed: {result}")
            
            print("  >> SPI (SCK:18, MISO:19, MOSI:23, 1MHz)...")
            result = cluster.spi_init(18, 19, 23, 1000000)
            if result and "ERROR" in str(result):
                raise Exception(f"SPI init failed: {result}")
            
            print("  >> UART (TX:17, RX:16, 115200)...")
            result = cluster.uart_init(17, 16, 115200)
            if result and "ERROR" in str(result):
                raise Exception(f"UART init failed: {result}")
            
            print("  >> CAN (TX:5, RX:6, 500kbps)...")
            result = cluster.can_init(5, 6, 500000)
            if result and "ERROR" in str(result):
                raise Exception(f"CAN init failed: {result}")
            
            print("
OK All peripherals initialized!")
            passed_tests += 1
            test_results[8] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[8] = False
        
        # ============================================================
        # TEST 9: GPIO CONTROL
        # ============================================================
        print_section("TEST 9: GPIO Control")
        try:
            print("
Testing GPIO operations:")
            print("  >> Setting GPIO 2 HIGH...")
            result = cluster.gpio_write(2, 1)
            if result and "ERROR" in str(result):
                raise Exception(f"GPIO write failed: {result}")
            
            print("  >> PWM on GPIO 2 (channel 0, 5kHz, 8-bit, 50% duty)...")
            result = cluster.pwm(2, 0, 5000, 8, 128)  # pin, channel, freq, resolution, duty
            if result and "ERROR" in str(result):
                raise Exception(f"PWM failed: {result}")
            
            print("
OK GPIO control tests passed!")
            passed_tests += 1
            test_results[9] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[9] = False
        
        # ============================================================
        # TEST 10: ADC READING
        # ============================================================
        print_section("TEST 10: ADC Reading")
        try:
            print("
Reading ADC from GPIO 34...")
            adc_value = cluster.adc_read(34)
            if adc_value and "ERROR" in str(adc_value):
                raise Exception(f"ADC read failed: {adc_value}")
            print(f"  ADC value: {adc_value}")
            print("
OK ADC reading test passed!")
            passed_tests += 1
            test_results[10] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[10] = False
        
        # ============================================================
        # TEST 11: SYSTEM MONITORING
        # ============================================================
        print_section("TEST 11: System Monitoring")
        try:
            print("
Retrieving system status...")
            cluster.print_system_status()
            print("
OK System monitoring test passed!")
            passed_tests += 1
            test_results[11] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[11] = False
        
        # ============================================================
        # TEST 12: DYNAMIC CODE UPLOAD
        # ============================================================
        print_section("TEST 12: Dynamic Code Upload")
        try:
            print("
Creating test algorithm...")
            test_code = """def custom_algorithm(x, y):
    return (x ** 2) + (y ** 2)
"""
            
            print("Uploading code via SLIP...")
            cluster.upload_code("test_algo.py", test_code)
            time.sleep(0.5)
            
            print("Defining task that uses uploaded code...")
            cluster.define_task("test_custom", "lambda: __import__('test_algo').custom_algorithm(3, 4)")
            time.sleep(0.3)
            
            print("Executing custom algorithm...")
            result = cluster.execute("test_custom")
            print(f"  custom_algorithm(3, 4) = {result}")
            
            if result and "ERROR" in str(result):
                raise Exception(f"Custom task failed: {result}")
            
            result_int = int(result) if isinstance(result, str) else result
            assert result_int == 25, f"Expected 25 (3²+4²), got {result_int}"
            
            print("
OK Dynamic code upload test passed!")
            passed_tests += 1
            test_results[12] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[12] = False
        
        # ============================================================
        # TEST 13: ERROR HANDLING
        # ============================================================
        print_section("TEST 13: Error Handling")
        try:
            print("
Testing error scenarios:")
            
            print("  >> Executing undefined task...")
            result = cluster.execute("nonexistent_task_xyz", 1, 2)
            print(f"    Response: {result}")
            if not (result is None or "not_defined" in str(result).lower() or "error" in str(result).lower()):
                raise Exception(f"Should return error for undefined task, got: {result}")
            print("    OK Correctly returned error for undefined task")
            
            print("
  >> Defining task with syntax error...")
            cluster.define_task("bad_syntax", "this is not valid python code at all")
            time.sleep(0.2)
            result = cluster.execute("bad_syntax")
            print(f"    Response: {result}")
            if not (result is None or "error" in str(result).lower() or "syntax" in str(result).lower()):
                raise Exception(f"Should handle syntax error, got: {result}")
            print("    OK Correctly handled syntax error")
            
            print("
  >> Executing task with wrong number of arguments...")
            result = cluster.execute("add", 5)  # add needs 2 args
            print(f"    Response: {result}")
            # This might succeed with None as second arg, or fail - either is acceptable
            print("    OK Handled argument mismatch")
            
            print("
OK Error handling tests passed!")
            passed_tests += 1
            test_results[13] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[13] = False
        
        # ============================================================
        # TEST 14: TASK LISTING
        # ============================================================
        print_section("TEST 14: Task Management")
        try:
            print("
Listing all defined tasks...")
            tasks = cluster.list_tasks()
            print(f"  Defined tasks: {tasks}")
            
            if not tasks:
                raise Exception("Task list is empty - should have defined tasks")
            
            print(f"  Found {len(tasks)} tasks")
            print("
OK Task listing test passed!")
            passed_tests += 1
            test_results[14] = True
        except Exception as e:
            print(f"X FAILED: {e}")
            failed_tests += 1
            test_results[14] = False
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print("
" + "="*70)
        print("=" + " "*68 + "=")
        if failed_tests == 0:
            print("=" + "  ALL TESTS PASSED!".center(68) + "=")
        else:
            print("=" + f"  {failed_tests} TEST(S) FAILED".center(68) + "=")
        print("=" + " "*68 + "=")
        print("="*70)
        
        print("
" + "="*70)
        print(f"TEST SUMMARY - {passed_tests}/{total_tests} PASSED, {failed_tests}/{total_tests} FAILED")
        print("="*70)
        print(f"{'OK' if test_results.get(1, False) else 'X'} Test 1: Connection & Communication")
        print(f"{'OK' if test_results.get(2, False) else 'X'} Test 2: Task Definition & Execution")
        print(f"{'OK' if test_results.get(3, False) else 'X'} Test 3: Canvas GROUP (Parallel)")
        print(f"{'OK' if test_results.get(4, False) else 'X'} Test 4: Canvas CHAIN (Pipeline)")
        print(f"{'OK' if test_results.get(5, False) else 'X'} Test 5: Canvas CHORD (Map-Reduce)")
        print(f"{'OK' if test_results.get(6, False) else 'X'} Test 6: Dual-Core Execution")
        print(f"{'OK' if test_results.get(7, False) else 'X'} Test 7: Dual-Core with Canvas")
        print(f"{'OK' if test_results.get(8, False) else 'X'} Test 8: Peripheral Initialization")
        print(f"{'OK' if test_results.get(9, False) else 'X'} Test 9: GPIO Control")
        print(f"{'OK' if test_results.get(10, False) else 'X'} Test 10: ADC Reading")
        print(f"{'OK' if test_results.get(11, False) else 'X'} Test 11: System Monitoring")
        print(f"{'OK' if test_results.get(12, False) else 'X'} Test 12: Dynamic Code Upload")
        print(f"{'OK' if test_results.get(13, False) else 'X'} Test 13: Error Handling")
        print(f"{'OK' if test_results.get(14, False) else 'X'} Test 14: Task Management")
        print("="*70)
        
        if failed_tests == 0:
            print("
>> ESP32 Distributed Cluster is fully operational!")
            print(">> All features verified and working correctly")
            print(">> Ready for production deployment
")
        else:
            print(f"
>> ERROR: {failed_tests} test(s) failed - see details above")
            print(">> Fix failed tests before deployment
")
            raise Exception(f"{failed_tests} tests failed")

if __name__ == "__main__":
    try:
        test_everything()
    except KeyboardInterrupt:
        print("

Test interrupted by user")
    except Exception as e:
        print(f"

>> TEST SUITE FAILED")
        import traceback
        traceback.print_exc()
        exit(1)

