#!/usr/bin/env python3
"""
Security Headers Test Suite
Tests that all required security headers are present in HTTP responses
"""

import pytest
from flask import Flask
from opentakserver.magk.services.security_headers import (
    SecurityHeadersManager,
    init_security_headers,
    get_csp_preset
)


class TestSecurityHeadersManager:
    """Test SecurityHeadersManager class"""
    
    def test_init_without_app(self):
        """Test initialization without Flask app"""
        manager = SecurityHeadersManager(enable_hsts=True)
        assert manager.enable_hsts is True
        assert manager.csp_policy is not None
    
    def test_init_with_app(self):
        """Test initialization with Flask app"""
        app = Flask(__name__)
        manager = SecurityHeadersManager(app, enable_hsts=True)
        assert manager.enable_hsts is True
        
        # Test that after_request handler is registered
        with app.test_client() as client:
            @app.route('/test')
            def test_route():
                return 'OK'
            
            response = client.get('/test')
            assert response.status_code == 200
    
    def test_csp_header_building(self):
        """Test Content Security Policy header construction"""
        manager = SecurityHeadersManager()
        csp_header = manager._build_csp_header()
        
        # Check that CSP header contains expected directives
        assert 'default-src' in csp_header
        assert 'script-src' in csp_header
        assert 'style-src' in csp_header
        assert "'self'" in csp_header
    
    def test_permissions_policy_building(self):
        """Test Permissions Policy header construction"""
        manager = SecurityHeadersManager()
        permissions_policy = manager._build_permissions_policy()
        
        # Check that permissions policy contains expected features
        assert 'geolocation=' in permissions_policy
        assert 'camera=' in permissions_policy
        assert 'microphone=' in permissions_policy
    
    def test_update_csp(self):
        """Test updating CSP directive"""
        manager = SecurityHeadersManager()
        original_sources = manager.csp_policy['script-src'].copy()
        
        manager.update_csp('script-src', ["'self'", 'https://cdn.example.com'])
        
        assert manager.csp_policy['script-src'] == ["'self'", 'https://cdn.example.com']
        assert manager.csp_policy['script-src'] != original_sources
    
    def test_add_csp_source(self):
        """Test adding source to CSP directive"""
        manager = SecurityHeadersManager()
        original_count = len(manager.csp_policy['script-src'])
        
        manager.add_csp_source('script-src', 'https://cdn.example.com')
        
        assert len(manager.csp_policy['script-src']) == original_count + 1
        assert 'https://cdn.example.com' in manager.csp_policy['script-src']
    
    def test_add_csp_source_no_duplicates(self):
        """Test that adding duplicate source doesn't create duplicates"""
        manager = SecurityHeadersManager()
        manager.add_csp_source('script-src', 'https://cdn.example.com')
        count_after_first = len(manager.csp_policy['script-src'])
        
        manager.add_csp_source('script-src', 'https://cdn.example.com')
        count_after_second = len(manager.csp_policy['script-src'])
        
        assert count_after_first == count_after_second


class TestSecurityHeadersInResponse:
    """Test that security headers are present in HTTP responses"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app with security headers"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_security_headers(app, enable_hsts=True)
        
        @app.route('/test')
        def test_route():
            return 'OK', 200
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_content_security_policy_present(self, client):
        """Test that Content-Security-Policy header is present"""
        response = client.get('/test')
        assert 'Content-Security-Policy' in response.headers
        
        csp = response.headers['Content-Security-Policy']
        assert 'default-src' in csp
        assert "'self'" in csp
    
    def test_x_frame_options_present(self, client):
        """Test that X-Frame-Options header is present"""
        response = client.get('/test')
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'
    
    def test_x_content_type_options_present(self, client):
        """Test that X-Content-Type-Options header is present"""
        response = client.get('/test')
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
    
    def test_x_xss_protection_present(self, client):
        """Test that X-XSS-Protection header is present"""
        response = client.get('/test')
        assert 'X-XSS-Protection' in response.headers
        assert response.headers['X-XSS-Protection'] == '1; mode=block'
    
    def test_referrer_policy_present(self, client):
        """Test that Referrer-Policy header is present"""
        response = client.get('/test')
        assert 'Referrer-Policy' in response.headers
        assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    
    def test_permissions_policy_present(self, client):
        """Test that Permissions-Policy header is present"""
        response = client.get('/test')
        assert 'Permissions-Policy' in response.headers
        
        permissions = response.headers['Permissions-Policy']
        assert 'geolocation=' in permissions
        assert 'camera=' in permissions
    
    def test_hsts_present(self, client):
        """Test that Strict-Transport-Security header is present"""
        response = client.get('/test')
        assert 'Strict-Transport-Security' in response.headers
        
        hsts = response.headers['Strict-Transport-Security']
        assert 'max-age=31536000' in hsts
        assert 'includeSubDomains' in hsts
    
    def test_server_header_removed(self, client):
        """Test that Server header is removed"""
        response = client.get('/test')
        assert 'Server' not in response.headers
    
    def test_all_security_headers_present(self, client):
        """Test that all required security headers are present"""
        response = client.get('/test')
        
        required_headers = [
            'Content-Security-Policy',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection',
            'Referrer-Policy',
            'Permissions-Policy',
            'Strict-Transport-Security'
        ]
        
        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"


class TestCSPPresets:
    """Test CSP configuration presets"""
    
    def test_strict_preset(self):
        """Test strict CSP preset"""
        csp = get_csp_preset('strict')
        
        assert csp['default-src'] == ["'none'"]
        assert csp['script-src'] == ["'self'"]
        assert "'unsafe-inline'" not in csp['script-src']
    
    def test_moderate_preset(self):
        """Test moderate CSP preset"""
        csp = get_csp_preset('moderate')
        
        assert csp['default-src'] == ["'self'"]
        assert "'unsafe-inline'" in csp['script-src']
        assert "'unsafe-eval'" not in csp['script-src']
    
    def test_relaxed_preset(self):
        """Test relaxed CSP preset"""
        csp = get_csp_preset('relaxed')
        
        assert csp['default-src'] == ["'self'"]
        assert "'unsafe-inline'" in csp['script-src']
        assert "'unsafe-eval'" in csp['script-src']
    
    def test_unknown_preset_fallback(self):
        """Test that unknown preset falls back to moderate"""
        csp = get_csp_preset('unknown')
        moderate_csp = get_csp_preset('moderate')
        
        assert csp == moderate_csp


class TestHSTSConfiguration:
    """Test HSTS configuration options"""
    
    def test_hsts_enabled(self):
        """Test HSTS when enabled"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_security_headers(app, enable_hsts=True)
        
        @app.route('/test')
        def test_route():
            return 'OK'
        
        with app.test_client() as client:
            response = client.get('/test')
            assert 'Strict-Transport-Security' in response.headers
    
    def test_hsts_disabled(self):
        """Test HSTS when disabled"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_security_headers(app, enable_hsts=False)
        
        @app.route('/test')
        def test_route():
            return 'OK'
        
        with app.test_client() as client:
            response = client.get('/test')
            assert 'Strict-Transport-Security' not in response.headers


class TestSecurityHeadersIntegration:
    """Integration tests for security headers"""
    
    def test_headers_on_multiple_routes(self):
        """Test that headers are applied to all routes"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_security_headers(app)
        
        @app.route('/route1')
        def route1():
            return 'Route 1'
        
        @app.route('/route2')
        def route2():
            return 'Route 2'
        
        with app.test_client() as client:
            response1 = client.get('/route1')
            response2 = client.get('/route2')
            
            # Both routes should have security headers
            assert 'Content-Security-Policy' in response1.headers
            assert 'Content-Security-Policy' in response2.headers
            assert 'X-Frame-Options' in response1.headers
            assert 'X-Frame-Options' in response2.headers
    
    def test_headers_on_error_responses(self):
        """Test that headers are applied to error responses"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_security_headers(app)
        
        @app.route('/error')
        def error_route():
            return 'Not Found', 404
        
        with app.test_client() as client:
            response = client.get('/error')
            
            # Error responses should also have security headers
            assert response.status_code == 404
            assert 'Content-Security-Policy' in response.headers
            assert 'X-Frame-Options' in response.headers
    
    def test_headers_on_json_responses(self):
        """Test that headers are applied to JSON responses"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        init_security_headers(app)
        
        @app.route('/json')
        def json_route():
            from flask import jsonify
            return jsonify({'status': 'ok'})
        
        with app.test_client() as client:
            response = client.get('/json')
            
            # JSON responses should have security headers
            assert 'Content-Security-Policy' in response.headers
            assert 'X-Frame-Options' in response.headers
            assert response.content_type == 'application/json'


def run_manual_tests():
    """
    Manual test function to verify security headers in a running app.
    Run this with: python -m pytest test_security_headers.py -v
    """
    print("\n" + "="*70)
    print("SECURITY HEADERS VALIDATION TEST")
    print("="*70)
    
    app = Flask(__name__)
    init_security_headers(app, enable_hsts=True)
    
    @app.route('/test')
    def test_route():
        return 'Security Headers Test'
    
    with app.test_client() as client:
        response = client.get('/test')
        
        print("\n✅ HTTP Response Status:", response.status_code)
        print("\n📋 Security Headers Present:")
        print("-" * 70)
        
        security_headers = [
            'Content-Security-Policy',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection',
            'Referrer-Policy',
            'Permissions-Policy',
            'Strict-Transport-Security'
        ]
        
        all_present = True
        for header in security_headers:
            if header in response.headers:
                value = response.headers[header]
                # Truncate long values for display
                display_value = value if len(value) < 60 else value[:57] + '...'
                print(f"✅ {header}: {display_value}")
            else:
                print(f"❌ {header}: MISSING")
                all_present = False
        
        print("-" * 70)
        
        if 'Server' in response.headers:
            print(f"⚠️  Server header present: {response.headers['Server']}")
            print("   (Should be removed for security)")
        else:
            print("✅ Server header removed (good)")
        
        print("\n" + "="*70)
        if all_present:
            print("✅ ALL SECURITY HEADERS PRESENT - TEST PASSED")
        else:
            print("❌ SOME SECURITY HEADERS MISSING - TEST FAILED")
        print("="*70 + "\n")
        
        return all_present


if __name__ == '__main__':
    # Run manual tests
    success = run_manual_tests()
    exit(0 if success else 1)
