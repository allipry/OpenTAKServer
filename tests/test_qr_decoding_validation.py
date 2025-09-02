"""
QR Code Decoding Validation Tests

This module provides comprehensive tests for QR code decoding using standard QR libraries,
ensuring that generated QR codes can be properly decoded and validated by external tools.

Requirements covered: 4.3, 4.4
"""

import os
import pytest
import sys
import tempfile
import io
from unittest.mock import patch, Mock

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.qr_validation_utils import QRValidationUtils, validate_qr_code, QRValidationResult


class TestQRDecodingValidation:
    """Test cases for QR code decoding validation using standard libraries."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QRValidationUtils(timeout=2.0)
        self.valid_qr_string = "tak://com.atakmap.app/enroll?host=192.168.1.100&username=testuser&token=testpass"
        self.localhost_qr_string = "tak://com.atakmap.app/enroll?host=localhost&username=testuser&token=testpass"
    
    @pytest.mark.unit
    def test_qr_library_availability_check(self):
        """Test QR library availability detection."""
        # Test when libraries are available
        try:
            import qrcode
            from PIL import Image
            
            is_decodable, error, details = self.validator.test_qr_decodability(self.valid_qr_string)
            assert details['qrcode_library'] == 'available'
            
        except ImportError:
            # Test when libraries are not available
            is_decodable, error, details = self.validator.test_qr_decodability(self.valid_qr_string)
            assert not is_decodable
            assert "not available" in error
    
    @pytest.mark.unit
    def test_qr_code_generation_and_validation(self):
        """Test QR code generation and data integrity validation."""
        pytest.importorskip("qrcode")
        pytest.importorskip("PIL")
        
        test_cases = [
            self.valid_qr_string,
            self.localhost_qr_string,
            "tak://com.atakmap.app/enroll?host=example.com&username=user@domain.com&token=pass!@#$",
            "tak://com.atakmap.app/enroll?host=very-long-hostname.example.domain.com&username=verylongusername&token=verylongpasswordwithmanycharacters"
        ]
        
        for qr_string in test_cases:
            is_decodable, error, details = self.validator.test_qr_decodability(qr_string)
            
            assert is_decodable, f"QR code should be decodable: {error}"
            assert error is None
            assert 'qr_version' in details
            assert 'data_length' in details
            assert details['data_length'] == len(qr_string)
            
            # Verify data integrity if available
            if 'data_integrity' in details:
                assert details['data_integrity'] in [True, 'unknown']
    
    @pytest.mark.unit
    def test_qr_code_size_and_version_handling(self):
        """Test QR code size handling and version selection."""
        pytest.importorskip("qrcode")
        pytest.importorskip("PIL")
        
        # Test different data sizes
        base_qr = "tak://com.atakmap.app/enroll?host=example.com&username=user&token="
        
        test_sizes = [
            ("short", "pass"),
            ("medium", "a" * 100),
            ("long", "a" * 500),
            ("very_long", "a" * 1000)
        ]
        
        for size_name, token in test_sizes:
            qr_string = base_qr + token
            is_decodable, error, details = self.validator.test_qr_decodability(qr_string)
            
            assert is_decodable, f"QR code should be decodable for {size_name} data: {error}"
            assert 'qr_version' in details
            assert 'qr_modules' in details
            
            # Longer data should require higher QR versions
            if size_name == "very_long":
                assert details['qr_version'] > 1, "Long data should require higher QR version"
    
    @pytest.mark.unit
    def test_qr_code_special_characters_encoding(self):
        """Test QR code handling of special characters."""
        pytest.importorskip("qrcode")
        pytest.importorskip("PIL")
        
        special_char_cases = [
            ("spaces", "tak://com.atakmap.app/enroll?host=example.com&username=user name&token=pass word"),
            ("symbols", "tak://com.atakmap.app/enroll?host=example.com&username=user@domain&token=pass!@#$"),
            ("encoded", "tak://com.atakmap.app/enroll?host=example.com&username=user%40domain&token=pass%21%40%23%24"),
            ("unicode", "tak://com.atakmap.app/enroll?host=example.com&username=üser&token=pässwörd")
        ]
        
        for case_name, qr_string in special_char_cases:
            is_decodable, error, details = self.validator.test_qr_decodability(qr_string)
            
            # All cases should be decodable by QR library
            assert is_decodable, f"QR code should handle {case_name}: {error}"
            assert details['data_length'] == len(qr_string)
    
    @pytest.mark.unit
    def test_qr_code_error_correction_levels(self):
        """Test QR code generation with different error correction levels."""
        pytest.importorskip("qrcode")
        
        import qrcode
        
        qr_string = self.valid_qr_string
        error_levels = [
            qrcode.constants.ERROR_CORRECT_L,
            qrcode.constants.ERROR_CORRECT_M,
            qrcode.constants.ERROR_CORRECT_Q,
            qrcode.constants.ERROR_CORRECT_H
        ]
        
        for error_level in error_levels:
            qr = qrcode.QRCode(
                version=1,
                error_correction=error_level,
                box_size=10,
                border=4,
            )
            
            try:
                qr.add_data(qr_string)
                qr.make(fit=True)
                
                # Should be able to generate QR code with any error correction level
                img = qr.make_image(fill_color="black", back_color="white")
                assert img is not None
                
            except Exception as e:
                pytest.fail(f"QR code generation failed with error level {error_level}: {e}")
    
    @pytest.mark.unit
    def test_qr_code_image_generation(self):
        """Test QR code image generation and properties."""
        pytest.importorskip("qrcode")
        pytest.importorskip("PIL")
        
        import qrcode
        from PIL import Image
        
        qr_string = self.valid_qr_string
        
        # Test different box sizes and borders
        configurations = [
            {"box_size": 5, "border": 2},
            {"box_size": 10, "border": 4},
            {"box_size": 20, "border": 8}
        ]
        
        for config in configurations:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                **config
            )
            
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Verify image properties
            assert isinstance(img, Image.Image)
            assert img.size[0] > 0 and img.size[1] > 0
            assert img.mode in ['1', 'L', 'RGB']  # Valid PIL image modes
    
    @pytest.mark.unit
    def test_qr_code_data_capacity_limits(self):
        """Test QR code data capacity limits."""
        pytest.importorskip("qrcode")
        
        import qrcode
        
        base_qr = "tak://com.atakmap.app/enroll?host=example.com&username=user&token="
        
        # Test progressively longer tokens to find capacity limits
        token_lengths = [10, 100, 500, 1000, 2000, 3000]
        
        for length in token_lengths:
            token = "a" * length
            qr_string = base_qr + token
            
            qr = qrcode.QRCode(version=None)  # Auto-select version
            
            try:
                qr.add_data(qr_string)
                qr.make(fit=True)
                
                # If successful, record the version used
                version_used = qr.version
                assert version_used > 0, f"Invalid QR version for length {length}"
                
                # Very long strings should use higher versions
                if length > 1000:
                    assert version_used > 5, f"Expected higher QR version for length {length}, got {version_used}"
                    
            except Exception as e:
                # If it fails, it should be due to data capacity limits
                if length > 2000:
                    # Expected to fail for very long data
                    assert "too much data" in str(e).lower() or "data overflow" in str(e).lower()
                else:
                    pytest.fail(f"Unexpected failure for reasonable data length {length}: {e}")
    
    @pytest.mark.unit
    def test_qr_validation_with_mock_library_failure(self):
        """Test QR validation behavior when QR library operations fail."""
        with patch('qrcode.QRCode') as mock_qr_class:
            # Mock QR code creation failure
            mock_qr_class.side_effect = Exception("QR library error")
            
            is_decodable, error, details = self.validator.test_qr_decodability(self.valid_qr_string)
            
            assert not is_decodable
            assert "QR code generation failed" in error
            assert "QR library error" in error
    
    @pytest.mark.unit
    def test_qr_validation_with_mock_image_failure(self):
        """Test QR validation behavior when image generation fails."""
        pytest.importorskip("qrcode")
        
        with patch('qrcode.QRCode') as mock_qr_class:
            mock_qr = Mock()
            mock_qr.add_data.return_value = None
            mock_qr.make.return_value = None
            mock_qr.make_image.side_effect = Exception("Image generation error")
            mock_qr_class.return_value = mock_qr
            
            is_decodable, error, details = self.validator.test_qr_decodability(self.valid_qr_string)
            
            assert not is_decodable
            assert "Image generation error" in error
    
    @pytest.mark.integration
    def test_comprehensive_qr_validation_with_decoding(self):
        """Test comprehensive QR validation including decoding tests."""
        test_cases = [
            {
                "qr": self.valid_qr_string,
                "should_be_valid": True,
                "should_have_warnings": False
            },
            {
                "qr": self.localhost_qr_string,
                "should_be_valid": True,
                "should_have_warnings": True  # localhost warning
            },
            {
                "qr": "invalid://wrong.scheme/enroll?host=example.com&username=user&token=pass",
                "should_be_valid": False,
                "should_have_warnings": False
            },
            {
                "qr": "tak://com.atakmap.app/enroll?host=example.com&username=&token=pass",
                "should_be_valid": False,  # empty username
                "should_have_warnings": False
            }
        ]
        
        for case in test_cases:
            result = validate_qr_code(case["qr"], test_hostname=False)  # Skip hostname test
            
            assert result.is_valid == case["should_be_valid"], f"Validation failed for: {case['qr'][:50]}..."
            
            if case["should_have_warnings"]:
                assert len(result.warnings) > 0, f"Expected warnings for: {case['qr'][:50]}..."
            
            # All valid format QR codes should be decodable (if library available)
            if result.format_valid:
                try:
                    import qrcode
                    assert result.qr_decodable, f"Valid QR should be decodable: {case['qr'][:50]}..."
                except ImportError:
                    # Skip decodability check if library not available
                    pass
    
    @pytest.mark.unit
    def test_qr_validation_edge_cases(self):
        """Test QR validation with edge cases."""
        edge_cases = [
            ("", False, "Empty string"),
            ("tak://com.atakmap.app/enroll?", False, "No parameters"),
            ("tak://com.atakmap.app/enroll?host=", False, "Empty host"),
            ("tak://com.atakmap.app/enroll?host=example.com", False, "Missing username and token"),
            ("TAK://COM.ATAKMAP.APP/ENROLL?HOST=EXAMPLE.COM&USERNAME=USER&TOKEN=PASS", False, "Wrong case"),
            ("tak://com.atakmap.app/enroll?host=example.com&username=user&token=pass&extra=value", True, "Extra parameters")
        ]
        
        for qr_string, should_be_valid, description in edge_cases:
            format_valid, errors, details = self.validator.validate_itak_qr_format(qr_string)
            
            assert format_valid == should_be_valid, f"Format validation failed for {description}: {qr_string}"
            
            if should_be_valid:
                assert len(errors) == 0, f"Valid QR should have no errors: {description}"
            else:
                assert len(errors) > 0, f"Invalid QR should have errors: {description}"
    
    @pytest.mark.slow
    def test_qr_performance_with_large_data(self):
        """Test QR code generation performance with large data sets."""
        pytest.importorskip("qrcode")
        
        import time
        
        # Test with progressively larger tokens
        base_qr = "tak://com.atakmap.app/enroll?host=example.com&username=user&token="
        
        performance_results = []
        
        for size in [100, 500, 1000]:
            token = "a" * size
            qr_string = base_qr + token
            
            start_time = time.time()
            is_decodable, error, details = self.validator.test_qr_decodability(qr_string)
            end_time = time.time()
            
            duration = end_time - start_time
            performance_results.append((size, duration, is_decodable))
            
            # Should complete within reasonable time (5 seconds)
            assert duration < 5.0, f"QR generation took too long for size {size}: {duration:.2f}s"
            
            if is_decodable:
                assert 'qr_version' in details
                assert details['qr_version'] > 0
        
        # Performance should not degrade dramatically with size
        if len(performance_results) >= 2:
            small_time = performance_results[0][1]
            large_time = performance_results[-1][1]
            
            # Large data should not take more than 10x longer than small data
            assert large_time < small_time * 10, f"Performance degradation too severe: {small_time:.3f}s -> {large_time:.3f}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])