"""
Integration tests for different deployment scenarios.
Tests QR code generation in localhost, external IP, and custom hostname environments.
"""

import os
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opentakserver.hostname_resolver import HostnameResolver, HostnameResult


class TestDeploymentScenarios:
    """Test cases for different deployment scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = HostnameResolver()
        # Clear any environment variables that might affect tests
        for env_var in ['EXTERNAL_HOST', 'SERVER_HOST', 'QR_DISABLE_EXTERNAL_IP', 'QR_HOST_DETECTION_TIMEOUT']:
            if env_var in os.environ:
                del os.environ[env_var]
    
    def teardown_method(self):
        """Clean up after tests."""
        self.resolver.clear_cache()
    
    def test_localhost_development_scenario(self):
        """Test QR code generation in localhost development environment."""
        # Simulate localhost development environment
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == 'localhost'
        assert result.detection_method == 'fallback'
        assert result.is_localhost == True
        assert result.is_external_accessible == False
        assert len(result.warnings) > 0
        assert any('fallback hostname' in warning for warning in result.warnings)
        assert any('EXTERNAL_HOST' in warning for warning in result.warnings)
    
    def test_localhost_with_port_scenario(self):
        """Test QR code generation with localhost and port."""
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='localhost:8443')
        
        assert result.hostname == 'localhost'
        assert result.detection_method == 'fallback'
        assert result.is_localhost == True
        
        # Verify port is stripped from hostname
        assert ':8443' not in result.hostname
    
    def test_docker_container_scenario(self):
        """Test QR code generation in Docker container environment."""
        # Simulate Docker container with internal hostname
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='opentakserver-core:8080')
        
        # Should use request host since it's not localhost
        assert result.hostname == 'opentakserver-core'
        assert result.detection_method == 'request_host'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_detection_scenario(self, mock_get):
        """Test QR code generation with external IP detection."""
        # Mock successful external IP detection
        mock_response = Mock()
        mock_response.text = '203.0.113.1'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
        assert len(result.warnings) == 0
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_service_fallback_scenario(self, mock_get):
        """Test external IP detection with service fallback."""
        # First service fails, second succeeds
        def side_effect(url, timeout):
            if 'ipify' in url:
                raise Exception("Service unavailable")
            else:
                mock_response = Mock()
                mock_response.text = '203.0.113.1'
                mock_response.raise_for_status.return_value = None
                return mock_response
        
        mock_get.side_effect = side_effect
        
        result = self.resolver.get_external_hostname()
        
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
        assert result.is_external_accessible == True
    
    @patch.dict(os.environ, {'EXTERNAL_HOST': 'production.example.com'})
    def test_production_environment_variable_scenario(self):
        """Test QR code generation in production with environment variable."""
        resolver = HostnameResolver()  # Create new instance to pick up env vars
        
        result = resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == 'production.example.com'
        assert result.detection_method == 'env_var'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
        assert len(result.warnings) == 0
    
    @patch.dict(os.environ, {'SERVER_HOST': 'staging.example.com'})
    def test_staging_environment_variable_scenario(self):
        """Test QR code generation in staging with SERVER_HOST variable."""
        resolver = HostnameResolver()
        
        result = resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == 'staging.example.com'
        assert result.detection_method == 'env_var'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    def test_reverse_proxy_scenario(self):
        """Test QR code generation behind reverse proxy."""
        # Simulate reverse proxy with external hostname
        result = self.resolver.get_external_hostname(
            request_host='proxy.example.com:443',
            override_host=None
        )
        
        # Should use request host from proxy
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='proxy.example.com:443')
        
        assert result.hostname == 'proxy.example.com'
        assert result.detection_method == 'request_host'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    def test_load_balancer_scenario(self):
        """Test QR code generation behind load balancer."""
        # Simulate load balancer scenario
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='lb.example.com:8443')
        
        assert result.hostname == 'lb.example.com'
        assert result.detection_method == 'request_host'
        assert result.is_external_accessible == True
    
    def test_custom_hostname_override_scenario(self):
        """Test QR code generation with custom hostname override."""
        result = self.resolver.get_external_hostname(
            request_host='localhost:8080',
            override_host='custom.example.com'
        )
        
        assert result.hostname == 'custom.example.com'
        assert result.detection_method == 'override'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
        assert len(result.warnings) == 0
    
    def test_custom_hostname_override_localhost_scenario(self):
        """Test QR code generation with localhost override (warning case)."""
        result = self.resolver.get_external_hostname(
            request_host='example.com:8080',
            override_host='localhost'
        )
        
        assert result.hostname == 'localhost'
        assert result.detection_method == 'override'
        assert result.is_localhost == True
        assert result.is_external_accessible == False
        assert len(result.warnings) > 0
        assert any('localhost' in warning for warning in result.warnings)
    
    def test_nat_firewall_scenario(self):
        """Test QR code generation behind NAT/firewall."""
        # Simulate NAT scenario where external IP detection is needed
        with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '203.0.113.1'  # External IP
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = self.resolver.get_external_hostname(request_host='192.168.1.100:8080')
        
        # Should detect external IP instead of internal IP
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
        assert result.is_external_accessible == True
    
    def test_cloud_deployment_scenario(self):
        """Test QR code generation in cloud deployment."""
        # Simulate cloud deployment with public IP
        with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '54.123.45.67'  # Cloud public IP
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = self.resolver.get_external_hostname(request_host='ip-10-0-1-100.ec2.internal:8080')
        
        assert result.hostname == '54.123.45.67'
        assert result.detection_method == 'external_ip'
        assert result.is_external_accessible == True
    
    def test_kubernetes_deployment_scenario(self):
        """Test QR code generation in Kubernetes deployment."""
        # Simulate Kubernetes with service hostname
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='opentakserver-service.default.svc.cluster.local:8080')
        
        assert result.hostname == 'opentakserver-service.default.svc.cluster.local'
        assert result.detection_method == 'request_host'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    @patch.dict(os.environ, {'EXTERNAL_HOST': 'k8s.example.com'})
    def test_kubernetes_with_ingress_scenario(self):
        """Test QR code generation in Kubernetes with ingress."""
        resolver = HostnameResolver()
        
        result = resolver.get_external_hostname(request_host='opentakserver-service:8080')
        
        # Should use environment variable for external access
        assert result.hostname == 'k8s.example.com'
        assert result.detection_method == 'env_var'
        assert result.is_external_accessible == True
    
    def test_vpn_deployment_scenario(self):
        """Test QR code generation in VPN environment."""
        # Simulate VPN with private IP range
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='10.8.0.1:8080')
        
        assert result.hostname == '10.8.0.1'
        assert result.detection_method == 'request_host'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    def test_multi_homed_server_scenario(self):
        """Test QR code generation on multi-homed server."""
        # Simulate server with multiple network interfaces
        with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '203.0.113.1'  # Primary external IP
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = self.resolver.get_external_hostname(request_host='192.168.1.100:8080')
        
        # Should detect primary external IP
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_network_connectivity_failure_scenario(self, mock_get):
        """Test QR code generation with network connectivity failure."""
        # Simulate network failure
        mock_get.side_effect = Exception("Network unreachable")
        
        result = self.resolver.get_external_hostname(request_host='example.com:8080')
        
        # Should fall back to request host
        assert result.hostname == 'example.com'
        assert result.detection_method == 'request_host'
        assert len(result.warnings) > 0
        assert any('External IP detection failed' in warning for warning in result.warnings)
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_service_timeout_scenario(self, mock_get):
        """Test QR code generation with external service timeout."""
        # Simulate timeout
        import requests
        mock_get.side_effect = requests.Timeout("Request timeout")
        
        result = self.resolver.get_external_hostname(request_host='backup.example.com:8080')
        
        # Should fall back to request host
        assert result.hostname == 'backup.example.com'
        assert result.detection_method == 'request_host'
        assert len(result.warnings) > 0
    
    @patch.dict(os.environ, {'QR_DISABLE_EXTERNAL_IP': 'true'})
    def test_external_ip_disabled_scenario(self):
        """Test QR code generation with external IP detection disabled."""
        resolver = HostnameResolver()
        
        result = resolver.get_external_hostname(request_host='internal.example.com:8080')
        
        # Should skip external IP detection
        assert result.hostname == 'internal.example.com'
        assert result.detection_method == 'request_host'
        assert result.is_external_accessible == True
    
    @patch.dict(os.environ, {'QR_HOST_DETECTION_TIMEOUT': '1'})
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_custom_timeout_scenario(self, mock_get):
        """Test QR code generation with custom timeout configuration."""
        # Simulate slow response
        import time
        def slow_response(*args, **kwargs):
            time.sleep(2)  # Longer than 1 second timeout
            mock_response = Mock()
            mock_response.text = '203.0.113.1'
            return mock_response
        
        mock_get.side_effect = slow_response
        resolver = HostnameResolver()
        
        # Should timeout and fall back
        result = resolver.get_external_hostname(request_host='fallback.example.com:8080')
        
        assert result.hostname == 'fallback.example.com'
        assert result.detection_method == 'request_host'
    
    def test_ipv6_scenario(self):
        """Test QR code generation with IPv6 addresses."""
        # Test IPv6 localhost
        result = self.resolver.get_external_hostname(
            request_host='[::1]:8080',
            override_host=None
        )
        
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='[::1]:8080')
        
        # Should detect as localhost
        assert result.is_localhost == True
        assert result.detection_method == 'fallback'
    
    def test_domain_name_scenario(self):
        """Test QR code generation with domain names."""
        domain_names = [
            'tak-server.military.net',
            'opentakserver.company.com',
            'tak.example.org',
            'server-01.domain.gov'
        ]
        
        for domain in domain_names:
            with patch.object(self.resolver, '_disable_external_ip', True):
                result = self.resolver.get_external_hostname(request_host=f'{domain}:8080')
            
            assert result.hostname == domain
            assert result.detection_method == 'request_host'
            assert result.is_localhost == False
            assert result.is_external_accessible == True
    
    def test_mixed_environment_priority_scenario(self):
        """Test QR code generation with mixed environment configuration."""
        # Test priority: override > env_var > external_ip > request_host > fallback
        
        with patch.dict(os.environ, {'EXTERNAL_HOST': 'env.example.com'}):
            with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.text = '203.0.113.1'
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                resolver = HostnameResolver()
                
                # Override should win
                result = resolver.get_external_hostname(
                    request_host='request.example.com:8080',
                    override_host='override.example.com'
                )
                
                assert result.hostname == 'override.example.com'
                assert result.detection_method == 'override'
                
                # Environment variable should win over external IP
                result = resolver.get_external_hostname(
                    request_host='request.example.com:8080'
                )
                
                assert result.hostname == 'env.example.com'
                assert result.detection_method == 'env_var'
    
    def test_error_recovery_scenario(self):
        """Test QR code generation error recovery mechanisms."""
        # Simulate multiple failure points with recovery
        with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
            # All external services fail
            mock_get.side_effect = Exception("All services down")
            
            # But we have a valid request host
            result = self.resolver.get_external_hostname(request_host='backup.example.com:8080')
            
            assert result.hostname == 'backup.example.com'
            assert result.detection_method == 'request_host'
            assert result.is_external_accessible == True
            assert len(result.warnings) > 0
            assert any('External IP detection failed' in warning for warning in result.warnings)


if __name__ == '__main__':
    pytest.main([__file__])