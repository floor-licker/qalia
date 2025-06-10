#!/usr/bin/env python3
"""
State fingerprinting system for graph-based web exploration.
Creates unique identifiers for different UI states beyond just URLs.
"""

import hashlib
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class UIState:
    """Represents a unique UI state that can be explored."""
    url: str
    page_hash: str
    interactive_elements: Optional[List[Dict[str, Any]]] = None  # NEW: Interactive elements in this state
    modal_state: Optional[Dict[str, Any]] = None
    dynamic_content: Optional[Dict[str, Any]] = None
    form_state: Optional[Dict[str, Any]] = None
    navigation_state: Optional[Dict[str, Any]] = None
    console_state: Optional[Dict[str, Any]] = None  # NEW: Console logs and errors
    
    def fingerprint(self) -> str:
        """Generate unique fingerprint for this state."""
        # Create element signature for fingerprinting (but not full details to avoid huge fingerprints)
        element_signature = None
        if self.interactive_elements:
            element_summary = {
                'count': len(self.interactive_elements),
                'types': sorted(list(set(elem.get('type', 'unknown') for elem in self.interactive_elements))),
                'key_elements': sorted([
                    f"{elem.get('type', 'unknown')}:{elem.get('text', elem.get('name', elem.get('selector', '')))[:20]}"
                    for elem in self.interactive_elements[:10]  # First 10 elements for signature
                ])
            }
            element_signature = element_summary
        
        state_data = {
            'url': self.url.split('#')[0],  # Remove fragment
            'page_hash': self.page_hash,
            'elements': element_signature,  # Include element signature in fingerprint
            'modal': self.modal_state,
            'dynamic': self.dynamic_content,
            'form': self.form_state,
            'navigation': self.navigation_state,
            'console': self.console_state  # Include console state in fingerprint
        }
        
        # Create deterministic hash
        state_str = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:12]
    
    def get_state_type(self) -> str:
        """Determine the primary type of this state."""
        if self.modal_state and self.modal_state.get('has_modal'):
            return 'modal'
        elif self.form_state and self.form_state.get('filled_fields'):
            return 'form'
        elif self.dynamic_content and self.dynamic_content.get('loaded_content'):
            return 'dynamic'
        elif self.navigation_state and self.navigation_state.get('expanded_menus'):
            return 'navigation'
        else:
            return 'page'
    
    def get_untested_elements(self, tested_element_signatures: set) -> List[Dict[str, Any]]:
        """Get interactive elements that haven't been tested yet."""
        if not self.interactive_elements:
            return []
        
        untested = []
        for element in self.interactive_elements:
            # Create element signature for comparison
            element_sig = f"{element.get('type', 'unknown')}:{element.get('selector', '')}"
            if element_sig not in tested_element_signatures:
                untested.append(element)
        
        return untested


@dataclass
class StateTransition:
    """Represents a transition from one state to another via an action."""
    from_state: str  # fingerprint
    to_state: str    # fingerprint
    action: Dict[str, Any]
    success: bool
    observable_changes: List[str]
    execution_time: float
    timestamp: str


class StateGraph:
    """Manages the graph of UI states and transitions."""
    
    def __init__(self):
        self.states: Dict[str, UIState] = {}
        self.transitions: List[StateTransition] = []
        self.current_state: Optional[str] = None
    
    def add_state(self, state: UIState) -> str:
        """Add a new state to the graph."""
        fingerprint = state.fingerprint()
        self.states[fingerprint] = state
        return fingerprint
    
    def add_transition(self, transition: StateTransition) -> None:
        """Add a transition between states."""
        self.transitions.append(transition)
    
    def get_unexplored_transitions(self, from_state: str) -> List[Dict[str, Any]]:
        """Get potential actions that haven't been tried from this state."""
        # Find all transitions already tried from this state
        tried_actions = set()
        for transition in self.transitions:
            if transition.from_state == from_state:
                action_sig = self._action_signature(transition.action)
                tried_actions.add(action_sig)
        
        # Return elements that haven't been tried
        state = self.states.get(from_state)
        if not state:
            return []
        
        # This would be populated by the state extraction process
        available_elements = getattr(state, 'interactive_elements', [])
        
        unexplored = []
        for element in available_elements:
            action_sig = self._element_to_action_signature(element)
            if action_sig not in tried_actions:
                unexplored.append(element)
        
        return unexplored
    
    def _action_signature(self, action: Dict[str, Any]) -> str:
        """Create signature for an action."""
        sig_data = {
            'action': action.get('action'),
            'target': action.get('target'),
            'value': action.get('value') if action.get('action') in ['fill', 'type'] else None
        }
        return json.dumps(sig_data, sort_keys=True)
    
    def _element_to_action_signature(self, element: Dict[str, Any]) -> str:
        """Convert element to action signature."""
        # This would create the action that would be performed on this element
        element_type = element.get('type')
        if element_type == 'button' or element_type == 'link':
            action = {'action': 'click', 'target': element.get('selector')}
        elif element_type == 'input':
            action = {'action': 'fill', 'target': element.get('selector'), 'value': 'test'}
        else:
            action = {'action': 'click', 'target': element.get('selector')}
        
        return self._action_signature(action)
    
    def export_to_xml(self, domain: str = "unknown", output_file: str = None) -> str:
        """
        Export the complete state graph to XML format.
        
        Args:
            domain: Domain name for the application
            output_file: Optional file path to save XML
            
        Returns:
            XML content as string
        """
        # Create root element
        root = ET.Element("ApplicationStateFingerprint")
        root.set("domain", domain)
        root.set("timestamp", datetime.now().isoformat())
        root.set("total_states", str(len(self.states)))
        root.set("total_transitions", str(len(self.transitions)))
        
        # Add metadata
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "GeneratedBy").text = "QA AI State-Based Explorer"
        ET.SubElement(metadata, "Version").text = "1.0"
        ET.SubElement(metadata, "Description").text = "Complete UI state fingerprint map with transitions and console tracking"
        
        # Add states section
        states_elem = ET.SubElement(root, "States")
        states_elem.set("count", str(len(self.states)))
        
        for fingerprint, state in self.states.items():
            state_elem = ET.SubElement(states_elem, "State")
            state_elem.set("fingerprint", fingerprint)
            state_elem.set("type", state.get_state_type())
            
            # Basic state info
            ET.SubElement(state_elem, "URL").text = state.url
            ET.SubElement(state_elem, "PageHash").text = state.page_hash
            
            # Interactive elements inventory
            if state.interactive_elements:
                elements_elem = ET.SubElement(state_elem, "InteractiveElements")
                elements_elem.set("count", str(len(state.interactive_elements)))
                
                # Group elements by type
                elements_by_type = {}
                for element in state.interactive_elements:
                    elem_type = element.get('type', 'unknown')
                    if elem_type not in elements_by_type:
                        elements_by_type[elem_type] = []
                    elements_by_type[elem_type].append(element)
                
                for elem_type, elements in elements_by_type.items():
                    type_elem = ET.SubElement(elements_elem, "ElementType")
                    type_elem.set("type", elem_type)
                    type_elem.set("count", str(len(elements)))
                    
                    for element in elements[:10]:  # Limit to first 10 per type to avoid huge XML
                        elem_elem = ET.SubElement(type_elem, "Element")
                        elem_elem.set("selector", element.get('selector', ''))
                        
                        if element.get('text'):
                            ET.SubElement(elem_elem, "Text").text = element['text'][:50]  # Truncate long text
                        if element.get('name'):
                            ET.SubElement(elem_elem, "Name").text = element['name']
                        if element.get('input_type'):
                            elem_elem.set("input_type", element['input_type'])
                        if element.get('href'):
                            ET.SubElement(elem_elem, "Href").text = element['href'][:100]  # Truncate long URLs
                        if element.get('placeholder'):
                            ET.SubElement(elem_elem, "Placeholder").text = element['placeholder']
            
            # Modal state
            if state.modal_state:
                modal_elem = ET.SubElement(state_elem, "ModalState")
                modal_elem.set("has_modal", str(state.modal_state.get('has_modal', False)))
                if state.modal_state.get('modal_types'):
                    types_elem = ET.SubElement(modal_elem, "ModalTypes")
                    for modal_type in state.modal_state['modal_types']:
                        ET.SubElement(types_elem, "Type").text = modal_type
                if state.modal_state.get('modal_selectors'):
                    selectors_elem = ET.SubElement(modal_elem, "ModalSelectors")
                    for selector in state.modal_state['modal_selectors']:
                        ET.SubElement(selectors_elem, "Selector").text = selector
            
            # Console state
            if state.console_state:
                console_elem = ET.SubElement(state_elem, "ConsoleState")
                console_elem.set("has_activity", str(state.console_state.get('has_console_activity', False)))
                console_elem.set("health", state.console_state.get('state_health', 'unknown'))
                
                # Log summary
                if state.console_state.get('log_summary'):
                    log_summary = state.console_state['log_summary']
                    log_elem = ET.SubElement(console_elem, "LogSummary")
                    log_elem.set("total_logs", str(log_summary.get('total_logs', 0)))
                    log_elem.set("has_errors", str(log_summary.get('has_errors', False)))
                    log_elem.set("has_warnings", str(log_summary.get('has_warnings', False)))
                    
                    if log_summary.get('counts_by_type'):
                        counts_elem = ET.SubElement(log_elem, "CountsByType")
                        for log_type, count in log_summary['counts_by_type'].items():
                            count_elem = ET.SubElement(counts_elem, "Count")
                            count_elem.set("type", log_type)
                            count_elem.text = str(count)
                    
                    if log_summary.get('recent_logs'):
                        recent_elem = ET.SubElement(log_elem, "RecentLogs")
                        for i, log in enumerate(log_summary['recent_logs']):
                            log_entry = ET.SubElement(recent_elem, "LogEntry")
                            log_entry.set("index", str(i))
                            log_entry.text = log
                
                # Network error summary
                if state.console_state.get('error_summary'):
                    error_summary = state.console_state['error_summary']
                    error_elem = ET.SubElement(console_elem, "NetworkErrorSummary")
                    error_elem.set("total_errors", str(error_summary.get('total_network_errors', 0)))
                    error_elem.set("has_critical", str(error_summary.get('has_critical_failures', False)))
                    
                    if error_summary.get('categories'):
                        categories_elem = ET.SubElement(error_elem, "ErrorCategories")
                        for category, count in error_summary['categories'].items():
                            cat_elem = ET.SubElement(categories_elem, "Category")
                            cat_elem.set("name", category)
                            cat_elem.text = str(count)
                    
                    if error_summary.get('recent_failures'):
                        failures_elem = ET.SubElement(error_elem, "RecentFailures")
                        for i, failure in enumerate(error_summary['recent_failures']):
                            failure_elem = ET.SubElement(failures_elem, "Failure")
                            failure_elem.set("index", str(i))
                            failure_elem.set("category", failure.get('category', 'unknown'))
                            if failure.get('url'):
                                ET.SubElement(failure_elem, "URL").text = failure['url']
                            if failure.get('failure'):
                                ET.SubElement(failure_elem, "Error").text = failure['failure']
                            if failure.get('timestamp'):
                                ET.SubElement(failure_elem, "Timestamp").text = failure['timestamp']
                
                # Critical issues
                if state.console_state.get('critical_issues'):
                    critical_elem = ET.SubElement(console_elem, "CriticalIssues")
                    for i, issue in enumerate(state.console_state['critical_issues']):
                        issue_elem = ET.SubElement(critical_elem, "Issue")
                        issue_elem.set("index", str(i))
                        issue_elem.text = issue
            
            # Form state
            if state.form_state:
                form_elem = ET.SubElement(state_elem, "FormState")
                form_elem.set("form_count", str(state.form_state.get('form_count', 0)))
                if state.form_state.get('form_types'):
                    types_elem = ET.SubElement(form_elem, "FormTypes")
                    for form_type in state.form_state['form_types']:
                        ET.SubElement(types_elem, "Type").text = form_type
            
            # Navigation state
            if state.navigation_state:
                nav_elem = ET.SubElement(state_elem, "NavigationState")
                # Add navigation state details as needed
            
            # Dynamic content state
            if state.dynamic_content:
                dynamic_elem = ET.SubElement(state_elem, "DynamicContentState")
                # Add dynamic content details as needed
        
        # Add transitions section
        transitions_elem = ET.SubElement(root, "Transitions")
        transitions_elem.set("count", str(len(self.transitions)))
        
        for i, transition in enumerate(self.transitions):
            trans_elem = ET.SubElement(transitions_elem, "Transition")
            trans_elem.set("index", str(i))
            trans_elem.set("success", str(transition.success))
            
            ET.SubElement(trans_elem, "FromState").text = transition.from_state
            ET.SubElement(trans_elem, "ToState").text = transition.to_state
            ET.SubElement(trans_elem, "Timestamp").text = transition.timestamp
            ET.SubElement(trans_elem, "ExecutionTime").text = str(transition.execution_time)
            
            # Action details
            action_elem = ET.SubElement(trans_elem, "Action")
            action_elem.set("type", transition.action.get('action', 'unknown'))
            if transition.action.get('target'):
                ET.SubElement(action_elem, "Target").text = transition.action['target']
            if transition.action.get('value'):
                ET.SubElement(action_elem, "Value").text = str(transition.action['value'])
            
            # Observable changes
            if transition.observable_changes:
                changes_elem = ET.SubElement(trans_elem, "ObservableChanges")
                for j, change in enumerate(transition.observable_changes):
                    change_elem = ET.SubElement(changes_elem, "Change")
                    change_elem.set("index", str(j))
                    change_elem.text = change
        
        # Add statistics section
        stats_elem = ET.SubElement(root, "Statistics")
        
        # State statistics
        state_types = {}
        for state in self.states.values():
            state_type = state.get_state_type()
            state_types[state_type] = state_types.get(state_type, 0) + 1
        
        state_stats_elem = ET.SubElement(stats_elem, "StateStatistics")
        for state_type, count in state_types.items():
            type_elem = ET.SubElement(state_stats_elem, "StateType")
            type_elem.set("name", state_type)
            type_elem.text = str(count)
        
        # Transition statistics
        successful_transitions = sum(1 for t in self.transitions if t.success)
        trans_stats_elem = ET.SubElement(stats_elem, "TransitionStatistics")
        ET.SubElement(trans_stats_elem, "SuccessfulTransitions").text = str(successful_transitions)
        ET.SubElement(trans_stats_elem, "FailedTransitions").text = str(len(self.transitions) - successful_transitions)
        if self.transitions:
            success_rate = (successful_transitions / len(self.transitions)) * 100
            ET.SubElement(trans_stats_elem, "SuccessRate").text = f"{success_rate:.2f}%"
        
        # Console activity statistics
        states_with_console_activity = sum(1 for state in self.states.values() 
                                         if state.console_state and state.console_state.get('has_console_activity'))
        states_with_critical_issues = sum(1 for state in self.states.values()
                                        if state.console_state and state.console_state.get('state_health') == 'critical')
        
        console_stats_elem = ET.SubElement(stats_elem, "ConsoleStatistics")
        ET.SubElement(console_stats_elem, "StatesWithConsoleActivity").text = str(states_with_console_activity)
        ET.SubElement(console_stats_elem, "StatesWithCriticalIssues").text = str(states_with_critical_issues)
        if len(self.states) > 0:
            console_coverage = (states_with_console_activity / len(self.states)) * 100
            ET.SubElement(console_stats_elem, "ConsoleCoveragePercentage").text = f"{console_coverage:.2f}%"
        
        # Convert to pretty-formatted XML string
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Remove empty lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        xml_content = '\n'.join(lines)
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            print(f"Application state fingerprint exported to: {output_file}")
        
        return xml_content


class StateExtractor:
    """Extracts UI state information from page content."""
    
    def extract_ui_state(self, page, url: str, page_info: Dict[str, Any], 
                        console_logs: List[str] = None, network_errors: List[Dict] = None,
                        interactive_elements: List[Dict[str, Any]] = None) -> UIState:
        """Extract current UI state from page."""
        
        # Calculate page content hash
        page_hash = self._calculate_page_hash(page_info)
        
        # Extract modal state
        modal_state = self._extract_modal_state(page_info)
        
        # Extract dynamic content state  
        dynamic_content = self._extract_dynamic_content(page_info)
        
        # Extract form state
        form_state = self._extract_form_state(page_info)
        
        # Extract navigation state
        navigation_state = self._extract_navigation_state(page_info)
        
        # Extract console state (NEW)
        console_state = self._extract_console_state(console_logs, network_errors)
        
        return UIState(
            url=url,
            page_hash=page_hash,
            interactive_elements=interactive_elements,  # Pass provided elements directly
            modal_state=modal_state,
            dynamic_content=dynamic_content,
            form_state=form_state,
            navigation_state=navigation_state,
            console_state=console_state
        )
    
    def _calculate_page_hash(self, page_info: Dict[str, Any]) -> str:
        """Calculate hash of core page content."""
        content_data = {
            'title': page_info.get('title', ''),
            'headings': page_info.get('headings', []),
            'forms_count': len(page_info.get('forms', [])),
            'has_nav': page_info.get('has_nav', False)
        }
        
        content_str = json.dumps(content_data, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _extract_modal_state(self, page_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract modal/dialog state."""
        modal_info = page_info.get('modal_present')
        if modal_info and modal_info.get('has_modal'):
            return {
                'has_modal': True,
                'modal_types': modal_info.get('modal_types', []),
                'modal_selectors': modal_info.get('modal_selectors_found', [])
            }
        return None
    
    def _extract_dynamic_content(self, page_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract dynamically loaded content state."""
        # Look for indicators of loaded content
        dynamic_indicators = {
            'has_loading_elements': False,
            'has_ajax_content': False,
            'loaded_content_types': []
        }
        
        # Check for loading indicators in the page
        if 'loading' in str(page_info).lower() or 'spinner' in str(page_info).lower():
            dynamic_indicators['has_loading_elements'] = True
        
        # Check for common AJAX content patterns
        if any(keyword in str(page_info).lower() for keyword in ['data-src', 'lazy-load', 'ajax']):
            dynamic_indicators['has_ajax_content'] = True
            dynamic_indicators['loaded_content_types'].append('ajax')
        
        # Return state if any dynamic content detected
        if dynamic_indicators['has_loading_elements'] or dynamic_indicators['has_ajax_content']:
            return {
                'loaded_content': True,
                'indicators': dynamic_indicators
            }
        
        return None
    
    def _extract_form_state(self, page_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract form fill state."""
        forms = page_info.get('forms', [])
        if forms:
            return {
                'form_count': len(forms),
                'filled_fields': [],  # Would track which fields are filled
                'form_types': [form.get('method', 'GET') for form in forms]
            }
        return None
    
    def _extract_navigation_state(self, page_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract navigation/menu state."""
        # Look for expanded menus, dropdowns, etc.
        nav_state = {
            'has_navigation': page_info.get('has_nav', False),
            'expanded_menus': [],
            'dropdown_states': []
        }
        
        # Check for navigation elements
        if nav_state['has_navigation']:
            # Look for common navigation patterns
            page_content = str(page_info).lower()
            if 'menu-open' in page_content or 'nav-expanded' in page_content:
                nav_state['expanded_menus'].append('main-menu')
            
            if 'dropdown-open' in page_content or 'submenu' in page_content:
                nav_state['dropdown_states'].append('expanded')
            
            return {
                'expanded_menus': nav_state['expanded_menus'],
                'dropdown_states': nav_state['dropdown_states'],
                'navigation_active': len(nav_state['expanded_menus']) > 0 or len(nav_state['dropdown_states']) > 0
            }
        
        return None
    
    def _extract_console_state(self, console_logs: List[str] = None, network_errors: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Extract console state including logs and network errors.
        
        Args:
            console_logs: List of console log messages
            network_errors: List of network error dictionaries
            
        Returns:
            Console state dictionary or None if no console activity
        """
        if not console_logs and not network_errors:
            return None
        
        console_state = {
            'has_console_activity': bool(console_logs or network_errors),
            'log_summary': {},
            'error_summary': {},
            'critical_issues': []
        }
        
        # Process console logs
        if console_logs:
            log_counts = {'error': 0, 'warning': 0, 'info': 0, 'debug': 0}
            recent_logs = []
            
            for log in console_logs[-10:]:  # Keep last 10 logs for state differentiation
                log_lower = log.lower()
                if '[error]' in log_lower or 'error' in log_lower:
                    log_counts['error'] += 1
                    if len(recent_logs) < 5:  # Track up to 5 recent critical logs
                        recent_logs.append(log)
                elif '[warning]' in log_lower or 'warning' in log_lower:
                    log_counts['warning'] += 1
                elif '[page_error]' in log_lower:
                    log_counts['error'] += 1
                    console_state['critical_issues'].append(log)
                    if len(recent_logs) < 5:
                        recent_logs.append(log)
            
            console_state['log_summary'] = {
                'total_logs': len(console_logs),
                'counts_by_type': log_counts,
                'recent_logs': recent_logs,
                'has_errors': log_counts['error'] > 0,
                'has_warnings': log_counts['warning'] > 0
            }
        
        # Process network errors
        if network_errors:
            error_categories = {}
            recent_failures = []
            
            for error in network_errors[-10:]:  # Keep last 10 network errors
                category = error.get('category', 'UNKNOWN')
                error_categories[category] = error_categories.get(category, 0) + 1
                
                # Track critical failures (API, NETWORK, UNKNOWN)
                if category in ['API', 'NETWORK', 'UNKNOWN'] and len(recent_failures) < 5:
                    recent_failures.append({
                        'url': error.get('url'),
                        'category': category,
                        'failure': error.get('failure'),
                        'timestamp': error.get('timestamp')
                    })
            
            console_state['error_summary'] = {
                'total_network_errors': len(network_errors),
                'categories': error_categories,
                'recent_failures': recent_failures,
                'has_critical_failures': any(cat in error_categories 
                                           for cat in ['API', 'NETWORK', 'UNKNOWN'])
            }
        
        # Determine if this console state indicates problems
        has_critical_issues = (
            console_state.get('log_summary', {}).get('has_errors', False) or
            console_state.get('error_summary', {}).get('has_critical_failures', False) or
            len(console_state.get('critical_issues', [])) > 0
        )
        
        console_state['state_health'] = 'critical' if has_critical_issues else 'normal'
        
        return console_state


# Integration with existing exploration
class StateBasedExplorer:
    """Enhanced explorer that uses state-based navigation."""
    
    def __init__(self):
        self.state_graph = StateGraph()
        self.state_extractor = StateExtractor()
        self.exploration_queue = []  # Queue of states to explore
    
    async def explore_with_state_tracking(self, page, url: str):
        """Explore using state-based approach."""
        
        # Extract current state
        page_info = {}  # Would get from existing extraction
        current_ui_state = self.state_extractor.extract_ui_state(page, url, page_info)
        state_fingerprint = self.state_graph.add_state(current_ui_state)
        
        # Get unexplored actions from this state
        unexplored_elements = self.state_graph.get_unexplored_transitions(state_fingerprint)
        
        # For each unexplored element, perform action and track state change
        for element in unexplored_elements:
            # Perform action
            action = self._create_action_for_element(element)
            before_state = state_fingerprint
            
            # Execute action and capture new state
            action_result = await self._execute_action(action)
            
            # Extract new state after action
            new_page_info = {}  # Would extract new page state
            new_ui_state = self.state_extractor.extract_ui_state(page, page.url, new_page_info)
            after_state = self.state_graph.add_state(new_ui_state)
            
            # Record transition
            transition = StateTransition(
                from_state=before_state,
                to_state=after_state,
                action=action,
                success=action_result.get('success', False),
                observable_changes=action_result.get('observable_changes', []),
                execution_time=action_result.get('execution_time', 0),
                timestamp=action_result.get('timestamp', '')
            )
            
            self.state_graph.add_transition(transition)
            
            # If we reached a new state, add it to exploration queue
            if after_state != before_state and after_state not in self.exploration_queue:
                self.exploration_queue.append(after_state)
    
    def _create_action_for_element(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Create action for an interactive element."""
        # Implementation would be similar to existing action creation
        return {}
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action and return result."""
        # Implementation would use existing action execution
        return {} 