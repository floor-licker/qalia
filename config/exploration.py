"""
Exploration Configuration

Configuration classes for different exploration strategies and behaviors.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class ExplorationStrategy(Enum):
    """Available exploration strategies."""
    SYSTEMATIC = "systematic"
    INTELLIGENT = "intelligent"
    HYBRID = "hybrid"


class ActionPriority(Enum):
    """Priority levels for different action types."""
    HIGH = 1
    MEDIUM = 2  
    LOW = 3


@dataclass
class StrategyConfig:
    """Configuration for exploration strategies."""
    strategy: ExplorationStrategy = ExplorationStrategy.SYSTEMATIC
    max_actions_per_page: int = 50
    max_depth: int = 3
    breadth_first: bool = True
    prioritize_forms: bool = True
    skip_external_links: bool = True
    enable_modal_exploration: bool = True
    action_delay: float = 1.0  # seconds between actions


@dataclass
class ElementConfig:
    """Configuration for element discovery and interaction."""
    include_hidden: bool = False
    include_disabled: bool = False
    min_element_size: int = 10  # minimum width/height in pixels
    exclude_selectors: List[str] = None
    priority_selectors: Dict[str, ActionPriority] = None
    
    def __post_init__(self):
        if self.exclude_selectors is None:
            self.exclude_selectors = [
                '.advertisement',
                '.cookie-banner',
                '.tracking-pixel'
            ]
        
        if self.priority_selectors is None:
            self.priority_selectors = {
                'button': ActionPriority.HIGH,
                'input[type="submit"]': ActionPriority.HIGH,
                'a.primary': ActionPriority.HIGH,
                'input': ActionPriority.MEDIUM,
                'select': ActionPriority.MEDIUM,
                'a': ActionPriority.LOW
            }


@dataclass
class TimeoutConfig:
    """Configuration for various timeouts."""
    navigation_timeout: int = 30000  # milliseconds
    action_timeout: int = 5000
    element_wait_timeout: int = 10000
    page_load_timeout: int = 60000


@dataclass
class ExplorationConfig:
    """Main exploration configuration."""
    strategy: StrategyConfig = None
    elements: ElementConfig = None
    timeouts: TimeoutConfig = None
    
    # Global limits
    max_total_actions: int = 500
    max_session_duration: int = 3600  # seconds
    max_pages: int = 50
    
    # Error handling
    max_retries: int = 3
    continue_on_error: bool = True
    capture_screenshots_on_error: bool = True
    
    # Performance
    parallel_execution: bool = False
    batch_size: int = 5
    
    def __post_init__(self):
        if self.strategy is None:
            self.strategy = StrategyConfig()
        if self.elements is None:
            self.elements = ElementConfig()
        if self.timeouts is None:
            self.timeouts = TimeoutConfig()
            
    @classmethod
    def for_systematic_exploration(cls) -> 'ExplorationConfig':
        """Create config optimized for systematic exploration."""
        return cls(
            strategy=StrategyConfig(
                strategy=ExplorationStrategy.SYSTEMATIC,
                max_actions_per_page=100,
                breadth_first=True,
                prioritize_forms=True
            )
        )
        
    @classmethod  
    def for_intelligent_exploration(cls) -> 'ExplorationConfig':
        """Create config optimized for AI-guided exploration."""
        return cls(
            strategy=StrategyConfig(
                strategy=ExplorationStrategy.INTELLIGENT,
                max_actions_per_page=25,
                action_delay=2.0  # Slower for AI decision making
            )
        )
        
    @classmethod
    def for_quick_scan(cls) -> 'ExplorationConfig':
        """Create config for quick website scanning."""
        return cls(
            strategy=StrategyConfig(
                strategy=ExplorationStrategy.SYSTEMATIC,
                max_actions_per_page=20,
                max_depth=2
            ),
            max_total_actions=100,
            max_pages=10
        ) 