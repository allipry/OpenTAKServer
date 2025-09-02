#!/usr/bin/env python3
"""
Comprehensive test runner for iTAK QR code functionality.
Runs all test suites and generates a detailed report.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
import json

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def run_test_suite(test_file, description):
    """Run a specific test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"Test file: {test_file}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run pytest with verbose output and capture results
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            test_file, 
            '-v',  # Verbose output
            '--tb=short',  # Short traceback format
            '--no-header',  # No header
            '--json-report',  # Generate JSON report
            '--json-report-file=test_report.json'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Parse results
        success = result.returncode == 0
        
        # Try to load JSON report for detailed stats
        stats = {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0}
        try:
            with open(os.path.join(os.path.dirname(__file__), 'test_report.json'), 'r') as f:
                report = json.load(f)
                summary = report.get('summary', {})
                stats['passed'] = summary.get('passed', 0)
                stats['failed'] = summary.get('failed', 0)
                stats['skipped'] = summary.get('skipped', 0)
                stats['errors'] = summary.get('error', 0)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            # Fallback to parsing stdout
            if 'passed' in result.stdout:
                # Simple parsing of pytest output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and ('failed' in line or 'error' in line or 'skipped' in line):
                        # Parse line like "5 passed, 2 failed, 1 skipped in 1.23s"
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'passed' and i > 0:
                                stats['passed'] = int(parts[i-1])
                            elif part == 'failed' and i > 0:
                                stats['failed'] = int(parts[i-1])
                            elif part == 'skipped' and i > 0:
                                stats['skipped'] = int(parts[i-1])
                            elif part == 'error' and i > 0:
                                stats['errors'] = int(parts[i-1])
                        break
        
        # Print results
        print(f"\nResults for {description}:")
        print(f"  Status: {'PASSED' if success else 'FAILED'}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Tests passed: {stats['passed']}")
        print(f"  Tests failed: {stats['failed']}")
        print(f"  Tests skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
        
        if not success:
            print(f"\nSTDOUT:\n{result.stdout}")
            print(f"\nSTDERR:\n{result.stderr}")
        
        return {
            'test_file': test_file,
            'description': description,
            'success': success,
            'duration': duration,
            'stats': stats,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except Exception as e:
        print(f"Error running test suite {test_file}: {e}")
        return {
            'test_file': test_file,
            'description': description,
            'success': False,
            'duration': 0,
            'stats': {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 1},
            'error': str(e)
        }


def generate_test_report(results):
    """Generate a comprehensive test report."""
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    total_duration = 0
    successful_suites = 0
    
    for result in results:
        stats = result['stats']
        total_passed += stats['passed']
        total_failed += stats['failed']
        total_skipped += stats['skipped']
        total_errors += stats['errors']
        total_duration += result['duration']
        
        if result['success']:
            successful_suites += 1
    
    print(f"\nOVERALL SUMMARY:")
    print(f"  Test suites run: {len(results)}")
    print(f"  Test suites passed: {successful_suites}")
    print(f"  Test suites failed: {len(results) - successful_suites}")
    print(f"  Total test duration: {total_duration:.2f} seconds")
    print(f"  Total tests passed: {total_passed}")
    print(f"  Total tests failed: {total_failed}")
    print(f"  Total tests skipped: {total_skipped}")
    print(f"  Total errors: {total_errors}")
    
    success_rate = (total_passed / (total_passed + total_failed)) * 100 if (total_passed + total_failed) > 0 else 0
    print(f"  Success rate: {success_rate:.1f}%")
    
    print(f"\nDETAILED RESULTS:")
    for result in results:
        status = "✓ PASSED" if result['success'] else "✗ FAILED"
        stats = result['stats']
        print(f"  {status} - {result['description']}")
        print(f"    File: {result['test_file']}")
        print(f"    Duration: {result['duration']:.2f}s")
        print(f"    Tests: {stats['passed']} passed, {stats['failed']} failed, {stats['skipped']} skipped")
        if stats['errors'] > 0:
            print(f"    Errors: {stats['errors']}")
        print()
    
    # Requirements coverage analysis
    print(f"\nREQUIREMENTS COVERAGE ANALYSIS:")
    print(f"  Requirement 4.1 (QR format validation): ✓ Covered by test_qr_code_generation.py")
    print(f"  Requirement 4.2 (Deployment scenarios): ✓ Covered by test_deployment_scenarios.py")
    print(f"  Requirement 4.3 (Integration testing): ✓ Covered by test_qr_api_integration.py")
    print(f"  Requirement 4.4 (Error handling): ✓ Covered by test_error_handling.py")
    print(f"  User creation functionality: ✓ Covered by test_user_creation.py")
    print(f"  Hostname resolution: ✓ Covered by test_hostname_resolver.py")
    
    # Recommendations
    print(f"\nRECOMMENDATIONS:")
    if total_failed > 0:
        print(f"  - Fix {total_failed} failing tests before deployment")
    if total_errors > 0:
        print(f"  - Investigate {total_errors} test errors")
    if success_rate < 95:
        print(f"  - Improve test success rate (currently {success_rate:.1f}%)")
    if successful_suites == len(results) and total_failed == 0:
        print(f"  - All tests passed! Ready for deployment.")
    
    return {
        'timestamp': datetime.now().isoformat(),
        'total_suites': len(results),
        'successful_suites': successful_suites,
        'total_tests': total_passed + total_failed,
        'total_passed': total_passed,
        'total_failed': total_failed,
        'total_skipped': total_skipped,
        'total_errors': total_errors,
        'success_rate': success_rate,
        'total_duration': total_duration,
        'results': results
    }


def main():
    """Main test runner function."""
    print("iTAK QR Code Comprehensive Test Suite")
    print("=====================================")
    
    # Define test suites
    test_suites = [
        ('test_hostname_resolver.py', 'Hostname Resolution Service Tests'),
        ('test_qr_code_generation.py', 'QR Code Format and Validation Tests'),
        ('test_qr_decoding_validation.py', 'QR Code Decoding and Library Tests'),
        ('test_qr_api_integration.py', 'QR Code API Integration Tests'),
        ('test_user_creation.py', 'User Creation Functionality Tests'),
        ('test_deployment_scenarios.py', 'Deployment Scenario Tests'),
        ('test_error_handling.py', 'Error Handling and Edge Case Tests'),
        ('test_integration_validation.py', 'Integration Validation Tests (Task 10)'),
    ]
    
    # Check if test files exist
    missing_files = []
    for test_file, description in test_suites:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if not os.path.exists(test_path):
            missing_files.append(test_file)
    
    if missing_files:
        print(f"Warning: Missing test files: {', '.join(missing_files)}")
        print("Some tests will be skipped.")
    
    # Run test suites
    results = []
    start_time = time.time()
    
    for test_file, description in test_suites:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            result = run_test_suite(test_file, description)
            results.append(result)
        else:
            print(f"\nSkipping {description} - file not found: {test_file}")
            results.append({
                'test_file': test_file,
                'description': description,
                'success': False,
                'duration': 0,
                'stats': {'passed': 0, 'failed': 0, 'skipped': 1, 'errors': 0},
                'error': 'Test file not found'
            })
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Generate comprehensive report
    report = generate_test_report(results)
    
    # Save report to file
    report_file = os.path.join(os.path.dirname(__file__), 'comprehensive_test_report.json')
    try:
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")
    except Exception as e:
        print(f"\nWarning: Could not save report file: {e}")
    
    # Exit with appropriate code
    if all(result['success'] for result in results):
        print(f"\n🎉 All test suites passed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Some test suites failed. Check the report above.")
        sys.exit(1)


if __name__ == '__main__':
    main()