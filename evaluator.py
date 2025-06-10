"""
Evaluator module for detecting broken or suspicious behavior in web applications.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import asyncio

logger = logging.getLogger(__name__)


class QAEvaluator:
    """
    Evaluates web application behavior to detect bugs, errors, and suspicious patterns.
    """
    
    def __init__(self):
        """Initialize the evaluator with detection patterns and thresholds."""
        
        # Error detection patterns
        self.error_patterns = {
            'http_errors': [
                r'404.*not found',
                r'500.*internal server error',
                r'503.*service unavailable',
                r'403.*forbidden',
                r'401.*unauthorized',
                r'502.*bad gateway',
                r'504.*gateway timeout'
            ],
            'javascript_errors': [
                r'uncaught.*error',
                r'reference.*error',
                r'type.*error',
                r'syntax.*error',
                r'network.*error',
                r'failed to fetch',
                r'cannot read property',
                r'undefined is not a function'
            ],
            'application_errors': [
                r'something went wrong',
                r'an error occurred',
                r'unexpected error',
                r'error processing',
                r'system error',
                r'database error',
                r'connection failed',
                r'server error',
                r'internal error',
                r'application error'
            ],
            'validation_errors': [
                r'required field',
                r'invalid.*format',
                r'please enter.*valid',
                r'field.*required',
                r'invalid input',
                r'validation failed',
                r'format is incorrect'
            ]
        }
        
        # Suspicious behavior indicators
        self.suspicious_indicators = {
            'unexpected_redirects': ['login', 'error', '404', 'maintenance'],
            'broken_layout': ['overlapping', 'cut off', 'missing', 'broken'],
            'performance_issues': ['timeout', 'slow', 'loading', 'delayed'],
            'accessibility_issues': ['contrast', 'keyboard', 'screen reader', 'alt text']
        }
        
        # Success indicators
        self.success_indicators = [
            'success', 'completed', 'saved', 'updated', 'created', 'submitted',
            'welcome', 'dashboard', 'profile', 'home', 'thank you'
        ]
    
    def evaluate_action_result(self, 
                                   action: Dict[str, Any],
                                   before_state: Dict[str, Any],
                                   after_state: Dict[str, Any],
                                   console_logs: List[str] = None,
                                   network_errors: List[str] = None) -> Dict[str, Any]:
        """
        Comprehensively evaluate the result of a web action.
        
        Args:
            action: The action that was performed
            before_state: Page state before the action
            after_state: Page state after the action  
            console_logs: Browser console log messages
            network_errors: Network error messages
            
        Returns:
            Dictionary containing evaluation results
        """
        evaluation = {
            'status': 'SUCCESS',
            'confidence': 1.0,
            'issues': [],
            'warnings': [],
            'successes': [],
            'severity': 'LOW',
            'summary': '',
            'details': {}
        }
        
        try:
            # Evaluate different aspects
            url_evaluation = self._evaluate_url_changes(before_state, after_state, action)
            content_evaluation = self._evaluate_content_changes(before_state, after_state, action)
            error_evaluation = self._evaluate_errors(after_state, console_logs, network_errors)
            performance_evaluation = self._evaluate_performance(before_state, after_state)
            interaction_evaluation = self._evaluate_interaction_success(action, before_state, after_state)
            
            # Combine evaluations
            all_evaluations = [
                url_evaluation,
                content_evaluation, 
                error_evaluation,
                performance_evaluation,
                interaction_evaluation
            ]
            
            # Aggregate results
            all_issues = []
            all_warnings = []
            all_successes = []
            max_severity = 'LOW'
            min_confidence = 1.0
            
            for eval_result in all_evaluations:
                all_issues.extend(eval_result.get('issues', []))
                all_warnings.extend(eval_result.get('warnings', []))
                all_successes.extend(eval_result.get('successes', []))
                
                severity = eval_result.get('severity', 'LOW')
                if self._severity_level(severity) > self._severity_level(max_severity):
                    max_severity = severity
                    
                confidence = eval_result.get('confidence', 1.0)
                min_confidence = min(min_confidence, confidence)
            
            # Determine overall status
            if all_issues:
                if any('CRITICAL' in issue or 'FATAL' in issue for issue in all_issues):
                    evaluation['status'] = 'BUG'
                elif len(all_issues) > 2 or max_severity == 'HIGH':
                    evaluation['status'] = 'BUG'
                else:
                    evaluation['status'] = 'WARNING'
            elif all_warnings:
                evaluation['status'] = 'WARNING'
            else:
                evaluation['status'] = 'SUCCESS'
            
            # Update evaluation
            evaluation.update({
                'issues': all_issues,
                'warnings': all_warnings,
                'successes': all_successes,
                'severity': max_severity,
                'confidence': min_confidence,
                'summary': self._generate_summary(evaluation['status'], all_issues, all_warnings, all_successes),
                'details': {
                    'url_changes': url_evaluation,
                    'content_changes': content_evaluation,
                    'errors': error_evaluation,
                    'performance': performance_evaluation,
                    'interaction': interaction_evaluation
                }
            })
            
            logger.info(f"Action evaluation: {evaluation['status']} - {evaluation['summary']}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            return {
                'status': 'WARNING',
                'confidence': 0.5,
                'issues': [f"Evaluation error: {str(e)}"],
                'warnings': [],
                'successes': [],
                'severity': 'MEDIUM',
                'summary': 'Could not complete evaluation',
                'details': {}
            }
    
    def _evaluate_url_changes(self, before_state: Dict, after_state: Dict, action: Dict) -> Dict[str, Any]:
        """Evaluate URL and navigation changes."""
        evaluation = {'issues': [], 'warnings': [], 'successes': [], 'severity': 'LOW', 'confidence': 1.0}
        
        url_before = before_state.get('url', '')
        url_after = after_state.get('url', '')
        
        if url_before == url_after:
            # No navigation occurred
            if action.get('action') == 'click' and 'href' in str(action.get('target', '')):
                evaluation['warnings'].append("Link click did not cause navigation")
                evaluation['confidence'] = 0.7
        else:
            # Navigation occurred
            evaluation['successes'].append(f"Navigation: {url_before} -> {url_after}")
            
            # Check for suspicious redirects
            parsed_after = urlparse(url_after)
            suspicious_paths = ['error', '404', '500', 'login', 'unauthorized']
            
            if any(path in parsed_after.path.lower() for path in suspicious_paths):
                evaluation['issues'].append(f"Suspicious redirect to: {url_after}")
                evaluation['severity'] = 'HIGH'
            
            # Check domain changes (potential security issue)
            parsed_before = urlparse(url_before)
            if parsed_before.netloc != parsed_after.netloc:
                evaluation['warnings'].append(f"Domain changed: {parsed_before.netloc} -> {parsed_after.netloc}")
        
        return evaluation
    
    def _evaluate_content_changes(self, before_state: Dict, after_state: Dict, action: Dict) -> Dict[str, Any]:
        """Evaluate content and page structure changes."""
        evaluation = {'issues': [], 'warnings': [], 'successes': [], 'severity': 'LOW', 'confidence': 1.0}
        
        title_before = before_state.get('title', '')
        title_after = after_state.get('title', '')
        
        # Title changes
        if title_before != title_after:
            evaluation['successes'].append(f"Page title changed: '{title_before}' -> '{title_after}'")
            
            # Check for error titles
            if any(error in title_after.lower() for error in ['error', '404', '500', 'not found']):
                evaluation['issues'].append(f"Error indicated in page title: {title_after}")
                evaluation['severity'] = 'HIGH'
        
        # Form-specific evaluations
        if action.get('action') in ['type', 'fill']:
            # Check if form submission was successful
            forms_before = len(before_state.get('forms', []))
            forms_after = len(after_state.get('forms', []))
            
            if forms_before > 0 and forms_after == 0:
                evaluation['successes'].append("Form disappeared after input (possible submission)")
            elif forms_before == forms_after:
                evaluation['warnings'].append("Form still present after input (no apparent change)")
        
        return evaluation
    
    def _evaluate_errors(self, after_state: Dict, console_logs: List[str] = None, network_errors: List[str] = None) -> Dict[str, Any]:
        """Evaluate error indicators in the page state and logs."""
        evaluation = {'issues': [], 'warnings': [], 'successes': [], 'severity': 'LOW', 'confidence': 1.0}
        
        # Check page content for errors
        error_indicators = after_state.get('error_indicators', [])
        if error_indicators:
            for error in error_indicators:
                evaluation['issues'].append(f"Page error: {error}")
                evaluation['severity'] = 'HIGH'
        
        # Check console logs
        if console_logs:
            for log in console_logs:
                log_lower = log.lower()
                
                # Check for JavaScript errors
                for category, patterns in self.error_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, log_lower):
                            evaluation['issues'].append(f"Console {category}: {log}")
                            evaluation['severity'] = 'MEDIUM'
                            break
        
        # Check network errors
        if network_errors:
            for error in network_errors:
                evaluation['issues'].append(f"Network error: {error}")
                evaluation['severity'] = 'HIGH'
        
        # If no errors found, that's good
        if not evaluation['issues']:
            evaluation['successes'].append("No errors detected in page or console")
        
        return evaluation
    
    def _evaluate_performance(self, before_state: Dict, after_state: Dict) -> Dict[str, Any]:
        """Evaluate performance-related issues."""
        evaluation = {'issues': [], 'warnings': [], 'successes': [], 'severity': 'LOW', 'confidence': 0.8}
        
        # This is a placeholder for performance evaluation
        # In a real implementation, you might track:
        # - Page load times
        # - Network request timings
        # - Resource loading failures
        # - Memory usage
        
        # For now, just check if the page seems to have loaded properly
        title_after = after_state.get('title', '')
        if not title_after:
            evaluation['warnings'].append("Page may not have loaded completely (no title)")
        else:
            evaluation['successes'].append("Page appears to have loaded successfully")
        
        return evaluation
    
    def _evaluate_interaction_success(self, action: Dict, before_state: Dict, after_state: Dict) -> Dict[str, Any]:
        """Evaluate whether the specific interaction was successful."""
        evaluation = {'issues': [], 'warnings': [], 'successes': [], 'severity': 'LOW', 'confidence': 1.0}
        
        action_type = action.get('action', '')
        
        if action_type == 'click':
            # For clicks, expect some kind of change
            url_changed = before_state.get('url') != after_state.get('url')
            title_changed = before_state.get('title') != after_state.get('title')
            
            # Detect modal/dialog state changes by checking for common modal indicators
            modal_appeared = self._detect_modal_state_change(before_state, after_state)
            
            # Detect other observable changes
            form_changes = self._detect_form_changes(before_state, after_state)
            content_changes = self._detect_content_changes(before_state, after_state)
            
            # Collect all observable changes
            observable_changes = []
            
            if url_changed:
                observable_changes.append("URL navigation")
            if title_changed:
                observable_changes.append("page title change")
            if modal_appeared:
                observable_changes.append("modal/dialog appearance")
            if form_changes:
                observable_changes.append("form state changes")
            if content_changes:
                observable_changes.append("page content changes")
            
            if observable_changes:
                evaluation['successes'].append(f"Click action caused observable changes: {', '.join(observable_changes)}")
            else:
                # Check if this might be a broken modal button
                if self._detect_broken_modal_button(action, before_state, after_state):
                    evaluation['issues'].append("BROKEN MODAL BUTTON: Button appears clickable but performs no action")
                    evaluation['severity'] = 'HIGH'
                    evaluation['confidence'] = 0.9
                else:
                    evaluation['warnings'].append("Click action did not cause observable changes")
                    evaluation['confidence'] = 0.6
        
        elif action_type in ['type', 'fill']:
            # For input actions, the form should still be present or we should have navigated
            forms_after = after_state.get('forms', [])
            url_changed = before_state.get('url') != after_state.get('url')
            
            if forms_after or url_changed:
                evaluation['successes'].append("Input action completed successfully")
            else:
                evaluation['warnings'].append("Form disappeared after input without navigation")
        
        elif action_type == 'select':
            # For select actions, similar to input
            evaluation['successes'].append("Select action completed")
        
        # Check for success indicators in page content
        page_content = after_state.get('title', '').lower()
        if any(indicator in page_content for indicator in self.success_indicators):
            evaluation['successes'].append("Success indicators found in page content")
        
        return evaluation
    
    def _detect_modal_state_change(self, before_state: Dict, after_state: Dict) -> bool:
        """
        Detect if a modal, dialog, or overlay appeared between before and after states.
        
        Args:
            before_state: Page state before action
            after_state: Page state after action
            
        Returns:
            True if modal state changed (appeared), False otherwise
        """
        try:
            # Check if we have explicit modal state information (preferred method)
            modal_before = before_state.get('modal_present', {})
            modal_after = after_state.get('modal_present', {})
            
            if isinstance(modal_before, dict) and isinstance(modal_after, dict):
                modal_before_present = modal_before.get('has_modal', False)
                modal_after_present = modal_after.get('has_modal', False)
                
                # Modal appeared if it wasn't there before but is there after
                if not modal_before_present and modal_after_present:
                    return True
            
            # Fallback to content-based detection if modal state info isn't available
            before_html = str(before_state.get('title', '')) + str(before_state.get('headings', []))
            after_html = str(after_state.get('title', '')) + str(after_state.get('headings', []))
            
            # Common modal indicators in content/titles
            modal_keywords = [
                'modal', 'dialog', 'popup', 'overlay', 'connect wallet', 
                'sign in', 'login', 'confirm', 'alert', 'warning'
            ]
            
            # Check if modal-related content appeared
            before_has_modal_content = any(keyword in before_html.lower() for keyword in modal_keywords)
            after_has_modal_content = any(keyword in after_html.lower() for keyword in modal_keywords)
            
            # Simple heuristic: if modal content wasn't there before but is there after
            modal_content_appeared = not before_has_modal_content and after_has_modal_content
            
            # Also check for form changes that might indicate modal with forms
            forms_before = len(before_state.get('forms', []))
            forms_after = len(after_state.get('forms', []))
            new_forms_appeared = forms_after > forms_before
            
            return modal_content_appeared or new_forms_appeared
            
        except Exception as e:
            # If we can't determine modal state, be conservative
            return False
    
    def _detect_form_changes(self, before_state: Dict, after_state: Dict) -> bool:
        """Detect changes in form state."""
        forms_before = before_state.get('forms', [])
        forms_after = after_state.get('forms', [])
        
        # Check for changes in number of forms
        if len(forms_before) != len(forms_after):
            return True
        
        # Check for changes in form structure
        for i, (form_before, form_after) in enumerate(zip(forms_before, forms_after)):
            if form_before.get('inputs', 0) != form_after.get('inputs', 0):
                return True
        
        return False
    
    def _detect_content_changes(self, before_state: Dict, after_state: Dict) -> bool:
        """Detect significant content changes."""
        # Compare headings
        headings_before = set(before_state.get('headings', []))
        headings_after = set(after_state.get('headings', []))
        
        if headings_before != headings_after:
            return True
        
        # Could add more content change detection here
        return False
    
    def _detect_broken_modal_button(self, action: Dict, before_state: Dict, after_state: Dict) -> bool:
        """
        Detect if a modal button appears broken (clickable but non-functional).
        
        Args:
            action: The action that was performed
            before_state: Page state before action
            after_state: Page state after action
            
        Returns:
            True if broken modal button is detected
        """
        # Check if this was a modal-related click action
        if action.get('action') != 'click':
            return False
        
        # Check if we're in a modal context
        modal_before = before_state.get('modal_present', {})
        modal_after = after_state.get('modal_present', {})
        
        # Modal was present before and after the action
        modal_was_open = modal_before.get('has_modal', False)
        modal_still_open = modal_after.get('has_modal', False)
        
        if not (modal_was_open and modal_still_open):
            return False  # Not a modal button issue
        
        # Check if this looks like a wallet/modal button based on action reasoning
        reasoning = action.get('reasoning', '').lower()
        modal_button_indicators = ['modal', 'wallet', 'connect', 'argent', 'braavos', 'metamask']
        
        is_modal_button = any(indicator in reasoning for indicator in modal_button_indicators)
        
        if not is_modal_button:
            return False
        
        # Check if there were any observable changes at all
        url_changed = before_state.get('url') != after_state.get('url')
        title_changed = before_state.get('title') != after_state.get('title')
        form_changes = self._detect_form_changes(before_state, after_state)
        content_changes = self._detect_content_changes(before_state, after_state)
        
        # If modal button was clicked but nothing changed, it's likely broken
        if not (url_changed or title_changed or form_changes or content_changes):
            return True
        
        return False
    
    def _severity_level(self, severity: str) -> int:
        """Convert severity string to numeric level for comparison."""
        levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
        return levels.get(severity.upper(), 1)
    
    def _generate_summary(self, status: str, issues: List[str], warnings: List[str], successes: List[str]) -> str:
        """Generate a human-readable summary of the evaluation."""
        if status == 'BUG':
            return f"Action resulted in {len(issues)} issue(s): {', '.join(issues[:2])}"
        elif status == 'WARNING':
            if issues:
                return f"Action completed with {len(issues)} issue(s) and {len(warnings)} warning(s)"
            else:
                return f"Action completed with {len(warnings)} warning(s)"
        else:
            return f"Action completed successfully with {len(successes)} positive indicator(s)"
    
    def evaluate_page_health(self, page_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the overall health of a page independent of actions.
        
        Args:
            page_info: Information about the current page
            
        Returns:
            Dictionary containing page health evaluation
        """
        evaluation = {
            'status': 'HEALTHY',
            'issues': [],
            'warnings': [],
            'recommendations': [],
            'score': 100
        }
        
        try:
            # Check for error indicators
            error_indicators = page_info.get('error_indicators', [])
            if error_indicators:
                evaluation['issues'].extend(error_indicators)
                evaluation['score'] -= len(error_indicators) * 20
                evaluation['status'] = 'UNHEALTHY'
            
            # Check page structure
            if not page_info.get('title'):
                evaluation['warnings'].append("Page has no title")
                evaluation['score'] -= 10
            
            if not page_info.get('headings'):
                evaluation['warnings'].append("Page has no headings")
                evaluation['score'] -= 5
            
            # Check for navigation
            if not page_info.get('has_nav'):
                evaluation['recommendations'].append("Consider adding navigation elements")
            
            # Check forms
            forms = page_info.get('forms', [])
            if forms:
                evaluation['recommendations'].append(f"Found {len(forms)} form(s) for testing")
            
            # Determine final status
            if evaluation['score'] < 60:
                evaluation['status'] = 'UNHEALTHY'
            elif evaluation['score'] < 80:
                evaluation['status'] = 'WARNING'
            
            logger.debug(f"Page health evaluation: {evaluation['status']} (score: {evaluation['score']})")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating page health: {e}")
            return {
                'status': 'UNKNOWN',
                'issues': [f"Evaluation error: {str(e)}"],
                'warnings': [],
                'recommendations': [],
                'score': 0
            }
    
    def should_continue_on_page(self, evaluation_history: List[Dict[str, Any]], max_consecutive_issues: int = 3) -> bool:
        """
        Determine if testing should continue on the current page based on evaluation history.
        
        Args:
            evaluation_history: List of recent evaluation results
            max_consecutive_issues: Maximum consecutive issues before stopping
            
        Returns:
            True if testing should continue, False otherwise
        """
        if not evaluation_history:
            return True
        
        # Check for consecutive issues
        consecutive_issues = 0
        for evaluation in reversed(evaluation_history[-max_consecutive_issues:]):
            if evaluation.get('status') in ['BUG', 'WARNING'] and evaluation.get('issues'):
                consecutive_issues += 1
            else:
                break
        
        if consecutive_issues >= max_consecutive_issues:
            logger.warning(f"Stopping page exploration due to {consecutive_issues} consecutive issues")
            return False
        
        return True 

 