#!/usr/bin/env python3
"""
Performance optimization module for high-speed web exploration.
Implements intelligent strategies to minimize delays and maximize throughput.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ActionProfile:
    """Profile of an action's execution characteristics."""
    action_type: str
    target_type: str
    average_duration: float
    success_rate: float
    timeout_rate: float
    priority_score: float
    
    
class PerformanceOptimizer:
    """
    Intelligent performance optimization for web exploration.
    Uses dynamic programming and greedy strategies to minimize execution time.
    """
    
    def __init__(self):
        # Action performance profiles (dynamic programming memoization)
        self.action_profiles: Dict[str, ActionProfile] = {}
        
        # Timing statistics
        self.execution_times: defaultdict = defaultdict(list)
        self.timeout_counts: defaultdict = defaultdict(int)
        self.success_counts: defaultdict = defaultdict(int)
        
        # Smart timeout management
        self.adaptive_timeouts: Dict[str, int] = {
            'default': 5000,      # 5 seconds (much faster than 30s)
            'modal_blocked': 2000, # 2 seconds for blocked elements
            'navigation': 8000,    # 8 seconds for page navigation
            'form_submit': 10000   # 10 seconds for form submissions
        }
        
        # Element prioritization
        self.priority_weights = {
            'button': 10,    # High priority - likely to cause state changes
            'link': 8,       # High priority - navigation
            'input': 6,      # Medium priority - data entry
            'select': 6,     # Medium priority - form elements
            'form': 5,       # Medium priority - form containers
            'generic': 3     # Low priority - other interactive elements
        }
        
        # Batch processing configuration
        self.batch_config = {
            'max_batch_size': 5,           # Max actions per batch
            'batch_delay': 0.5,            # Minimal delay between batches
            'state_check_interval': 3      # Check state every N actions
        }
    
    def get_adaptive_timeout(self, action: Dict[str, Any], element_type: str, 
                           is_modal_present: bool = False) -> int:
        """
        Get adaptive timeout based on action type and context.
        
        Args:
            action: Action being performed
            element_type: Type of element being interacted with
            is_modal_present: Whether a modal is currently blocking
            
        Returns:
            Timeout in milliseconds
        """
        action_key = f"{action.get('action')}_{element_type}"
        
        # Use learned timeout if available
        if action_key in self.action_profiles:
            profile = self.action_profiles[action_key]
            # If high timeout rate, use shorter timeout
            if profile.timeout_rate > 0.3:
                return self.adaptive_timeouts['modal_blocked']
        
        # Context-based timeouts
        if is_modal_present:
            return self.adaptive_timeouts['modal_blocked']
        elif action.get('action') == 'goto':
            return self.adaptive_timeouts['navigation']
        elif action.get('action') in ['fill', 'type'] and 'submit' in str(action.get('target', '')).lower():
            return self.adaptive_timeouts['form_submit']
        
        return self.adaptive_timeouts['default']
    
    def prioritize_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize elements using greedy strategy for maximum value.
        
        Args:
            elements: List of interactive elements
            
        Returns:
            Sorted list of elements by priority
        """
        def calculate_priority(element: Dict[str, Any]) -> float:
            base_priority = self.priority_weights.get(element.get('type', 'generic'), 3)
            
            # Boost priority for elements with high success rates
            element_key = f"{element.get('type')}_{element.get('tag_name', '')}"
            if element_key in self.action_profiles:
                profile = self.action_profiles[element_key]
                base_priority *= (1 + profile.success_rate)
                base_priority *= (2 - profile.timeout_rate)  # Penalize high timeout rates
            
            # Boost priority for modal triggers (high state change potential)
            element_text = str(element.get('text', '')).lower()
            if any(trigger in element_text for trigger in ['connect', 'login', 'sign', 'menu']):
                base_priority *= 1.5
            
            # Penalize elements that are likely to be blocked
            if element.get('potentially_blocked', False):
                base_priority *= 0.3
            
            return base_priority
        
        # Sort by priority (highest first)
        prioritized = sorted(elements, key=calculate_priority, reverse=True)
        
        logger.debug(f"Prioritized {len(elements)} elements: "
                    f"top 3 types: {[e.get('type') for e in prioritized[:3]]}")
        
        return prioritized
    
    def create_execution_batches(self, elements: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group elements into optimal execution batches.
        
        Args:
            elements: Prioritized list of elements
            
        Returns:
            List of batches for sequential execution
        """
        batches = []
        current_batch = []
        
        for element in elements:
            # Start new batch if current is full
            if len(current_batch) >= self.batch_config['max_batch_size']:
                batches.append(current_batch)
                current_batch = []
            
            current_batch.append(element)
        
        # Add final batch if not empty
        if current_batch:
            batches.append(current_batch)
        
        logger.debug(f"Created {len(batches)} execution batches")
        return batches
    
    def record_action_performance(self, action: Dict[str, Any], element: Dict[str, Any], 
                                duration: float, success: bool, timed_out: bool) -> None:
        """
        Record action performance for dynamic programming optimization.
        
        Args:
            action: Action that was performed
            element: Element that was acted upon
            duration: Execution duration in seconds
            success: Whether action succeeded
            timed_out: Whether action timed out
        """
        action_key = f"{action.get('action')}_{element.get('type', 'unknown')}"
        
        # Update timing statistics
        self.execution_times[action_key].append(duration)
        if success:
            self.success_counts[action_key] += 1
        if timed_out:
            self.timeout_counts[action_key] += 1
        
        # Update or create action profile
        total_attempts = len(self.execution_times[action_key])
        success_rate = self.success_counts[action_key] / total_attempts
        timeout_rate = self.timeout_counts[action_key] / total_attempts
        avg_duration = sum(self.execution_times[action_key]) / total_attempts
        
        # Calculate priority score (higher = better)
        priority_score = success_rate * (1 - timeout_rate) * (1 / (1 + avg_duration))
        
        self.action_profiles[action_key] = ActionProfile(
            action_type=action.get('action', ''),
            target_type=element.get('type', ''),
            average_duration=avg_duration,
            success_rate=success_rate,
            timeout_rate=timeout_rate,
            priority_score=priority_score
        )
        
        logger.debug(f"Updated profile for {action_key}: "
                    f"success={success_rate:.2f}, timeout={timeout_rate:.2f}, "
                    f"avg_time={avg_duration:.2f}s")
    
    def should_skip_element(self, element: Dict[str, Any], modal_present: bool = False) -> bool:
        """
        Determine if element should be skipped for performance reasons.
        
        Args:
            element: Element to evaluate
            modal_present: Whether modal is currently present
            
        Returns:
            True if element should be skipped
        """
        element_key = f"{element.get('type')}_{element.get('tag_name', '')}"
        
        # Skip if element has consistently failed
        if element_key in self.action_profiles:
            profile = self.action_profiles[element_key]
            if profile.timeout_rate > 0.8 and profile.success_rate < 0.1:
                logger.debug(f"Skipping {element_key} due to poor performance history")
                return True
        
        # Skip elements likely blocked by modal
        if modal_present and element.get('potentially_blocked', True):
            return True
        
        return False
    
    def get_minimal_wait_time(self, action_type: str) -> float:
        """
        Get minimal wait time based on action type and learned performance.
        
        Args:
            action_type: Type of action being performed
            
        Returns:
            Wait time in seconds
        """
        # Use learned timing if available
        action_profiles = [p for key, p in self.action_profiles.items() 
                          if p.action_type == action_type]
        
        if action_profiles:
            avg_duration = sum(p.average_duration for p in action_profiles) / len(action_profiles)
            # Wait for 50% of average duration (greedy approach)
            return max(0.1, avg_duration * 0.5)
        
        # Default minimal waits (much faster than current system)
        wait_times = {
            'click': 0.2,
            'fill': 0.3,
            'type': 0.3,
            'select': 0.2,
            'goto': 1.0
        }
        
        return wait_times.get(action_type, 0.2)
    
    def detect_modal_state_efficiently(self, page_info: Dict[str, Any]) -> bool:
        """
        Fast modal detection using heuristics.
        
        Args:
            page_info: Current page information
            
        Returns:
            True if modal is likely present
        """
        # Quick heuristic checks instead of expensive DOM queries
        modal_indicators = page_info.get('modal_present', {})
        
        return (
            modal_indicators.get('has_modal', False) or
            'fixed inset-0' in str(page_info.get('body_classes', '')) or
            any(keyword in str(page_info.get('title', '')).lower() 
                for keyword in ['dialog', 'modal', 'popup'])
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance optimization statistics."""
        total_actions = sum(len(times) for times in self.execution_times.values())
        total_timeouts = sum(self.timeout_counts.values())
        total_successes = sum(self.success_counts.values())
        
        avg_success_rate = total_successes / total_actions if total_actions > 0 else 0
        avg_timeout_rate = total_timeouts / total_actions if total_actions > 0 else 0
        
        return {
            'total_actions_tracked': total_actions,
            'overall_success_rate': avg_success_rate,
            'overall_timeout_rate': avg_timeout_rate,
            'learned_profiles': len(self.action_profiles),
            'top_performing_actions': sorted(
                self.action_profiles.items(),
                key=lambda x: x[1].priority_score,
                reverse=True
            )[:5]
        } 