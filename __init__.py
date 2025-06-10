"""
QA-AI: Autonomous Website Testing and Exploration

A modular, intelligent system for automated website testing using Playwright and AI.

Key Components:
- Core: Browser management, sessions, state tracking
- Exploration: Strategies, element discovery, action execution
- Reporting: Analysis, formatting, and export capabilities
- Config: Centralized configuration management
- Explorers: Ready-to-use explorer implementations
"""

# Core components
from core import BrowserManager, SessionManager, StateTracker

# Exploration components  
from exploration import SystematicStrategy, ElementExtractor, ActionExecutor

# Configuration
from config import ExplorationConfig, BrowserConfig

# Ready-to-use explorers
from explorers import BasicExplorer, AdvancedExplorer

# Reporting
from reporting import XMLFormatter, BugAnalyzer, CoverageAnalyzer

__version__ = "2.0.0"

__all__ = [
    # Core
    'BrowserManager', 'SessionManager', 'StateTracker',
    
    # Exploration
    'SystematicStrategy', 'ElementExtractor', 'ActionExecutor',
    
    # Configuration
    'ExplorationConfig', 'BrowserConfig',
    
    # Explorers
    'BasicExplorer', 'AdvancedExplorer',
    
    # Reporting
    'XMLFormatter', 'BugAnalyzer', 'CoverageAnalyzer'
] 