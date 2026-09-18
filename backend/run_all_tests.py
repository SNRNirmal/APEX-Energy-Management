"""
APEX-Energy — Master Test Suite Runner
======================================
Executes all regression and integration test suites from Phase 1 through Phase 6:
- Phase 1: test_apex_dataset.py (9 tests)
- Phase 2: test_apex_forecast.py (7 tests)
- Phase 3: test_apex_decision_engine.py (7 tests)
- Phase 4: test_apex_verification.py (9 tests)
- Phase 5: test_apex_evaluation.py (9 tests)
- Legacy:  test_backend.py (14 tests)
- Phase 6: test_apex_dashboard_api.py (8 tests)

Total Target: 63 tests (0 failures, 0 errors).
"""

import sys
import os
import unittest

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def run_master_test_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_modules = [
        "test_apex_dataset",
        "test_apex_forecast",
        "test_apex_decision_engine",
        "test_apex_verification",
        "test_apex_evaluation",
        "test_backend",
        "test_apex_dashboard_api",
        "test_apex_phase7_stress"
    ]

    print("=" * 70)
    print("APEX-Energy: Running Complete Regression & Phase 7 Test Suites")
    print("=" * 70)

    for mod_name in test_modules:
        mod = __import__(mod_name)
        tests = loader.loadTestsFromModule(mod)
        suite.addTests(tests)
        print(f"Loaded {tests.countTestCases():2d} tests from {mod_name}.py")

    print("-" * 70)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    print(f"SUMMARY:")
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Failures:       {len(result.failures)}")
    print(f"Errors:         {len(result.errors)}")
    print(f"Status:         {'SUCCESS / PASS' if result.wasSuccessful() else 'FAIL'}")
    print("=" * 70)

    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_master_test_suite()
    sys.exit(0 if success else 1)
