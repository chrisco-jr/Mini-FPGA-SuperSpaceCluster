import os
from broccoli_cluster import BroccoliCluster

# Use environment variable or default port
PORT = os.environ.get("BROCCOLI_PORT", "COM25")

with BroccoliCluster(PORT) as cluster:
    # Test simple dynamic code
    test_code = '''
def test_func():
    return "hello_world"

result = test_func()
'''
    
    print("Uploading test code...")
    cluster.upload_code('test.py', test_code)
    
    print("Defining task...")
    cluster.define_task('test_task', """lambda: (
        lambda g=globals(): [
            exec(open('test.py').read(), g),
            g.get('result', 'no_result')
        ][-1]
    )()""")
    
    print("Executing...")
    result = cluster.execute('test_task')
    print(f"Result: {result}")
    
    # Clean up
    cluster.define_task('cleanup', 'lambda: __import__("os").remove("test.py") or "cleaned"')
    cleanup_result = cluster.execute('cleanup')
    print(f"Cleanup: {cleanup_result}")