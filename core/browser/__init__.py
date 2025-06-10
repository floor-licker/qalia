"""
Browser Management Module

Handles browser lifecycle, event management, and page interactions.
"""

from .manager import BrowserManager, BrowserConfig
from .events import EventHandler
from .lifecycle import BrowserLifecycle

__all__ = ['BrowserManager', 'BrowserConfig', 'EventHandler', 'BrowserLifecycle'] 