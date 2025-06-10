"""
Error Handling Utility

Manages error detection, categorization, screenshot capture, and error reporting
for comprehensive website exploration error handling.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """Represents an error encountered during exploration."""
    error_type: str
    message: str
    url: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: str = 'medium'  # low, medium, high, critical


class ErrorHandler:
    """
    Centralized error handling for website exploration.
    
    Provides error categorization, screenshot capture, and comprehensive
    error tracking for analysis and debugging.
    """
    
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        
        # Error storage
        self.console_errors: List[ErrorRecord] = []
        self.http_errors: List[ErrorRecord] = []
        self.action_errors: List[ErrorRecord] = []
        self.navigation_errors: List[ErrorRecord] = []
        self.timeout_errors: List[ErrorRecord] = []
        
        # Error handlers
        self.custom_handlers: Dict[str, Callable] = {}
        
        # Error categorization rules
        self.severity_rules = {
            'critical': [
                'server error 500',
                'database connection',
                'application crash',
                'security violation'
            ],
            'high': [
                'javascript error',
                'uncaught exception',
                'network timeout',
                'authentication failed'
            ],
            'medium': [
                '404 not found',
                'validation error',
                'form submission failed',
                'asset loading failed'
            ],
            'low': [
                'warning',
                'deprecation',
                'console log',
                'network slow'
            ]
        }
    
    async def handle_console_error(self, message) -> ErrorRecord:
        """Handle console error messages."""
        try:
            error_text = message.text
            url = message.location.get('url', '') if message.location else ''
            line = message.location.get('line_number', 0) if message.location else 0
            
            # Categorize error
            severity = self._categorize_error_severity(error_text)
            
            error_record = ErrorRecord(
                error_type='console_error',
                message=error_text,
                url=url,
                timestamp=time.time(),
                context={
                    'message_type': message.type,
                    'source_url': url,
                    'line_number': line
                },
                severity=severity
            )
            
            # Capture screenshot for significant errors
            if severity in ['high', 'critical'] and self.session_manager:
                screenshot_path = await self._capture_error_screenshot(
                    'console_error',
                    error_text[:50],
                    url
                )
                error_record.screenshot_path = screenshot_path
            
            self.console_errors.append(error_record)
            
            # Call custom handlers
            await self._call_custom_handlers('console_error', error_record)
            
            logger.error(f"🚨 Console Error [{severity}]: {error_text[:100]}")
            
            return error_record
            
        except Exception as e:
            logger.error(f"Error handling console message: {e}")
            return None
    
    async def handle_http_error(self, response) -> ErrorRecord:
        """Handle HTTP error responses."""
        try:
            status_code = response.status
            url = response.url
            
            # Categorize error
            severity = self._categorize_http_error(status_code)
            error_type = self._get_http_error_type(status_code)
            
            error_record = ErrorRecord(
                error_type=error_type,
                message=f"HTTP {status_code} error for {url}",
                url=url,
                timestamp=time.time(),
                context={
                    'status_code': status_code,
                    'method': response.request.method if response.request else 'unknown',
                    'headers': dict(response.headers) if response.headers else {}
                },
                severity=severity
            )
            
            # Capture screenshot for significant errors
            if severity in ['high', 'critical'] and self.session_manager:
                screenshot_path = await self._capture_error_screenshot(
                    error_type,
                    f"HTTP_{status_code}",
                    url
                )
                error_record.screenshot_path = screenshot_path
            
            self.http_errors.append(error_record)
            
            # Call custom handlers
            await self._call_custom_handlers('http_error', error_record)
            
            logger.warning(f"🌐 HTTP Error [{severity}]: {status_code} - {url}")
            
            return error_record
            
        except Exception as e:
            logger.error(f"Error handling HTTP response: {e}")
            return None
    
    async def handle_action_error(self, action: Dict[str, Any], element: Dict[str, Any], 
                                error: str, page=None) -> ErrorRecord:
        """Handle action execution errors."""
        try:
            current_url = page.url if page else element.get('url', 'unknown')
            
            error_record = ErrorRecord(
                error_type='action_error',
                message=f"Action '{action.get('action', 'unknown')}' failed: {error}",
                url=current_url,
                timestamp=time.time(),
                context={
                    'action': action,
                    'element': element,
                    'error_details': error
                },
                severity=self._categorize_action_error(error)
            )
            
            # Capture screenshot
            if self.session_manager and page:
                screenshot_path = await self._capture_error_screenshot(
                    'action_error',
                    f"{action.get('action', 'unknown')}_{error[:30]}",
                    current_url
                )
                error_record.screenshot_path = screenshot_path
            
            self.action_errors.append(error_record)
            
            # Call custom handlers
            await self._call_custom_handlers('action_error', error_record)
            
            logger.error(f"⚡ Action Error: {error[:100]}")
            
            return error_record
            
        except Exception as e:
            logger.error(f"Error handling action error: {e}")
            return None
    
    async def handle_navigation_error(self, url: str, error: str, page=None) -> ErrorRecord:
        """Handle navigation errors."""
        try:
            error_record = ErrorRecord(
                error_type='navigation_error',
                message=f"Navigation to {url} failed: {error}",
                url=url,
                timestamp=time.time(),
                context={
                    'target_url': url,
                    'error_details': error
                },
                severity=self._categorize_navigation_error(error)
            )
            
            # Capture screenshot
            if self.session_manager and page:
                screenshot_path = await self._capture_error_screenshot(
                    'navigation_error',
                    error[:30],
                    url
                )
                error_record.screenshot_path = screenshot_path
            
            self.navigation_errors.append(error_record)
            
            # Call custom handlers
            await self._call_custom_handlers('navigation_error', error_record)
            
            logger.error(f"🧭 Navigation Error: {error[:100]}")
            
            return error_record
            
        except Exception as e:
            logger.error(f"Error handling navigation error: {e}")
            return None
    
    async def handle_timeout_error(self, operation: str, timeout: int, url: str, page=None) -> ErrorRecord:
        """Handle timeout errors."""
        try:
            error_record = ErrorRecord(
                error_type='timeout_error',
                message=f"Timeout during {operation} (after {timeout}ms)",
                url=url,
                timestamp=time.time(),
                context={
                    'operation': operation,
                    'timeout_ms': timeout,
                    'target_url': url
                },
                severity='medium'
            )
            
            # Capture screenshot
            if self.session_manager and page:
                screenshot_path = await self._capture_error_screenshot(
                    'timeout_error',
                    f"{operation}_{timeout}ms",
                    url
                )
                error_record.screenshot_path = screenshot_path
            
            self.timeout_errors.append(error_record)
            
            # Call custom handlers
            await self._call_custom_handlers('timeout_error', error_record)
            
            logger.warning(f"⏰ Timeout Error: {operation} after {timeout}ms")
            
            return error_record
            
        except Exception as e:
            logger.error(f"Error handling timeout: {e}")
            return None
    
    def register_handler(self, error_type: str, handler: Callable) -> None:
        """Register custom error handler."""
        self.custom_handlers[error_type] = handler
    
    async def _call_custom_handlers(self, error_type: str, error_record: ErrorRecord) -> None:
        """Call custom handlers for error type."""
        if error_type in self.custom_handlers:
            try:
                await self.custom_handlers[error_type](error_record)
            except Exception as e:
                logger.error(f"Custom error handler failed: {e}")
    
    async def _capture_error_screenshot(self, error_type: str, error_details: str, url: str) -> Optional[str]:
        """Capture screenshot for error context."""
        if not self.session_manager:
            return None
        
        try:
            return await self.session_manager.capture_error_screenshot(
                self.session_manager.page,  # Assuming session manager has page reference
                error_type,
                error_details,
                url
            )
        except Exception as e:
            logger.debug(f"Screenshot capture failed: {e}")
            return None
    
    def _categorize_error_severity(self, error_text: str) -> str:
        """Categorize error severity based on error text."""
        error_lower = error_text.lower()
        
        for severity, keywords in self.severity_rules.items():
            for keyword in keywords:
                if keyword in error_lower:
                    return severity
        
        return 'medium'  # Default
    
    def _categorize_http_error(self, status_code: int) -> str:
        """Categorize HTTP error severity."""
        if status_code >= 500:
            return 'critical'
        elif status_code == 404:
            return 'medium'
        elif status_code >= 400:
            return 'high'
        else:
            return 'low'
    
    def _categorize_action_error(self, error: str) -> str:
        """Categorize action error severity."""
        error_lower = error.lower()
        
        if any(keyword in error_lower for keyword in ['timeout', 'not found', 'not attached']):
            return 'medium'
        elif any(keyword in error_lower for keyword in ['security', 'permission', 'access denied']):
            return 'high'
        else:
            return 'medium'
    
    def _categorize_navigation_error(self, error: str) -> str:
        """Categorize navigation error severity."""
        error_lower = error.lower()
        
        if any(keyword in error_lower for keyword in ['timeout', 'network']):
            return 'high'
        elif 'not found' in error_lower:
            return 'medium'
        else:
            return 'medium'
    
    def _get_http_error_type(self, status_code: int) -> str:
        """Get specific HTTP error type."""
        error_map = {
            400: "400_bad_request", 401: "401_unauthorized", 403: "403_forbidden",
            404: "404_not_found", 405: "405_method_not_allowed", 408: "408_timeout",
            429: "429_rate_limit", 500: "500_server_error", 502: "502_bad_gateway",
            503: "503_unavailable", 504: "504_gateway_timeout"
        }
        
        if status_code in error_map:
            return error_map[status_code]
        elif 400 <= status_code < 500:
            return f"{status_code}_client_error"
        elif status_code >= 500:
            return f"{status_code}_server_error"
        else:
            return f"{status_code}_http_error"
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary."""
        all_errors = (
            self.console_errors + 
            self.http_errors + 
            self.action_errors + 
            self.navigation_errors + 
            self.timeout_errors
        )
        
        # Count by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for error in all_errors:
            severity_counts[error.severity] += 1
        
        # Count by type
        type_counts = {}
        for error in all_errors:
            error_type = error.error_type
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
        
        # Recent errors (last 10)
        recent_errors = sorted(all_errors, key=lambda x: x.timestamp, reverse=True)[:10]
        
        return {
            'total_errors': len(all_errors),
            'console_errors': len(self.console_errors),
            'http_errors': len(self.http_errors),
            'action_errors': len(self.action_errors),
            'navigation_errors': len(self.navigation_errors),
            'timeout_errors': len(self.timeout_errors),
            'severity_breakdown': severity_counts,
            'type_breakdown': type_counts,
            'recent_errors': [
                {
                    'type': e.error_type,
                    'message': e.message[:100],
                    'severity': e.severity,
                    'timestamp': e.timestamp
                }
                for e in recent_errors
            ]
        }
    
    def get_errors_by_severity(self, severity: str) -> List[ErrorRecord]:
        """Get all errors of specific severity."""
        all_errors = (
            self.console_errors + 
            self.http_errors + 
            self.action_errors + 
            self.navigation_errors + 
            self.timeout_errors
        )
        
        return [e for e in all_errors if e.severity == severity]
    
    def get_errors_by_type(self, error_type: str) -> List[ErrorRecord]:
        """Get all errors of specific type."""
        all_errors = (
            self.console_errors + 
            self.http_errors + 
            self.action_errors + 
            self.navigation_errors + 
            self.timeout_errors
        )
        
        return [e for e in all_errors if e.error_type == error_type]
    
    def clear_errors(self) -> None:
        """Clear all stored errors."""
        self.console_errors.clear()
        self.http_errors.clear()
        self.action_errors.clear()
        self.navigation_errors.clear()
        self.timeout_errors.clear()
        
        logger.info("🧹 All errors cleared")
    
    def export_errors_to_dict(self) -> Dict[str, Any]:
        """Export all errors to dictionary format."""
        def error_to_dict(error: ErrorRecord) -> Dict[str, Any]:
            return {
                'error_type': error.error_type,
                'message': error.message,
                'url': error.url,
                'timestamp': error.timestamp,
                'context': error.context,
                'screenshot_path': error.screenshot_path,
                'severity': error.severity
            }
        
        return {
            'console_errors': [error_to_dict(e) for e in self.console_errors],
            'http_errors': [error_to_dict(e) for e in self.http_errors],
            'action_errors': [error_to_dict(e) for e in self.action_errors],
            'navigation_errors': [error_to_dict(e) for e in self.navigation_errors],
            'timeout_errors': [error_to_dict(e) for e in self.timeout_errors],
            'summary': self.get_error_summary()
        } 