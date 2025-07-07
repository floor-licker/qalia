"""
Utils package for exhaustive website exploration.

This package contains modular components extracted from the various explorer implementations
to provide clean, reusable functionality for comprehensive website testing.
"""

# Import utilities with error handling for missing dependencies
try:
    from .browser_manager import BrowserManager, BrowserConfig
except ImportError as e:
    BrowserManager = None
    BrowserConfig = None
    print(f"Warning: BrowserManager not available: {e}")

try:
    from .element_extractor import ElementExtractor
except ImportError as e:
    ElementExtractor = None
    print(f"Warning: ElementExtractor not available: {e}")

try:
    from .action_executor import ActionExecutor, ActionConfig, ActionResult
except ImportError as e:
    ActionExecutor = None
    ActionConfig = None
    ActionResult = None
    print(f"Warning: ActionExecutor not available: {e}")

try:
    from .state_manager import StateManager, PageState, StateTransition
except ImportError as e:
    StateManager = None
    PageState = None
    StateTransition = None
    print(f"Warning: StateManager not available: {e}")

try:
    from .error_handler import ErrorHandler, ErrorRecord
except ImportError as e:
    ErrorHandler = None
    ErrorRecord = None
    print(f"Warning: ErrorHandler not available: {e}")

try:
    from .modal_handler import ModalHandler
except ImportError as e:
    ModalHandler = None
    print(f"Warning: ModalHandler not available: {e}")

try:
    from .session_reporter import SessionReporter
except ImportError as e:
    SessionReporter = None
    print(f"Warning: SessionReporter not available: {e}")

try:
    from .navigation_utils import NavigationUtils
except ImportError as e:
    NavigationUtils = None
    print(f"Warning: NavigationUtils not available: {e}")

try:
    from .typo_detector import TypoDetector
except ImportError as e:
    TypoDetector = None
    print(f"Warning: TypoDetector not available: {e}")

# Only include available components in __all__
__all__ = []
if BrowserManager is not None:
    __all__.extend(['BrowserManager', 'BrowserConfig'])
if ElementExtractor is not None:
    __all__.append('ElementExtractor')
if ActionExecutor is not None:
    __all__.extend(['ActionExecutor', 'ActionConfig', 'ActionResult'])
if StateManager is not None:
    __all__.extend(['StateManager', 'PageState', 'StateTransition'])
if ErrorHandler is not None:
    __all__.extend(['ErrorHandler', 'ErrorRecord'])
if ModalHandler is not None:
    __all__.append('ModalHandler')
if SessionReporter is not None:
    __all__.append('SessionReporter')
if NavigationUtils is not None:
    __all__.append('NavigationUtils')
if TypoDetector is not None:
    __all__.append('TypoDetector') 