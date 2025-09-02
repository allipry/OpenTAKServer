# iTAK QR Code Testing Suite

This directory contains comprehensive tests for the iTAK QR code generation functionality, covering all requirements specified in the design document.

## Test Files Overview

### Core Test Suites

1. **`test_hostname_resolver.py`** - Unit tests for hostname resolution service
   - Tests environment variable detection
   - Tests external IP detection with mocked services
   - Tests localhost detection and validation
   - Tests hostname override functionality
   - Tests caching and timeout behavior
   - **Requirements covered**: 4.1, 4.2, 4.3, 4.4

2. **`test_qr_code_generation.py`** - QR code format validation and iTAK compatibility
   - Tests iTAK QR code format compliance
   - Tests parameter encoding and special characters
   - Tests QR string length validation
   - Tests compatibility with QR code libraries
   - **Requirements covered**: 4.1, 4.3, 4.4

3. **`test_qr_api_integration.py`** - Integration tests for QR code API endpoints
   - Tests GET and POST endpoints
   - Tests parameter validation
   - Tests hostname resolution integration
   - Tests user creation integration
   - Tests error handling and response formats
   - **Requirements covered**: 4.1, 4.2, 4.3, 4.4

4. **`test_user_creation.py`** - User creation functionality tests
   - Tests username and password validation
   - Tests user role validation
   - Tests successful user creation scenarios
   - Tests error handling for database failures
   - Tests concurrent user creation
   - **Requirements covered**: 4.1, 4.3, 4.4

5. **`test_deployment_scenarios.py`** - Different deployment environment tests
   - Tests localhost development environment
   - Tests Docker container scenarios
   - Tests external IP detection scenarios
   - Tests production environment variables
   - Tests reverse proxy and load balancer scenarios
   - Tests cloud and Kubernetes deployments
   - **Requirements covered**: 4.2, 4.3, 4.4

6. **`test_error_handling.py`** - Error handling and edge case tests
   - Tests None and empty input handling
   - Tests invalid hostname formats
   - Tests external service failures
   - Tests cache corruption handling
   - Tests Unicode and special character handling
   - Tests memory pressure scenarios
   - **Requirements covered**: 4.1, 4.4

7. **`test_qr_decoding_validation.py`** - QR code decoding and library compatibility tests
   - Tests QR code generation with standard libraries (qrcode, PIL)
   - Tests QR code data capacity and version handling
   - Tests special character encoding in QR codes
   - Tests QR code image generation and properties
   - Tests performance with large data sets
   - **Requirements covered**: 4.3, 4.4

### Utility Files

- **`validate_tests.py`** - Simple validation script that runs without external dependencies
- **`qr_validation_utils.py`** - Comprehensive QR code validation utilities and hostname accessibility testing
- **`run_comprehensive_tests.py`** - Comprehensive test runner with detailed reporting
- **`conftest.py`** - Pytest configuration and fixtures (requires Flask dependencies)
- **`README.md`** - This documentation file

### Configuration Files

- **`../pytest.ini`** - Pytest configuration with markers and options

## Requirements Coverage

The test suite covers all requirements from the design document:

### Requirement 4.1 - QR Format Validation
- ✅ **Covered by**: `test_qr_code_generation.py`, `test_error_handling.py`
- Tests exact iTAK URL format compliance
- Tests parameter validation and encoding
- Tests QR string length limits
- Tests compatibility with QR code libraries

### Requirement 4.2 - Deployment Scenarios
- ✅ **Covered by**: `test_deployment_scenarios.py`, `test_hostname_resolver.py`
- Tests localhost development environment
- Tests Docker container scenarios
- Tests external IP detection
- Tests production environment variables
- Tests reverse proxy and load balancer scenarios
- Tests cloud deployments (AWS, Kubernetes)

### Requirement 4.3 - Integration Testing
- ✅ **Covered by**: `test_qr_api_integration.py`, `test_user_creation.py`
- Tests complete QR code generation flow
- Tests API endpoint integration
- Tests user creation functionality
- Tests hostname resolution integration
- Tests error recovery mechanisms

### Requirement 4.4 - Error Handling and Edge Cases
- ✅ **Covered by**: `test_error_handling.py`, all test files
- Tests invalid input handling
- Tests network failure scenarios
- Tests service timeout handling
- Tests malformed data handling
- Tests concurrent access scenarios

## Running Tests

### Quick Validation (No Dependencies)
```bash
python OpenTAKServer/tests/validate_tests.py
```

### Individual Test Suites (Requires pytest)
```bash
# Run specific test file
python -m pytest OpenTAKServer/tests/test_hostname_resolver.py -v

# Run with specific markers
python -m pytest OpenTAKServer/tests/ -m "unit" -v

# Run all tests
python -m pytest OpenTAKServer/tests/ -v
```

### Comprehensive Test Suite
```bash
python OpenTAKServer/tests/run_comprehensive_tests.py
```

## Test Categories

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.deployment` - Deployment scenario tests
- `@pytest.mark.error_handling` - Error handling tests
- `@pytest.mark.network` - Tests requiring network access
- `@pytest.mark.slow` - Slow running tests

## Dependencies

### Required for Basic Testing
- Python 3.7+
- `urllib.parse` (standard library)
- `unittest.mock` (standard library)

### Required for Full Test Suite
- `pytest` - Test framework
- `pytest-json-report` - JSON test reporting
- `requests` - HTTP library (for hostname resolver)

### Optional Dependencies
- `qrcode` - QR code generation library (for QR code validation tests)
- `PIL` - Image processing (for QR code tests)
- `flask` - Web framework (for API integration tests)
- `flask-security` - Security extensions (for user creation tests)

## Test Data and Mocking

The test suite uses extensive mocking to avoid external dependencies:

- **Network requests** are mocked using `unittest.mock.patch`
- **External IP services** are mocked with configurable responses
- **Database operations** are mocked for user creation tests
- **Environment variables** are patched for configuration tests

## Continuous Integration

The test suite is designed to run in CI/CD environments:

- Tests are deterministic and don't rely on external services
- Network timeouts are configurable
- Tests can run in parallel
- Comprehensive reporting is available in JSON format

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the OpenTAKServer directory is in Python path
2. **Missing Dependencies**: Install required packages or use `validate_tests.py`
3. **Network Tests Failing**: Check if external IP services are accessible
4. **Timeout Issues**: Adjust timeout values in environment variables

### Debug Mode

Run tests with verbose output and debug information:
```bash
python -m pytest OpenTAKServer/tests/ -v -s --tb=long
```

### Test Coverage

To generate test coverage reports (requires pytest-cov):
```bash
python -m pytest OpenTAKServer/tests/ --cov=opentakserver --cov-report=html
```

## Contributing

When adding new tests:

1. Follow the existing naming convention (`test_*.py`)
2. Add appropriate pytest markers
3. Include docstrings explaining test purpose
4. Mock external dependencies
5. Update this README if adding new test categories
6. Ensure tests are deterministic and can run in any order

## Test Results

The comprehensive test suite generates detailed reports including:

- Test execution time
- Pass/fail statistics
- Requirements coverage analysis
- Deployment readiness assessment
- Recommendations for improvements

Example output:
```
COMPREHENSIVE TEST REPORT
Generated: 2025-01-27 10:30:00
=====================================

OVERALL SUMMARY:
  Test suites run: 6
  Test suites passed: 6
  Total tests passed: 45
  Total tests failed: 0
  Success rate: 100.0%
  
REQUIREMENTS COVERAGE ANALYSIS:
  Requirement 4.1 (QR format validation): ✓ Covered
  Requirement 4.2 (Deployment scenarios): ✓ Covered
  Requirement 4.3 (Integration testing): ✓ Covered
  Requirement 4.4 (Error handling): ✓ Covered

RECOMMENDATIONS:
  - All tests passed! Ready for deployment.
```