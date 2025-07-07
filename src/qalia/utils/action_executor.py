"""
Action Execution Utility

Handles execution of various types of actions on web elements with
comprehensive error handling, retry logic, and adaptive timeouts.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from .browser_manager import BrowserManager
from .modal_handler import ModalHandler
from .error_handler import ErrorHandler
from .rich_state_detector import RichStateDetector, StateChange  # Import our new detector

logger = logging.getLogger(__name__)


@dataclass
class ActionConfig:
    """Configuration for action execution."""
    default_timeout: int = 5000
    retry_attempts: int = 2
    wait_after_action: float = 1.0
    modal_timeout: int = 2000
    form_timeout: int = 10000
    enable_screenshots: bool = True


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    action_type: str
    element_info: Dict[str, Any]
    duration: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    # Rich state detection results
    state_changes: List[StateChange] = None
    success_assessment: Dict[str, Any] = None
    baseline_state: Dict[str, Any] = None
    final_state: Dict[str, Any] = None


class ActionExecutor:
    """
    Executes actions on web elements with intelligent error handling and retry logic.
    
    Provides consistent action execution across different exploration strategies
    with adaptive timeouts and comprehensive error recovery.
    """
    
    def __init__(self, browser_manager: BrowserManager, modal_handler: ModalHandler, 
                 error_handler: ErrorHandler, config: ActionConfig = None):
        self.browser_manager = browser_manager
        self.modal_handler = modal_handler
        self.error_handler = error_handler
        self.config = config or ActionConfig()
        
        # Initialize rich state detector
        self.state_detector: Optional[RichStateDetector] = None
        
        # Test value generators
        self.test_values = {
            'text': 'Test Input',
            'email': 'test@example.com',
            'password': 'TestPass123',
            'search': 'search test',
            'tel': '555-1234',
            'url': 'https://example.com',
            'number': '123'
        }
        
        # Action history for learning
        self.action_history: list = []
    
    async def initialize_state_detection(self):
        """Initialize the rich state detection system."""
        if self.browser_manager.page:
            self.state_detector = RichStateDetector(self.browser_manager.page)
            await self.state_detector.capture_baseline()
            logger.info("🔍 Rich state detection initialized")
    
    async def execute_action(self, element: Dict[str, Any]) -> ActionResult:
        """
        Execute an action on an element with rich state change detection.
        
        Args:
            element: Element information containing selector, type, text, etc.
            
        Returns:
            ActionResult with comprehensive success assessment
        """
        start_time = time.time()
        action_type = self._determine_action_type(element)
        element_type = element.get('type', 'unknown')
        element_text = element.get('text', '')
        selector = element.get('selector', '')
        
        logger.info(f"🎯 Executing {action_type} on {element_type}: {element_text[:50]}")
                
        # Ensure state detector is initialized
        if not self.state_detector:
            await self.initialize_state_detection()
        
        try:
            # Capture baseline state before action
            baseline_snapshot = await self.state_detector.capture_baseline()
                
            # Execute the actual action
            success, error_message, screenshot_path = await self._execute_playwright_action(
                element, action_type
            )
                
            # Wait for state changes to settle
            await asyncio.sleep(self.config.wait_after_action)
                
            # Detect and analyze state changes
            action_description = f"{action_type} on {element_type} '{element_text}'"
            state_changes = await self.state_detector.detect_changes_after_action(action_description)
                
            # Get rich success assessment
            success_assessment = self.state_detector.get_action_success_assessment(
                state_changes, element_type, action_type
            )
            
            # Override simple success with rich assessment if we have high confidence
            if success_assessment["confidence"] > 0.8:
                success = success_assessment["success"]
                if not success and not error_message:
                    error_message = success_assessment["reasoning"]
            
            duration = time.time() - start_time
            
            # Log rich assessment results
            if state_changes:
                logger.info(f"✅ Rich analysis: {len(state_changes)} changes detected, "
                          f"success={success_assessment['success']} "
                          f"(confidence: {success_assessment['confidence']:.1%})")
                
                for change in state_changes[:3]:  # Log first 3 changes
                    logger.debug(f"   🔄 {change.change_type}: {change.description}")
            else:
                logger.warning(f"⚠️ No state changes detected for {action_description}")
            
            return ActionResult(
                success=success,
                action_type=action_type,
                element_info=element,
                duration=duration,
                error_message=error_message,
                screenshot_path=screenshot_path,
                state_changes=state_changes,
                success_assessment=success_assessment,
                baseline_state=baseline_snapshot.__dict__ if baseline_snapshot else None,
                final_state=self.state_detector.last_snapshot.__dict__ if self.state_detector.last_snapshot else None
            )
                    
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Action execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            return ActionResult(
                success=False,
                action_type=action_type,
                element_info=element,
                duration=duration,
                error_message=error_msg,
                state_changes=[],
                success_assessment={
                    "success": False,
                    "confidence": 1.0,
                    "reasoning": "Action execution threw exception",
                    "severity": "critical",
                    "evidence": str(e)
                }
            )

    async def _execute_playwright_action(self, element: Dict[str, Any], action_type: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Execute the actual Playwright action.
        
        Returns:
            Tuple of (success, error_message, screenshot_path)
        """
        try:
            selector = element.get('selector', '')
            page = self.browser_manager.page
            
            # Wait for element to be available
            await page.wait_for_selector(selector, timeout=self.config.default_timeout)
            
            # Get the element
            element_handle = page.locator(selector).first
        
            # Scroll element into view
            await element_handle.scroll_into_view_if_needed()
            
            # Wait for element to be actionable
            await element_handle.wait_for(state="visible", timeout=self.config.default_timeout)
            
            # Execute action based on type
            if action_type == "click":
                await element_handle.click(timeout=self.config.default_timeout)
            elif action_type == "hover":
                await element_handle.hover(timeout=self.config.default_timeout)
            elif action_type == "fill":
                text_to_fill = element.get('value', 'test input')
                await element_handle.fill(text_to_fill, timeout=self.config.default_timeout)
            elif action_type == "select":
                option_value = element.get('value', '0')
                await element_handle.select_option(option_value, timeout=self.config.default_timeout)
            else:
                # Default to click
                await element_handle.click(timeout=self.config.default_timeout)
            
            return True, None, None
            
        except Exception as e:
            error_message = f"Playwright action failed: {str(e)}"
            logger.error(f"❌ {error_message}")
            
            # Take error screenshot if enabled
            screenshot_path = None
            if self.config.enable_screenshots:
                try:
                    screenshot_path = await self._take_error_screenshot(element, str(e))
                except Exception as screenshot_error:
                    logger.error(f"❌ Failed to take error screenshot: {screenshot_error}")
            
            return False, error_message, screenshot_path
    
    async def _take_error_screenshot(self, element: Dict[str, Any], error: str) -> Optional[str]:
        """Take a screenshot when an action fails."""
        try:
            timestamp = int(time.time())
            element_text = element.get('text', 'unknown')[:20]
            filename = f"error_{timestamp}_{element_text}.png"
            
            # TODO: Integrate with session manager for proper path
            screenshot_path = f"screenshots/{filename}"
            await self.browser_manager.page.screenshot(path=screenshot_path)
            
            logger.info(f"📸 Error screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"❌ Failed to save error screenshot: {e}")
            return None
    
    def _determine_action_type(self, element: Dict[str, Any]) -> str:
        """Determine the appropriate action type for an element."""
        element_type = element.get('type', '').lower()
        tag_name = element.get('tag', '').lower()
        
        if element_type in ['button', 'submit']:
            return "click"
        elif element_type in ['text', 'email', 'password', 'search']:
            return "fill"
        elif element_type == 'select':
            return "select"
        elif tag_name in ['a', 'button']:
            return "click"
        elif tag_name in ['input', 'textarea']:
            return "fill"
        elif tag_name == 'select':
            return "select"
        else:
            return "click"  # Default action
    
    def _get_test_value(self, element: Dict[str, Any]) -> str:
        """Get appropriate test value for element."""
        element_type = element['type']
        
        if element_type == 'input':
            input_type = element.get('input_type', 'text')
            return self.test_values.get(input_type, 'test')
        elif element_type == 'textarea':
            return 'Test textarea content'
        elif element_type == 'select':
            options = element.get('options', [])
            if len(options) > 1:
                # Choose second option to avoid default
                return options[1].get('value', options[1].get('text', ''))
            return ''
        else:
            return ''
    
    def _get_adaptive_timeout(self, action_type: str, element: Dict[str, Any]) -> int:
        """Get adaptive timeout based on action type and element context."""
        base_timeout = self.config.default_timeout
        
        # Adjust based on action type
        if action_type in ['fill', 'type']:
            return self.config.form_timeout
        elif action_type == 'click':
            # Check if element might trigger modal
            text = element.get('text', '').lower()
            if any(keyword in text for keyword in ['login', 'sign', 'connect', 'modal']):
                return self.config.modal_timeout
        
        # Check action history for this element type
        similar_actions = [
            h for h in self.action_history[-20:]  # Last 20 actions
            if h['element_type'] == element['type'] and h['action'] == action_type
        ]
        
        if similar_actions:
            avg_duration = sum(h['duration'] for h in similar_actions) / len(similar_actions)
            # Add buffer to average duration
            adaptive_timeout = int(avg_duration * 1000 * 2)  # Convert to ms and double
            return max(base_timeout, min(adaptive_timeout, 15000))  # Cap at 15s
        
        return base_timeout
    
    async def _handle_timeout_retry(self, action: Dict[str, Any], element: Dict[str, Any], attempt: int) -> None:
        """Handle timeout-specific retry logic."""
        logger.info(f"🔄 Handling timeout retry (attempt {attempt + 1})")
        
        # Check for modals that might be blocking
        modal_detected = await self._check_for_blocking_modals()
        if modal_detected:
            logger.info("🎭 Modal detected, attempting to dismiss")
            await self._attempt_modal_dismissal()
        
        # Brief wait before retry
        await asyncio.sleep(1)
    
    async def _handle_error_retry(self, action: Dict[str, Any], element: Dict[str, Any], 
                                error: Exception, attempt: int) -> bool:
        """
        Handle general error retry logic.
        
        Returns:
            True if retry should continue, False if should abort
        """
        error_msg = str(error).lower()
        
        logger.info(f"🔄 Handling error retry (attempt {attempt + 1}): {error_msg[:50]}")
        
        # Handle specific error types
        if "strict mode violation" in error_msg and "resolved to" in error_msg:
            # Multiple elements found - modify selector
            return await self._handle_selector_ambiguity(action, element)
            
        elif "intercepts pointer events" in error_msg:
            # Element blocked by overlay
            return await self._handle_element_blocked(action, element)
            
        elif "not attached to the dom" in error_msg:
            # Element disappeared
            logger.warning("Element no longer in DOM, skipping retry")
            return False
            
        else:
            # General error - wait and retry
            await asyncio.sleep(2)
            return True
    
    async def _handle_selector_ambiguity(self, action: Dict[str, Any], element: Dict[str, Any]) -> bool:
        """Handle selector ambiguity by making selector more specific."""
        original_selector = action['target']
        
        if ':has-text(' in original_selector:
            # Make selector more specific by adding .first
            action['target'] = f"({original_selector}).first"
            logger.info(f"📍 Using more specific selector: {action['target']}")
            return True
        
        return False
    
    async def _handle_element_blocked(self, action: Dict[str, Any], element: Dict[str, Any]) -> bool:
        """Handle element blocked by overlay."""
        logger.info("🚧 Element blocked, attempting to clear overlays")
        
        # Try to dismiss modals/overlays
        modal_dismissed = await self._attempt_modal_dismissal()
        if modal_dismissed:
            await asyncio.sleep(1)
            return True
        
        # Try scrolling element into view
        try:
            locator = self.browser_manager.page.locator(action['target']).first
            await locator.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            return True
        except:
            pass
        
        return False
    
    async def _check_for_blocking_modals(self) -> bool:
        """Check for modals that might be blocking interactions."""
        modal_selectors = [
            '[role="dialog"]',
            '[aria-modal="true"]',
            '.modal',
            '.popup',
            '.overlay'
        ]
        
        for selector in modal_selectors:
            try:
                modal = self.browser_manager.page.locator(selector).first
                if await modal.is_visible():
                    return True
            except:
                continue
        
        return False
    
    async def _attempt_modal_dismissal(self) -> bool:
        """Attempt to dismiss blocking modals."""
        try:
            # Try ESC key
            await self.browser_manager.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # Check if modal is gone
            if not await self._check_for_blocking_modals():
                logger.info("✅ Modal dismissed with ESC key")
                return True
            
            # Try clicking close buttons
            close_selectors = [
                'button:has-text("Close")',
                'button:has-text("✕")',
                'button:has-text("×")',
                '[aria-label="Close"]'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = self.browser_manager.page.locator(selector).first
                    if await close_btn.is_visible():
                        await close_btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        
                        if not await self._check_for_blocking_modals():
                            logger.info(f"✅ Modal dismissed with close button: {selector}")
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Modal dismissal failed: {e}")
            return False
    
    def _record_action_result(self, action: Dict[str, Any], element: Dict[str, Any], 
                            success: bool, error: Optional[str]) -> None:
        """Record action result for learning and optimization."""
        result_record = {
            'action': action['action'],
            'element_type': element['type'],
            'success': success,
            'error': error,
            'timestamp': time.time(),
            'duration': 0  # Would be filled by caller
        }
        
        self.action_history.append(result_record)
        
        # Keep history manageable
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-50:]
    
    def get_action_success_rate(self, action_type: str = None, element_type: str = None) -> float:
        """Get success rate for specific action/element combinations."""
        if not self.action_history:
            return 0.0
        
        filtered_actions = self.action_history
        
        if action_type:
            filtered_actions = [a for a in filtered_actions if a['action'] == action_type]
        
        if element_type:
            filtered_actions = [a for a in filtered_actions if a['element_type'] == element_type]
        
        if not filtered_actions:
            return 0.0
        
        successes = sum(1 for a in filtered_actions if a['success'])
        return successes / len(filtered_actions)
    
    def get_action_stats(self) -> Dict[str, Any]:
        """Get comprehensive action execution statistics."""
        if not self.action_history:
            return {'total_actions': 0, 'success_rate': 0.0}
        
        total = len(self.action_history)
        successes = sum(1 for a in self.action_history if a['success'])
        
        # Group by action type
        action_stats = {}
        for action in self.action_history:
            action_type = action['action']
            if action_type not in action_stats:
                action_stats[action_type] = {'total': 0, 'successes': 0}
            
            action_stats[action_type]['total'] += 1
            if action['success']:
                action_stats[action_type]['successes'] += 1
        
        # Calculate success rates
        for action_type, stats in action_stats.items():
            stats['success_rate'] = stats['successes'] / stats['total']
        
        return {
            'total_actions': total,
            'success_rate': successes / total,
            'action_breakdown': action_stats
        }
    
    def get_state_detector_summary(self) -> Dict[str, Any]:
        """Get a summary of the state detector's findings."""
        if not self.state_detector:
            return {"initialized": False}
        
        return {
            "initialized": True,
            "total_changes_detected": len(self.state_detector.change_history),
            "change_types": list(set(change.change_type for change in self.state_detector.change_history)),
            "detector_state": self.state_detector.to_dict()
        } 