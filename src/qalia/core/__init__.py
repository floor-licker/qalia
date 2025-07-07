"""
Core Qalia Components

This package contains the fundamental building blocks for web exploration:
- Browser management and lifecycle
- Session management and persistence
- State tracking and fingerprinting
"""

from .browser.manager import BrowserManager, BrowserConfig
from .session.manager import SessionManager

__all__ = [
    'BrowserManager', 'BrowserConfig',
    'SessionManager'
] 