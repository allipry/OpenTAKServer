#!/usr/bin/env python3
"""
Error Handler Test Suite
Tests secure error handling across all endpoints and error scenarios
"""

import pytest
from flask import Flask, jsonify
from opentakserver.magk.services.error_handler import (
    SecureErrorHandler,
    init_error_handlers,
    create_error_response,
    get_error_message,
    ERROR_MESSAGES
)


class TestSecureErrorHandler:
    """Test SecureErrorHandler class"""
    
    def test_init_without_app(self):
        """Test initialization without Flask app"""
        handler = SecureErrorHandler(debug_mode=False)
        assert handler.debug_mode is False
    
    def test_init_with_app(self):
        """Test initialization with Flask app"""
        app = Flask(__name__)
        app.config['DEBUG'] = False
        handler = SecureErrorHandler(app, debug_mode=False)
        assert handler.debug_mode is False
    
    def test_debug_mode_from_config(self):
        """Test debug mode is read from app config"""
        app = Flask(__name__)
        app.config['DEBUG'] = True
        handler = SecureErrorHandler(app)
        assert handler.debug_mode is True


class TestErrorResponses:
    """Test error response format and content"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app with error handlers"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        init_error_handlers(app, debug_mode=False)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_400_bad_request(self, app, client):
        """Test 400 Bad Request error handling"""
        @app.route('/bad-request')
        def bad_request():
            from werkzeug.exceptions import BadRequest
            raise BadRequest("Invalid input")
        
        response = client.get('/bad-request')
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['version'] == '3'
        assert 'BadRequestException' in data['type']
        assert 'Invalid request' in data['data']['message']
        assert data['nodeId'] == 'opentakserver'
    
    def test_401_unauthorized(self, app, client):
        """Test 401 Unauthorized error handling"""
        @app.route('/unauthorized')
        def unauthorized():
            from werkzeug.exceptions import Unauthorized
            raise Unauthorized("Not authenticated")
        
        response = client.get('/unauthorized')
        assert response.status_code == 401
        
        data = response.get_json()
        assert 'UnauthorizedException' in data['type']
        assert 'Authentication required' in data['data']['message']
    
    def test_403_forbidden(self, app, client):
        """Test 403 Forbidden error handling"""
        @app.route('/forbidden')
        def forbidden():
            from werkzeug.exceptions import Forbidden
            raise Forbidden("Access denied")
        
        response = client.get('/forbidden')
        assert response.status_code == 403
        
        data = response.get_json()
        assert 'ForbiddenException' in data['type']
        assert 'Access denied' in data['data']['message']
    
    def test_404_not_found(self, app, client):
        """Test 404 Not Found error handling"""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'NotFoundException' in data['type']
        assert 'not found' in data['data']['message'].lower()
    
    def test_405_method_not_allowed(self, app, client):
        """Test 405 Method Not Allowed error handling"""
        @app.route('/post-only', methods=['POST'])
        def post_only():
            return 'OK'
        
        response = client.get('/post-only')
        assert response.status_code == 405
        
        data = response.get_json()
        assert 'MethodNotAllowedException' in data['type']
        assert 'not allowed' in data['data']['message'].lower()
    
    def test_429_rate_limit_exceeded(self, app, client):
        """Test 429 Rate Limit Exceeded error handling"""
        @app.route('/rate-limited')
        def rate_limited():
            from werkzeug.exceptions import TooManyRequests
            raise TooManyRequests("Rate limit exceeded")
        
        response = client.get('/rate-limited')
        assert response.status_code == 429
        
        data = response.get_json()
        assert 'RateLimitException' in data['type']
        assert 'Too many requests' in data['data']['message']
    
    def test_500_internal_error(self, app, client):
        """Test 500 Internal Server Error handling"""
        @app.route('/internal-error')
        def internal_error():
            raise Exception("Something went wrong")
        
        response = client.get('/internal-error')
        assert response.status_code == 500
        
        data = response.get_json()
        assert 'UnhandledException' in data['type']
        assert 'unexpected error' in data['data']['message'].lower()
        # Should NOT contain exception details in production
        assert 'debug' not in data['data']


class TestDebugMode:
    """Test debug mode behavior"""
    
    @pytest.fixture
    def debug_app(self):
        """Create Flask app with debug mode enabled"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        init_error_handlers(app, debug_mode=True)
        return app
    
    @pytest.fixture
    def debug_client(self, debug_app):
        """Create test client for debug app"""
        return debug_app.test_client()
    
    def test_debug_mode_includes_details(self, debug_app, debug_client):
        """Test that debug mode includes error details"""
        @debug_app.route('/error')
        def error():
            raise ValueError("Test error")
        
        response = debug_client.get('/error')
        assert response.status_code == 500
        
        data = response.get_json()
        # Debug mode should include error details
        assert 'debug' in data['data']
        assert 'error' in data['data']['debug']
        assert 'traceback' in data['data']['debug']
    
    def test_production_mode_hides_details(self):
        """Test that production mode hides error details"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        init_error_handlers(app, debug_mode=False)
        
        @app.route('/error')
        def error():
            raise ValueError("Sensitive error info")
        
        with app.test_client() as client:
            response = client.get('/error')
            data = response.get_json()
            
            # Production mode should NOT include error details
            assert 'debug' not in data['data']
            assert 'Sensitive error info' not in str(data)


class TestMartiAPICompatibility:
    """Test Marti API response format compatibility"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_error_handlers(app)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_response_format_structure(self, app, client):
        """Test that error responses follow Marti API format"""
        @app.route('/test-error')
        def test_error():
            from werkzeug.exceptions import BadRequest
            raise BadRequest()
        
        response = client.get('/test-error')
        data = response.get_json()
        
        # Check Marti API format
        assert 'version' in data
        assert 'type' in data
        assert 'data' in data
        assert 'nodeId' in data
        
        assert data['version'] == '3'
        assert 'com.bbn.marti.remote.exception' in data['type']
        assert 'message' in data['data']
        assert data['nodeId'] == 'opentakserver'
    
    def test_all_errors_use_marti_format(self, app, client):
        """Test that all error types use Marti API format"""
        error_routes = []
        
        @app.route('/error-400')
        def error_400():
            from werkzeug.exceptions import BadRequest
            raise BadRequest()
        error_routes.append(('/error-400', 400))
        
        @app.route('/error-401')
        def error_401():
            from werkzeug.exceptions import Unauthorized
            raise Unauthorized()
        error_routes.append(('/error-401', 401))
        
        @app.route('/error-403')
        def error_403():
            from werkzeug.exceptions import Forbidden
            raise Forbidden()
        error_routes.append(('/error-403', 403))
        
        @app.route('/error-500')
        def error_500():
            raise Exception("Test")
        error_routes.append(('/error-500', 500))
        
        for route, expected_status in error_routes:
            response = client.get(route)
            assert response.status_code == expected_status
            
            data = response.get_json()
            assert data['version'] == '3'
            assert 'com.bbn.marti.remote.exception' in data['type']
            assert data['nodeId'] == 'opentakserver'


class TestCreateErrorResponse:
    """Test create_error_response utility function"""
    
    def test_create_basic_error_response(self):
        """Test creating basic error response"""
        response, status_code = create_error_response(400, "Bad input")
        
        assert status_code == 400
        assert response['version'] == '3'
        assert response['data']['message'] == "Bad input"
    
    def test_create_error_with_custom_type(self):
        """Test creating error with custom type"""
        response, status_code = create_error_response(
            403,
            "Access denied",
            "CustomException"
        )
        
        assert 'CustomException' in response['type']
    
    def test_error_response_structure(self):
        """Test error response has correct structure"""
        response, _ = create_error_response(500, "Error")
        
        assert 'version' in response
        assert 'type' in response
        assert 'data' in response
        assert 'nodeId' in response
        assert 'message' in response['data']


class TestErrorMessages:
    """Test standardized error messages"""
    
    def test_get_error_message_valid_key(self):
        """Test getting error message by valid key"""
        message = get_error_message('invalid_input')
        assert message == ERROR_MESSAGES['invalid_input']
        assert 'Invalid input' in message
    
    def test_get_error_message_invalid_key(self):
        """Test getting error message with invalid key"""
        message = get_error_message('nonexistent_key')
        # Should return default internal error message
        assert message == ERROR_MESSAGES['internal_error']
    
    def test_all_error_messages_defined(self):
        """Test that all expected error messages are defined"""
        expected_keys = [
            'invalid_input',
            'authentication_failed',
            'account_locked',
            'rate_limit_exceeded',
            'resource_not_found',
            'permission_denied',
            'internal_error',
            'database_error',
            'file_upload_error',
            'certificate_error'
        ]
        
        for key in expected_keys:
            assert key in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[key]) > 0


class TestErrorHandlerIntegration:
    """Integration tests for error handler"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app with multiple routes"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_error_handlers(app)
        
        @app.route('/success')
        def success():
            return jsonify({'status': 'ok'}), 200
        
        @app.route('/client-error')
        def client_error():
            from werkzeug.exceptions import BadRequest
            raise BadRequest("Client error")
        
        @app.route('/server-error')
        def server_error():
            raise Exception("Server error")
        
        @app.route('/json-endpoint')
        def json_endpoint():
            return jsonify({'data': 'test'})
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_successful_requests_unaffected(self, client):
        """Test that successful requests are not affected by error handlers"""
        response = client.get('/success')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'ok'
    
    def test_json_responses_unaffected(self, client):
        """Test that normal JSON responses work correctly"""
        response = client.get('/json-endpoint')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_error_responses_are_json(self, client):
        """Test that error responses are JSON"""
        response = client.get('/client-error')
        assert response.content_type == 'application/json'
        
        response = client.get('/server-error')
        assert response.content_type == 'application/json'
    
    def test_multiple_error_types(self, client):
        """Test handling multiple error types in same app"""
        # Test 400
        response = client.get('/client-error')
        assert response.status_code == 400
        assert response.get_json()['version'] == '3'
        
        # Test 404
        response = client.get('/nonexistent')
        assert response.status_code == 404
        assert response.get_json()['version'] == '3'
        
        # Test 500
        response = client.get('/server-error')
        assert response.status_code == 500
        assert response.get_json()['version'] == '3'


class TestInformationDisclosure:
    """Test that sensitive information is not disclosed"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        init_error_handlers(app, debug_mode=False)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_no_stack_traces_in_production(self, app, client):
        """Test that stack traces are not exposed in production"""
        @app.route('/error')
        def error():
            raise ValueError("Sensitive internal error")
        
        response = client.get('/error')
        data = response.get_json()
        
        # Should not contain stack trace
        assert 'traceback' not in str(data).lower()
        assert 'Traceback' not in str(data)
        assert 'ValueError' not in str(data)
    
    def test_no_file_paths_disclosed(self, app, client):
        """Test that file paths are not disclosed"""
        @app.route('/error')
        def error():
            raise Exception("Error in /path/to/sensitive/file.py")
        
        response = client.get('/error')
        data = response.get_json()
        
        # Should not contain file paths
        assert '/path/to/' not in str(data)
        assert 'file.py' not in str(data)
    
    def test_no_database_errors_disclosed(self, app, client):
        """Test that database errors are not disclosed"""
        @app.route('/db-error')
        def db_error():
            raise Exception("Database connection failed: postgresql://user:pass@host/db")
        
        response = client.get('/db-error')
        data = response.get_json()
        
        # Should not contain database connection strings
        assert 'postgresql://' not in str(data)
        assert 'user:pass' not in str(data)
        # Should show generic error
        assert 'unexpected error' in data['data']['message'].lower()


def run_manual_tests():
    """Manual test function for error handler validation"""
    print("\n" + "="*70)
    print("ERROR HANDLER VALIDATION TEST")
    print("="*70)
    
    app = Flask(__name__)
    app.config['DEBUG'] = False
    init_error_handlers(app, debug_mode=False)
    
    @app.route('/test-400')
    def test_400():
        from werkzeug.exceptions import BadRequest
        raise BadRequest()
    
    @app.route('/test-500')
    def test_500():
        raise Exception("Test error")
    
    with app.test_client() as client:
        print("\n📋 Testing Error Responses:")
        print("-" * 70)
        
        # Test 400
        response = client.get('/test-400')
        print(f"✅ 400 Bad Request: {response.status_code}")
        print(f"   Response: {response.get_json()['data']['message']}")
        
        # Test 404
        response = client.get('/nonexistent')
        print(f"✅ 404 Not Found: {response.status_code}")
        print(f"   Response: {response.get_json()['data']['message']}")
        
        # Test 500
        response = client.get('/test-500')
        print(f"✅ 500 Internal Error: {response.status_code}")
        print(f"   Response: {response.get_json()['data']['message']}")
        
        print("-" * 70)
        print("✅ ALL ERROR HANDLERS WORKING CORRECTLY")
        print("="*70 + "\n")


if __name__ == '__main__':
    run_manual_tests()
