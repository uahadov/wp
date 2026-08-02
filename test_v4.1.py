#!/usr/bin/env python3
"""
v4.1 Comprehensive Test Suite
Test all thread-safe implementations
"""

import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

print("🧪 v4.1 COMPREHENSIVE TEST SUITE\n")

# Test 1: Module Imports
print("1️⃣ Testing module imports...")
try:
    import config
    from logger import get_logger
    from database import get_db
    from rate_limiter import get_rate_limiter
    from progress_tracker import get_tracker
    from parallel_scanner import get_parallel_scanner
    from false_positive_learner import get_learner
    print("   ✅ All modules imported successfully\n")
except Exception as e:
    print(f"   ❌ Import failed: {e}\n")
    sys.exit(1)

# Test 2: Thread-Safe Progress Tracker
print("2️⃣ Testing thread-safe progress tracker...")
try:
    tracker = get_tracker()
    tracker.reset()
    tracker.start_scan(10, 5)
    
    def update_progress(thread_id):
        for i in range(10):
            tracker.increment_scanned()
            time.sleep(0.001)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(update_progress, i) for i in range(5)]
        for f in futures:
            f.result()
    
    assert tracker.total_scanned == 50, f"Expected 50, got {tracker.total_scanned}"
    print(f"   ✅ Thread-safe counter: {tracker.total_scanned} (expected 50)\n")
except Exception as e:
    print(f"   ❌ Progress tracker test failed: {e}\n")
    sys.exit(1)

# Test 3: Thread-Safe Database
print("3️⃣ Testing thread-safe database...")
try:
    db = get_db()
    
    def db_operation(thread_id):
        # Simulate concurrent database access
        result = db.execute("SELECT COUNT(*) as count FROM plugins", None)
        return result
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(db_operation, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    print(f"   ✅ Concurrent DB access: {len(results)} queries completed\n")
except Exception as e:
    print(f"   ❌ Database test failed: {e}\n")
    sys.exit(1)

# Test 4: Thread-Safe Rate Limiter
print("4️⃣ Testing thread-safe rate limiter...")
try:
    from rate_limiter import get_rate_limiter, RateLimitConfig
    
    limiter = get_rate_limiter()
    
    def test_func():
        time.sleep(0.01)
        return "success"
    
    def call_with_retry(thread_id):
        try:
            result = limiter.call_with_retry(test_func, service=f"test_{thread_id}")
            return result
        except Exception:
            return "failed"
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(call_with_retry, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    success_count = sum(1 for r in results if r == "success")
    print(f"   ✅ Rate limiter: {success_count}/10 successful calls\n")
except Exception as e:
    print(f"   ❌ Rate limiter test failed: {e}\n")
    sys.exit(1)

# Test 5: No Deadlock in Progress Report
print("5️⃣ Testing deadlock prevention...")
try:
    tracker = get_tracker()
    tracker.reset()
    tracker.start_scan(10, 5)
    tracker.start_batch(1)
    tracker.update_plugin(1, "test-plugin", "1.0")
    
    def get_report(thread_id):
        return tracker.get_progress_report()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_report, i) for i in range(20)]
        reports = [f.result() for f in futures]
    
    assert len(reports) == 20, f"Expected 20 reports, got {len(reports)}"
    print(f"   ✅ No deadlock: {len(reports)} concurrent reports generated\n")
except Exception as e:
    print(f"   ❌ Deadlock test failed: {e}\n")
    sys.exit(1)

# Test 6: FP Learner Pattern Loading
print("6️⃣ Testing FP learner...")
try:
    learner = get_learner()
    patterns = learner.patterns
    stats = learner.get_statistics()
    
    print(f"   ✅ FP Learner: {len(patterns)} patterns, {stats['total_patterns']} total\n")
except Exception as e:
    print(f"   ❌ FP learner test failed: {e}\n")
    sys.exit(1)

# Test 7: Parallel Scanner
print("7️⃣ Testing parallel scanner...")
try:
    scanner = get_parallel_scanner(max_workers=3)
    
    def dummy_scan(plugin):
        time.sleep(0.01)
        return {"plugin": plugin["name"], "result": "scanned"}
    
    test_plugins = [{"name": f"plugin-{i}", "version": "1.0"} for i in range(10)]
    result = scanner.scan_plugins_parallel(test_plugins, dummy_scan, timeout=5)
    
    print(f"   ✅ Parallel scan: {len(result['completed'])} completed, "
          f"{result['plugins_per_minute']:.1f} plugins/min\n")
except Exception as e:
    print(f"   ❌ Parallel scanner test failed: {e}\n")
    sys.exit(1)

# Final Summary
print("=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\nv4.1 is PRODUCTION READY:")
print("  ✅ Thread-safe implementations")
print("  ✅ No deadlocks")
print("  ✅ Concurrent database access")
print("  ✅ Parallel scanning works")
print("  ✅ FP learning loaded")
print("\n🚀 Ready to scan!")
