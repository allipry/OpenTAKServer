#!/usr/bin/env python3
"""
Email Service Module
Handles email sending for registration notifications and credentials
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', 'donotreply@magktech.com')
        self.from_name = os.getenv('FROM_NAME', 'MAGK-Admin Registration')
        self.reply_to_email = os.getenv('REPLY_TO_EMAIL', 'admin@magktech.com')
        self.server_name = os.getenv('SERVER_NAME', 'MAGK-Admin TAK Server')
        self.external_host = os.getenv('EXTERNAL_HOST', 'tak.magktech.com')
        
    def send_registration_email(self, user_data, team_data, event_data, temp_password):
        """
        Send registration confirmation email with credentials
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"TAK Server Registration Confirmed - {event_data['name']}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = user_data['email']
            msg['Reply-To'] = self.reply_to_email
            
            # Create email content
            text_content = self._create_text_email(user_data, team_data, event_data, temp_password)
            html_content = self._create_html_email(user_data, team_data, event_data, temp_password)
            
            # Attach parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            success = self._send_email(msg)
            
            if success:
                logger.info(f"Registration email sent successfully to {user_data['email']} for user {user_data['callsign']}")
                return True
            else:
                logger.error(f"Failed to send registration email to {user_data['email']} for user {user_data['callsign']}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending registration email to {user_data['email']}: {e}")
            return False
    
    def _create_text_email(self, user_data, team_data, event_data, temp_password):
        """Create plain text email content"""
        device_instructions = self._get_device_instructions(user_data['deviceType'])
        
        return f"""
TAK Server Registration Confirmed

Hello {user_data['name']},

Your registration for the TAK Server has been successfully completed!

REGISTRATION DETAILS:
- Callsign: {user_data['callsign']}
- Event: {event_data['name']}
- Team: {team_data['name']}
- Device Type: {user_data['deviceType'].upper()}

TEMPORARY CREDENTIALS:
- Username: {user_data['callsign']}
- Temporary Password: {temp_password}

SERVER CONNECTION:
- Server: {self.external_host}
- TCP Port: 8087
- SSL Port: 8089

{device_instructions}

IMPORTANT SECURITY NOTES:
- Change your temporary password after first login
- Keep your credentials secure and do not share them
- Contact your team leader if you have any issues

If you have any questions or need assistance, please contact your team administrator.

Best regards,
{self.server_name} Team

---
This is an automated message. Please do not reply to this email.
For support, contact: {self.reply_to_email}
        """.strip()
    
    def _create_html_email(self, user_data, team_data, event_data, temp_password):
        """Create HTML email content"""
        device_instructions = self._get_device_instructions(user_data['deviceType'], html=True)
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TAK Server Registration Confirmed</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .info-box {{ background: white; padding: 20px; margin: 20px 0; border-radius: 6px; border-left: 4px solid #007bff; }}
        .credentials {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 6px; margin: 20px 0; }}
        .warning {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 6px; margin: 10px 0; }}
        code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 TAK Server Registration Confirmed</h1>
            <p>Welcome to {self.server_name}</p>
        </div>
        
        <div class="content">
            <p>Hello <strong>{user_data['name']}</strong>,</p>
            
            <p>Your registration for the TAK Server has been <strong>successfully completed</strong>!</p>
            
            <div class="info-box">
                <h3>📋 Registration Details</h3>
                <ul>
                    <li><strong>Callsign:</strong> {user_data['callsign']}</li>
                    <li><strong>Event:</strong> {event_data['name']}</li>
                    <li><strong>Team:</strong> {team_data['name']}</li>
                    <li><strong>Device Type:</strong> {user_data['deviceType'].upper()}</li>
                </ul>
            </div>
            
            <div class="credentials">
                <h3>🔐 Temporary Credentials</h3>
                <p><strong>Username:</strong> <code>{user_data['callsign']}</code></p>
                <p><strong>Temporary Password:</strong> <code>{temp_password}</code></p>
            </div>
            
            <div class="info-box">
                <h3>🌐 Server Connection</h3>
                <ul>
                    <li><strong>Server:</strong> {self.external_host}</li>
                    <li><strong>TCP Port:</strong> 8087</li>
                    <li><strong>SSL Port:</strong> 8089 (Recommended)</li>
                </ul>
            </div>
            
            {device_instructions}
            
            <div class="warning">
                <h3>⚠️ Important Security Notes</h3>
                <ul>
                    <li>Change your temporary password after first login</li>
                    <li>Keep your credentials secure and do not share them</li>
                    <li>Contact your team leader if you have any issues</li>
                </ul>
            </div>
            
            <p>If you have any questions or need assistance, please contact your team administrator.</p>
            
            <p>Best regards,<br>
            <strong>{self.server_name} Team</strong></p>
        </div>
        
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>For support, contact: <a href="mailto:{self.reply_to_email}">{self.reply_to_email}</a></p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _get_device_instructions(self, device_type, html=False):
        """Get device-specific setup instructions"""
        if device_type.lower() == 'android':
            if html:
                return """
                <div class="info-box">
                    <h3>📱 Android (ATAK) Setup Instructions</h3>
                    <ol>
                        <li>Download and install <strong>ATAK</strong> from the Google Play Store</li>
                        <li>Open ATAK and go to <strong>Settings</strong> → <strong>Network Preferences</strong></li>
                        <li>Add a new server connection with the details above</li>
                        <li>Use your callsign and temporary password to connect</li>
                        <li>Change your password in the TAK server settings after first login</li>
                    </ol>
                </div>
                """
            else:
                return """
ANDROID (ATAK) SETUP INSTRUCTIONS:
1. Download and install ATAK from the Google Play Store
2. Open ATAK and go to Settings → Network Preferences
3. Add a new server connection with the details above
4. Use your callsign and temporary password to connect
5. Change your password in the TAK server settings after first login
                """.strip()
        elif device_type.lower() == 'ios':
            if html:
                return """
                <div class="info-box">
                    <h3>📱 iOS (iTAK) Setup Instructions</h3>
                    <ol>
                        <li>Download and install <strong>iTAK</strong> from the App Store</li>
                        <li>Open iTAK and go to <strong>Settings</strong> → <strong>Server Settings</strong></li>
                        <li>Add a new server connection with the details above</li>
                        <li>Use your callsign and temporary password to connect</li>
                        <li>Change your password in the server settings after first login</li>
                    </ol>
                </div>
                """
            else:
                return """
iOS (iTAK) SETUP INSTRUCTIONS:
1. Download and install iTAK from the App Store
2. Open iTAK and go to Settings → Server Settings
3. Add a new server connection with the details above
4. Use your callsign and temporary password to connect
5. Change your password in the server settings after first login
                """.strip()
        else:
            if html:
                return """
                <div class="info-box">
                    <h3>💻 General Setup Instructions</h3>
                    <p>Please contact your team administrator for device-specific setup instructions.</p>
                </div>
                """
            else:
                return "Please contact your team administrator for device-specific setup instructions."
    
    def _send_email(self, msg):
        """Send email using SMTP"""
        try:
            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.smtp_use_tls:
                    server.starttls()
            
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.from_email, msg['To'], text)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"SMTP Error: {e}")
            return False
    
    def test_smtp_connection(self):
        """Test SMTP connection"""
        try:
            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.smtp_use_tls:
                    server.starttls()
            
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            
            server.quit()
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def send_password_reset_email(self, email, username, reset_url, expires_hours=24):
        """
        Send password reset email with secure reset link
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Password Reset Request - {self.server_name}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = email
            msg['Reply-To'] = self.reply_to_email
            
            # Create email content
            text_content = self._create_password_reset_text(username, reset_url, expires_hours)
            html_content = self._create_password_reset_html(username, reset_url, expires_hours)
            
            # Attach parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            success = self._send_email(msg)
            
            if success:
                logger.info(f"Password reset email sent successfully to {email} for user {username}")
                return True
            else:
                logger.error(f"Failed to send password reset email to {email} for user {username}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {e}")
            return False
    
    def _create_password_reset_text(self, username, reset_url, expires_hours):
        """Create plain text password reset email"""
        return f"""
Password Reset Request

Hello {username},

We received a request to reset your password for {self.server_name}.

To reset your password, click the link below or copy and paste it into your browser:

{reset_url}

This link will expire in {expires_hours} hours.

If you did not request a password reset, please ignore this email. Your password will remain unchanged.

For security reasons:
- Never share your password reset link with anyone
- The link can only be used once
- If the link expires, you can request a new one

If you have any questions or concerns, please contact your administrator.

Best regards,
{self.server_name} Team

---
This is an automated message. Please do not reply to this email.
"""
    
    def _create_password_reset_html(self, username, reset_url, expires_hours):
        """Create HTML password reset email"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background: #4CAF50;
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
        .security-note {{
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            padding: 15px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Password Reset Request</h1>
        <p>{self.server_name}</p>
    </div>
    
    <div class="content">
        <p>Hello <strong>{username}</strong>,</p>
        
        <p>We received a request to reset your password for {self.server_name}.</p>
        
        <p style="text-align: center;">
            <a href="{reset_url}" class="button">Reset Your Password</a>
        </p>
        
        <p style="text-align: center; color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <code style="background: #e9ecef; padding: 5px 10px; border-radius: 3px; display: inline-block; margin-top: 10px; word-break: break-all;">
                {reset_url}
            </code>
        </p>
        
        <div class="warning">
            <strong>⏰ Time Sensitive:</strong> This link will expire in <strong>{expires_hours} hours</strong>.
        </div>
        
        <div class="security-note">
            <strong>🛡️ Security Notes:</strong>
            <ul>
                <li>If you did not request a password reset, please ignore this email</li>
                <li>Never share your password reset link with anyone</li>
                <li>The link can only be used once</li>
                <li>If the link expires, you can request a new one</li>
            </ul>
        </div>
        
        <p>If you have any questions or concerns, please contact your administrator.</p>
        
        <p>Best regards,<br>
        <strong>{self.server_name} Team</strong></p>
    </div>
    
    <div class="footer">
        <p>This is an automated message. Please do not reply to this email.</p>
        <p>&copy; {datetime.now().year} {self.server_name}. All rights reserved.</p>
    </div>
</body>
</html>
"""


# Global email service instance
email_service = EmailService()
