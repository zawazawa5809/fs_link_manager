"""Test runner with coverage report for FS Link Manager"""

import sys
import os
import unittest
import logging

# Suppress debug logs during testing
logging.disable(logging.CRITICAL)

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests_with_coverage():
    """Run all tests with coverage reporting"""
    try:
        import coverage
        has_coverage = True
    except ImportError:
        has_coverage = False
        print("Coverage module not installed. Running tests without coverage.")
        print("Install with: pip install coverage\n")

    if has_coverage:
        # Initialize coverage
        cov = coverage.Coverage(source=['fs_link_manager'])
        cov.start()

    # Discover and run tests
    loader = unittest.TestLoader()
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(test_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if has_coverage:
        # Stop coverage and print report
        cov.stop()
        print("\n" + "="*70)
        print("COVERAGE REPORT")
        print("="*70)
        cov.report()

        # Save HTML report
        html_dir = os.path.join(os.path.dirname(__file__), 'htmlcov')
        cov.html_report(directory=html_dir)
        print(f"\nDetailed HTML coverage report saved to: {html_dir}")

    return result.wasSuccessful()


def run_tests_simple():
    """Run tests without coverage (fallback)"""
    loader = unittest.TestLoader()
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(test_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    """Main entry point"""
    print("FS Link Manager - Test Suite")
    print("="*70)

    # Check if coverage is requested
    if '--coverage' in sys.argv or '-c' in sys.argv:
        success = run_tests_with_coverage()
    else:
        success = run_tests_simple()
        print("\nTip: Run with --coverage flag to generate coverage report")

    # Print final status
    print("\n" + "="*70)
    if success:
        print("✅ All tests passed successfully!")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())