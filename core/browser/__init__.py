"""
Browser Management Module

Handles browser lifecycle, event management, and page interactions.
"""

from .manager import BrowserManager, BrowserConfig
from .events import EventHandler

__all__ = ['BrowserManager', 'BrowserConfig', 'EventHandler'] 