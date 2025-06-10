"""
Session Management Module

Handles exploration session persistence, state storage, and result management.
"""

from .manager import SessionManager, SessionConfig
from .storage import SessionStorage

__all__ = ['SessionManager', 'SessionConfig', 'SessionStorage'] 