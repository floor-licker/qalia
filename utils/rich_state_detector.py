"""
Rich State Detection System

This module provides comprehensive state detection capabilities to determine
if user actions (clicks, form submissions, etc.) actually achieved their intended purpose,
going far beyond simple "no timeout" detection.
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from playwright.async_api import Page

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """Comprehensive snapshot of page state at a given moment."""
    timestamp: float
    url: str
    page_title: str
    
    # DOM State
    element_count: int
    visible_element_count: int
    interactive_element_count: int
    dom_hash: str
    
    # Content State
    text_content_hash: str
    image_count: int
    link_count: int
    button_count: int
    form_count: int
    
    # Modal/Dialog State
    modal_present: bool
    dialog_present: bool
    overlay_present: bool
    popup_present: bool
    
    # CSS/Visual State
    css_classes: Set[str]
    visible_css_classes: Set[str]
    computed_styles_hash: str
    
    # ARIA/Accessibility State
    aria_states: Dict[str, Any]
    focus_element: Optional[str]
    
    # JavaScript State
    js_errors: List[str]
    console_messages: List[str]
    local_storage_keys: Set[str]
    session_storage_keys: Set[str]
    
    # Network State
    pending_requests: int
    recent_requests: List[str]
    
    # Form State
    form_values: Dict[str, Any]
    validation_messages: List[str]


@dataclass
class StateChange:
    """Detected change between two state snapshots."""
    change_type: str
    category: str
    severity: str  # low, medium, high, critical
    description: str
    evidence: Dict[str, Any]
    confidence: float  # 0.0 to 1.0


class RichStateDetector:
    """
    Comprehensive state detection system that can identify meaningful
    changes in web application state beyond simple URL navigation.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.baseline_snapshot: Optional[StateSnapshot] = None
        self.last_snapshot: Optional[StateSnapshot] = None
        self.change_history: List[StateChange] = []
        
    async def capture_baseline(self) -> StateSnapshot:
        """Capture the initial baseline state."""
        self.baseline_snapshot = await self._capture_snapshot()
        self.last_snapshot = self.baseline_snapshot
        logger.debug(f"📸 Baseline state captured: {self.baseline_snapshot.url}")
        return self.baseline_snapshot
    
    async def detect_changes_after_action(self, action_description: str, wait_time: float = 2.0) -> List[StateChange]:
        """
        Detect all meaningful state changes after an action is performed.
        
        Args:
            action_description: Description of the action that was performed
            wait_time: Time to wait for changes to settle
            
        Returns:
            List of detected state changes
        """
        logger.debug(f"🔍 Detecting state changes after: {action_description}")
        
        # Wait for immediate changes
        await asyncio.sleep(0.5)
        
        # Capture intermediate snapshots to detect rapid changes
        intermediate_snapshots = []
        for i in range(3):
            await asyncio.sleep(wait_time / 3)
            snapshot = await self._capture_snapshot()
            intermediate_snapshots.append(snapshot)
        
        # Analyze all changes
        all_changes = []
        previous_snapshot = self.last_snapshot
        
        for i, snapshot in enumerate(intermediate_snapshots):
            changes = await self._analyze_state_differences(previous_snapshot, snapshot, f"{action_description} (step {i+1})")
            all_changes.extend(changes)
            previous_snapshot = snapshot
        
        # Update last snapshot
        self.last_snapshot = intermediate_snapshots[-1] if intermediate_snapshots else self.last_snapshot
        
        # Add to change history
        self.change_history.extend(all_changes)
        
        logger.info(f"✅ Detected {len(all_changes)} state changes after {action_description}")
        return all_changes
    
    async def _capture_snapshot(self) -> StateSnapshot:
        """Capture a comprehensive snapshot of the current page state."""
        try:
            # Basic page info
            url = self.page.url
            title = await self.page.title()
            timestamp = time.time()
            
            # DOM State Analysis
            dom_info = await self._analyze_dom_state()
            
            # Content Analysis
            content_info = await self._analyze_content_state()
            
            # Modal/Dialog Detection
            modal_info = await self._detect_modals_and_dialogs()
            
            # CSS/Visual State
            css_info = await self._analyze_css_state()
            
            # ARIA/Accessibility State
            aria_info = await self._analyze_aria_state()
            
            # JavaScript State
            js_info = await self._analyze_javascript_state()
            
            # Network State
            network_info = await self._analyze_network_state()
            
            # Form State
            form_info = await self._analyze_form_state()
            
            return StateSnapshot(
                timestamp=timestamp,
                url=url,
                page_title=title,
                **dom_info,
                **content_info,
                **modal_info,
                **css_info,
                **aria_info,
                **js_info,
                **network_info,
                **form_info
            )
            
        except Exception as e:
            logger.error(f"❌ Error capturing state snapshot: {e}")
            # Return minimal snapshot on error
            return StateSnapshot(
                timestamp=time.time(),
                url=self.page.url,
                page_title="",
                element_count=0,
                visible_element_count=0,
                interactive_element_count=0,
                dom_hash="error",
                text_content_hash="error",
                image_count=0,
                link_count=0,
                button_count=0,
                form_count=0,
                modal_present=False,
                dialog_present=False,
                overlay_present=False,
                popup_present=False,
                css_classes=set(),
                visible_css_classes=set(),
                computed_styles_hash="error",
                aria_states={},
                focus_element=None,
                js_errors=[],
                console_messages=[],
                local_storage_keys=set(),
                session_storage_keys=set(),
                pending_requests=0,
                recent_requests=[],
                form_values={},
                validation_messages=[]
            )
    
    async def _analyze_dom_state(self) -> Dict[str, Any]:
        """Analyze DOM structure and element counts."""
        try:
            # Count different types of elements
            element_count = await self.page.evaluate("() => document.querySelectorAll('*').length")
            visible_element_count = await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('*');
                    let visibleCount = 0;
                    elements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                            visibleCount++;
                        }
                    });
                    return visibleCount;
                }
            """)
            
            interactive_element_count = await self.page.evaluate("""
                () => document.querySelectorAll('button, input, select, textarea, a[href], [onclick], [tabindex]').length
            """)
            
            # Create DOM structure hash for change detection
            dom_structure = await self.page.evaluate("""
                () => {
                    const createHash = (str) => {
                        let hash = 0;
                        for (let i = 0; i < str.length; i++) {
                            const char = str.charCodeAt(i);
                            hash = ((hash << 5) - hash) + char;
                            hash = hash & hash; // Convert to 32-bit integer
                        }
                        return hash.toString();
                    };
                    
                    const getStructure = (element, depth = 0) => {
                        if (depth > 10) return '';
                                            return element.tagName + (element.id ? '#' + element.id : '') + 
                           (element.className && typeof element.className === 'string' ? '.' + element.className.replace(/\\s+/g, '.') : '') +
                               Array.from(element.children).map(child => getStructure(child, depth + 1)).join('');
                    };
                    
                    return createHash(getStructure(document.body));
                }
            """)
            
            return {
                "element_count": element_count,
                "visible_element_count": visible_element_count,
                "interactive_element_count": interactive_element_count,
                "dom_hash": str(dom_structure)
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing DOM state: {e}")
            return {
                "element_count": 0,
                "visible_element_count": 0,
                "interactive_element_count": 0,
                "dom_hash": "error"
            }
    
    async def _analyze_content_state(self) -> Dict[str, Any]:
        """Analyze page content and media elements."""
        try:
            # Get text content hash
            text_content = await self.page.evaluate("() => document.body.innerText")
            text_hash = str(hash(text_content))
            
            # Count media and interactive elements
            image_count = await self.page.evaluate("() => document.querySelectorAll('img').length")
            link_count = await self.page.evaluate("() => document.querySelectorAll('a[href]').length")
            button_count = await self.page.evaluate("() => document.querySelectorAll('button, input[type=\"button\"], input[type=\"submit\"]').length")
            form_count = await self.page.evaluate("() => document.querySelectorAll('form').length")
            
            return {
                "text_content_hash": text_hash,
                "image_count": image_count,
                "link_count": link_count,
                "button_count": button_count,
                "form_count": form_count
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing content state: {e}")
            return {
                "text_content_hash": "error",
                "image_count": 0,
                "link_count": 0,
                "button_count": 0,
                "form_count": 0
            }
    
    async def _detect_modals_and_dialogs(self) -> Dict[str, Any]:
        """Detect presence of modals, dialogs, overlays, and popups."""
        try:
            modal_detection = await self.page.evaluate("""
                () => {
                    // Common modal selectors and patterns
                    const modalSelectors = [
                        '[role="dialog"]',
                        '[role="modal"]',
                        '.modal',
                        '.dialog',
                        '.popup',
                        '.overlay',
                        '[data-modal]',
                        '[data-dialog]',
                        '.MuiDialog-root',
                        '.ant-modal',
                        '.ui-dialog'
                    ];
                    
                    const checkOverlay = () => {
                        const elements = document.querySelectorAll('*');
                        for (let el of elements) {
                            const style = window.getComputedStyle(el);
                            if (style.position === 'fixed' && style.zIndex > 1000) {
                                return true;
                            }
                        }
                        return false;
                    };
                    
                    return {
                        modal_present: modalSelectors.some(sel => document.querySelector(sel) !== null),
                        dialog_present: document.querySelector('[role="dialog"]') !== null,
                        overlay_present: checkOverlay(),
                        popup_present: document.querySelector('.popup, [data-popup]') !== null
                    };
                }
            """)
            
            return modal_detection
        except Exception as e:
            logger.error(f"❌ Error detecting modals: {e}")
            return {
                "modal_present": False,
                "dialog_present": False,
                "overlay_present": False,
                "popup_present": False
            }
    
    async def _analyze_css_state(self) -> Dict[str, Any]:
        """Analyze CSS classes and computed styles."""
        try:
            css_analysis = await self.page.evaluate("""
                () => {
                    const allClasses = new Set();
                    const visibleClasses = new Set();
                    
                    document.querySelectorAll('*').forEach(el => {
                        if (el.className && typeof el.className === 'string' && el.className.trim()) {
                            el.className.split(/\\s+/).forEach(cls => {
                                if (cls && cls.trim()) {
                                    allClasses.add(cls.trim());
                                    
                                    const style = window.getComputedStyle(el);
                                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                                        visibleClasses.add(cls.trim());
                                    }
                                }
                            });
                        }
                    });
                    
                    // Create styles hash from key visual properties
                    const keyElements = document.querySelectorAll('body, header, nav, main, footer, .modal, .dialog');
                    let stylesString = '';
                    keyElements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        stylesString += style.display + style.position + style.zIndex + style.opacity;
                    });
                    
                    const createHash = (str) => {
                        let hash = 0;
                        for (let i = 0; i < str.length; i++) {
                            hash = ((hash << 5) - hash) + str.charCodeAt(i);
                            hash = hash & hash;
                        }
                        return hash.toString();
                    };
                    
                    return {
                        css_classes: Array.from(allClasses),
                        visible_css_classes: Array.from(visibleClasses),
                        computed_styles_hash: createHash(stylesString)
                    };
                }
            """)
            
            return {
                "css_classes": set(css_analysis["css_classes"]),
                "visible_css_classes": set(css_analysis["visible_css_classes"]),
                "computed_styles_hash": css_analysis["computed_styles_hash"]
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing CSS state: {e}")
            return {
                "css_classes": set(),
                "visible_css_classes": set(),
                "computed_styles_hash": "error"
            }
    
    async def _analyze_aria_state(self) -> Dict[str, Any]:
        """Analyze ARIA states and accessibility properties."""
        try:
            aria_analysis = await self.page.evaluate("""
                () => {
                    const ariaStates = {};
                    const focusElement = document.activeElement ? 
                        (document.activeElement.tagName + (document.activeElement.id ? '#' + document.activeElement.id : '')) : null;
                    
                    // Collect ARIA states from elements
                    document.querySelectorAll('[aria-expanded], [aria-selected], [aria-checked], [aria-hidden], [aria-disabled]').forEach((el, index) => {
                        const key = el.tagName + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '') + '_' + index;
                        ariaStates[key] = {
                            expanded: el.getAttribute('aria-expanded'),
                            selected: el.getAttribute('aria-selected'),
                            checked: el.getAttribute('aria-checked'),
                            hidden: el.getAttribute('aria-hidden'),
                            disabled: el.getAttribute('aria-disabled')
                        };
                    });
                    
                    return {
                        aria_states: ariaStates,
                        focus_element: focusElement
                    };
                }
            """)
            
            return aria_analysis
        except Exception as e:
            logger.error(f"❌ Error analyzing ARIA state: {e}")
            return {
                "aria_states": {},
                "focus_element": None
            }
    
    async def _analyze_javascript_state(self) -> Dict[str, Any]:
        """Analyze JavaScript errors and storage states."""
        try:
            js_analysis = await self.page.evaluate("""
                () => {
                    return {
                        local_storage_keys: Object.keys(localStorage),
                        session_storage_keys: Object.keys(sessionStorage)
                    };
                }
            """)
            
            return {
                "js_errors": [],  # TODO: Integrate with error handler
                "console_messages": [],  # TODO: Integrate with console listener
                "local_storage_keys": set(js_analysis["local_storage_keys"]),
                "session_storage_keys": set(js_analysis["session_storage_keys"])
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing JavaScript state: {e}")
            return {
                "js_errors": [],
                "console_messages": [],
                "local_storage_keys": set(),
                "session_storage_keys": set()
            }
    
    async def _analyze_network_state(self) -> Dict[str, Any]:
        """Analyze network requests and loading states."""
        try:
            # TODO: Integrate with network monitoring
            return {
                "pending_requests": 0,
                "recent_requests": []
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing network state: {e}")
            return {
                "pending_requests": 0,
                "recent_requests": []
            }
    
    async def _analyze_form_state(self) -> Dict[str, Any]:
        """Analyze form values and validation states."""
        try:
            form_analysis = await self.page.evaluate("""
                () => {
                    const formValues = {};
                    const validationMessages = [];
                    
                    // Collect form field values
                    document.querySelectorAll('input, select, textarea').forEach((field, index) => {
                        const key = field.name || field.id || field.type + '_' + index;
                        if (field.type === 'checkbox' || field.type === 'radio') {
                            formValues[key] = field.checked;
                        } else {
                            formValues[key] = field.value;
                        }
                    });
                    
                    // Collect validation messages
                    document.querySelectorAll('.error, .validation-error, [role="alert"]').forEach(el => {
                        if (el.textContent.trim()) {
                            validationMessages.push(el.textContent.trim());
                        }
                    });
                    
                    return {
                        form_values: formValues,
                        validation_messages: validationMessages
                    };
                }
            """)
            
            return form_analysis
        except Exception as e:
            logger.error(f"❌ Error analyzing form state: {e}")
            return {
                "form_values": {},
                "validation_messages": []
            }
    
    async def _analyze_state_differences(self, before: StateSnapshot, after: StateSnapshot, action_context: str) -> List[StateChange]:
        """Analyze differences between two state snapshots and identify meaningful changes."""
        changes = []
        
        # URL/Navigation Changes
        if before.url != after.url:
            changes.append(StateChange(
                change_type="navigation",
                category="url_change",
                severity="high",
                description=f"Navigation occurred: {before.url} → {after.url}",
                evidence={"from_url": before.url, "to_url": after.url},
                confidence=1.0
            ))
        
        # Modal/Dialog Changes
        if not before.modal_present and after.modal_present:
            changes.append(StateChange(
                change_type="ui_change",
                category="modal_opened",
                severity="high",
                description="Modal or dialog opened",
                evidence={"modal_present": True},
                confidence=0.9
            ))
        elif before.modal_present and not after.modal_present:
            changes.append(StateChange(
                change_type="ui_change",
                category="modal_closed",
                severity="medium",
                description="Modal or dialog closed",
                evidence={"modal_present": False},
                confidence=0.9
            ))
        
        # DOM Structure Changes
        if before.dom_hash != after.dom_hash:
            element_diff = after.element_count - before.element_count
            if abs(element_diff) > 0:
                changes.append(StateChange(
                    change_type="dom_change",
                    category="structure_change",
                    severity="medium" if abs(element_diff) > 5 else "low",
                    description=f"DOM structure changed: {element_diff:+} elements",
                    evidence={"element_diff": element_diff, "before_count": before.element_count, "after_count": after.element_count},
                    confidence=0.8
                ))
        
        # Content Changes
        if before.text_content_hash != after.text_content_hash:
            changes.append(StateChange(
                change_type="content_change",
                category="text_update",
                severity="medium",
                description="Page text content changed",
                evidence={"content_changed": True},
                confidence=0.7
            ))
        
        # CSS Class Changes
        new_classes = after.css_classes - before.css_classes
        removed_classes = before.css_classes - after.css_classes
        if new_classes or removed_classes:
            changes.append(StateChange(
                change_type="visual_change",
                category="css_classes",
                severity="low",
                description=f"CSS classes changed: +{len(new_classes)} -{len(removed_classes)}",
                evidence={"new_classes": list(new_classes), "removed_classes": list(removed_classes)},
                confidence=0.6
            ))
        
        # ARIA State Changes
        aria_changes = []
        for element_key in set(before.aria_states.keys()) | set(after.aria_states.keys()):
            before_aria = before.aria_states.get(element_key, {})
            after_aria = after.aria_states.get(element_key, {})
            if before_aria != after_aria:
                aria_changes.append({"element": element_key, "before": before_aria, "after": after_aria})
        
        if aria_changes:
            changes.append(StateChange(
                change_type="accessibility_change",
                category="aria_states",
                severity="medium",
                description=f"ARIA states changed for {len(aria_changes)} elements",
                evidence={"aria_changes": aria_changes},
                confidence=0.8
            ))
        
        # Focus Changes
        if before.focus_element != after.focus_element:
            changes.append(StateChange(
                change_type="interaction_change",
                category="focus_change",
                severity="low",
                description=f"Focus changed: {before.focus_element} → {after.focus_element}",
                evidence={"from_focus": before.focus_element, "to_focus": after.focus_element},
                confidence=0.9
            ))
        
        # Form State Changes
        form_changes = []
        all_form_keys = set(before.form_values.keys()) | set(after.form_values.keys())
        for key in all_form_keys:
            before_val = before.form_values.get(key)
            after_val = after.form_values.get(key)
            if before_val != after_val:
                form_changes.append({"field": key, "before": before_val, "after": after_val})
        
        if form_changes:
            changes.append(StateChange(
                change_type="form_change",
                category="field_values",
                severity="medium",
                description=f"Form values changed for {len(form_changes)} fields",
                evidence={"form_changes": form_changes},
                confidence=0.8
            ))
        
        # Validation Message Changes
        if before.validation_messages != after.validation_messages:
            changes.append(StateChange(
                change_type="validation_change",
                category="error_messages",
                severity="high",
                description="Validation messages changed",
                evidence={"before_messages": before.validation_messages, "after_messages": after.validation_messages},
                confidence=0.9
            ))
        
        logger.debug(f"🔍 Found {len(changes)} changes after {action_context}")
        return changes
    
    def get_action_success_assessment(self, changes: List[StateChange], element_type: str, action_type: str) -> Dict[str, Any]:
        """
        Assess whether an action was truly successful based on detected state changes.
        
        Returns:
            Dictionary with success assessment including confidence, evidence, and reasoning
        """
        if not changes:
            # No changes detected
            if element_type == "button":
                return {
                    "success": False,
                    "confidence": 0.7,
                    "reasoning": "Button click produced no detectable state changes",
                    "severity": "medium",
                    "evidence": "No DOM, visual, or functional changes observed"
                }
            elif element_type == "link":
                return {
                    "success": False,
                    "confidence": 0.8,
                    "reasoning": "Link click produced no navigation or state changes",
                    "severity": "high",
                    "evidence": "Expected navigation or content update not observed"
                }
            else:
                return {
                    "success": False,
                    "confidence": 0.6,
                    "reasoning": f"{element_type} interaction produced no detectable changes",
                    "severity": "medium",
                    "evidence": "No state changes observed"
                }
        
        # Analyze the types of changes
        high_confidence_success = any(
            change.change_type in ["navigation", "ui_change"] and change.category in ["url_change", "modal_opened", "modal_closed"]
            for change in changes
        )
        
        medium_confidence_success = any(
            change.change_type in ["dom_change", "content_change", "form_change", "accessibility_change"]
            for change in changes
        )
        
        if high_confidence_success:
            return {
                "success": True,
                "confidence": 0.9,
                "reasoning": "Action produced significant functional changes",
                "severity": "low",
                "evidence": f"Detected {len(changes)} changes including navigation/UI updates"
            }
        elif medium_confidence_success:
            return {
                "success": True,
                "confidence": 0.7,
                "reasoning": "Action produced moderate state changes",
                "severity": "low",
                "evidence": f"Detected {len(changes)} DOM/content changes"
            }
        else:
            # Only low-impact changes
            return {
                "success": True,
                "confidence": 0.5,
                "reasoning": "Action produced minor changes only",
                "severity": "low",
                "evidence": f"Detected {len(changes)} minor visual/focus changes"
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detector state to dictionary for serialization."""
        return {
            "baseline_snapshot": asdict(self.baseline_snapshot) if self.baseline_snapshot else None,
            "last_snapshot": asdict(self.last_snapshot) if self.last_snapshot else None,
            "change_history": [asdict(change) for change in self.change_history]
        } 