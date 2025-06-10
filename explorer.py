"""
Core exploration module for autonomous web crawling and testing using Playwright.
"""

import asyncio
import logging
import hashlib
import traceback
import time
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
import json
import uuid
import re

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from session_manager import SessionManager

logger = logging.getLogger(__name__)


@dataclass
class WebExplorer:
    """
    Enhanced web explorer that discovers and fingerprints website states.
    """
    
    base_url: str
    max_depth: int = 3
    exploration_timeout: int = 300
    action_timeout: int = 5000
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    headless: bool = True
    state_fingerprints: Set[str] = field(default_factory=set)
    state_details: Dict[str, Dict] = field(default_factory=dict)
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    console_messages: List[Dict[str, Any]] = field(default_factory=list)
    visited_urls: Set[str] = field(default_factory=set)
    bugs_found: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    session_manager: Optional[SessionManager] = None
    start_time: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize session manager after dataclass initialization."""
        if self.session_manager is None:
            self.session_manager = SessionManager(self.base_url)
        
        self.domain = urlparse(self.base_url).netloc
        self.explored_actions = []
        self.form_data_pool = []
        self.navigation_paths = {}
    
    async def _handle_response(self, response):
        """Handle HTTP responses and capture error screenshots."""
        try:
            url = response.url
            status = response.status
            
            # Log the response
            logger.info(f"Response: {status} {url}")
            
            # Handle error status codes
            if status >= 400:
                error_type = self._get_error_type(status)
                error_details = f"HTTP_{status}"
                
                logger.warning(f"HTTP Error {status}: {url}")
                
                # Capture screenshot for errors
                if self.page and self.session_manager:
                    screenshot_path = await self.session_manager.capture_error_screenshot(
                        self.page, 
                        error_type,
                        error_details,
                        url
                    )
                    
                    # Record the error with screenshot reference
                    error_record = {
                        'type': 'http_error',
                        'status_code': status,
                        'url': url,
                        'timestamp': time.time(),
                        'screenshot': screenshot_path,
                        'error_details': error_details
                    }
                    
                    if status >= 500:
                        self.bugs_found.append(error_record)
                    else:
                        self.warnings.append(error_record)
                        
        except Exception as e:
            logger.error(f"Error handling response: {e}")
    
    def _get_error_type(self, status_code: int) -> str:
        """Map HTTP status codes to error types for screenshot naming."""
        error_map = {
            400: "400_bad_request",
            401: "401_unauthorized", 
            403: "403_forbidden",
            404: "404_not_found",
            405: "405_method_not_allowed",
            408: "408_timeout",
            429: "429_rate_limit",
            500: "500_server_error",
            502: "502_bad_gateway",
            503: "503_unavailable",
            504: "504_gateway_timeout"
        }
        
        if status_code in error_map:
            return error_map[status_code]
        elif 400 <= status_code < 500:
            return f"{status_code}_client_error"
        elif status_code >= 500:
            return f"{status_code}_server_error"
        else:
            return f"{status_code}_error"

    async def _handle_console_message(self, msg):
        """Handle console messages and capture screenshots for errors."""
        try:
            timestamp = time.time()
            message_data = {
                'type': msg.type,
                'text': msg.text,
                'url': msg.location.get('url', '') if msg.location else '',
                'line': msg.location.get('line_number', 0) if msg.location else 0,
                'timestamp': timestamp
            }
            
            self.console_messages.append(message_data)
            
            # Capture screenshots for console errors
            if msg.type in ['error', 'assert'] and self.page and self.session_manager:
                error_type = f"console_{msg.type}"
                error_details = msg.text[:100]  # Truncate for filename
                current_url = self.page.url
                
                screenshot_path = await self.session_manager.capture_error_screenshot(
                    self.page,
                    error_type,
                    error_details,
                    current_url
                )
                
                # Record console error with screenshot
                error_record = {
                    'type': 'console_error',
                    'console_type': msg.type,
                    'message': msg.text,
                    'url': current_url,
                    'source_url': message_data['url'],
                    'line': message_data['line'],
                    'timestamp': timestamp,
                    'screenshot': screenshot_path
                }
                
                if msg.type == 'error':
                    self.bugs_found.append(error_record)
                else:
                    self.warnings.append(error_record)
                    
        except Exception as e:
            logger.error(f"Error handling console message: {e}")

    async def _navigate_to_url(self, url: str, timeout: int = 10000) -> bool:
        """Navigate to URL with error handling and screenshot capture."""
        try:
            logger.info(f"🧭 Navigating to: {url}")
            
            # Set up response handler for this navigation
            self.page.on('response', self._handle_response)
            
            response = await self.page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            
            if response:
                # Check if navigation resulted in an error
                if response.status >= 400:
                    # Screenshot already captured in _handle_response
                    logger.warning(f"Navigation resulted in {response.status} error: {url}")
                    return False
            
            # Wait a bit for dynamic content to load
            await asyncio.sleep(2)
            return True
            
        except PlaywrightTimeoutError:
            logger.warning(f"Navigation timeout for: {url}")
            
            # Capture timeout screenshot
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "navigation_timeout", 
                    f"timeout_{timeout}ms",
                    url
                )
            
            timeout_error = {
                'type': 'navigation_timeout',
                'url': url,
                'timeout': timeout,
                'timestamp': time.time(),
                'screenshot': 'captured'
            }
            self.warnings.append(timeout_error)
            return False
            
        except Exception as e:
            logger.error(f"Navigation error for {url}: {e}")
            
            # Capture navigation error screenshot
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "navigation_error",
                    str(e)[:50],
                    url
                )
            
            nav_error = {
                'type': 'navigation_error',
                'url': url,
                'error': str(e),
                'timestamp': time.time(),
                'screenshot': 'captured'
            }
            self.bugs_found.append(nav_error)
            return False

    async def _execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute action with error handling and screenshot capture."""
        try:
            element_locator = action['selector']
            action_type = action['type']
            
            logger.info(f"🎯 Executing {action_type} on {element_locator}")
            
            # Wait for element to be available
            await self.page.wait_for_selector(element_locator, timeout=self.action_timeout)
            element = self.page.locator(element_locator)
            
            # Execute the action based on type
            if action_type == 'click':
                await element.click(timeout=self.action_timeout)
            elif action_type == 'type':
                text_value = action.get('value', 'test input')
                await element.fill(text_value, timeout=self.action_timeout)
            elif action_type == 'select':
                option_value = action.get('value', '0')
                await element.select_option(option_value, timeout=self.action_timeout)
            elif action_type == 'hover':
                await element.hover(timeout=self.action_timeout)
            elif action_type == 'focus':
                await element.focus(timeout=self.action_timeout)
            
            # Wait for potential state changes
            await asyncio.sleep(1)
            return True
            
        except PlaywrightTimeoutError:
            logger.warning(f"Action timeout: {action_type} on {element_locator}")
            
            # Capture action timeout screenshot
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "action_timeout",
                    f"{action_type}_{element_locator[:30]}",
                    self.page.url
                )
                
            timeout_error = {
                'type': 'action_timeout',
                'action': action,
                'url': self.page.url,
                'timestamp': time.time(),
                'screenshot': 'captured'
            }
            self.warnings.append(timeout_error)
            return False
            
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            
            # Capture action error screenshot
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "action_error", 
                    f"{action_type}_{str(e)[:30]}",
                    self.page.url
                )
            
            action_error = {
                'type': 'action_error',
                'action': action,
                'error': str(e),
                'url': self.page.url,
                'timestamp': time.time(),
                'screenshot': 'captured'
            }
            self.bugs_found.append(action_error)
            return False

    async def _setup_browser(self) -> None:
        """Initialize Playwright browser, context, and page."""
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        # Create context with proper viewport
        self.context = await self.browser.new_context(
            viewport=self.viewport_size,
            user_agent='Mozilla/5.0 (compatible; QA-Bot/1.0; Autonomous Testing Agent)'
        )
        
        # Create page and set up event listeners
        self.page = await self.context.new_page()
        
        # Set up console log capture
        self.page.on('console', self._handle_console_message)
        self.page.on('pageerror', self._handle_page_error)
        self.page.on('requestfailed', self._handle_request_failed)
        
        logger.info("Browser setup completed")
    
    async def _exploration_loop(self) -> Dict[str, Any]:
        """
        Intelligent exploration loop using dual-queue architecture for SPAs and multi-page sites.
        
        Returns:
            Dictionary containing exploration results
        """
        exploration_results = {
            'pages_visited': [],
            'actions_performed': [],
            'bugs_found': [],
            'warnings': [],
            'start_time': time.time(),
            'urls_visited': set()
        }
        
        # DUAL-QUEUE ARCHITECTURE
        # Queue 1: URL-based exploration (traditional multi-page navigation)
        pages_to_visit = [self.start_url]
        visited_page_urls = set()  # Separate tracking for page-level visits
        
        # Queue 2: State-based exploration (SPA state transitions)
        unexplored_states = set()
            
        while self._should_continue_exploration(pages_to_visit, unexplored_states):
            
                        # STRATEGY 1: URL-based exploration (for multi-page sites)
            if pages_to_visit:
                current_url = pages_to_visit.pop(0)
                
                # Skip if different domain or already explored as a PAGE (not just visited during session)
                if (not is_same_domain(current_url, self.start_url) or 
                    current_url in visited_page_urls):
                    logger.debug(f"Skipping URL: {current_url} (external or page already explored)")
                    continue
                
                # Mark as explored at PAGE level
                visited_page_urls.add(current_url)
                
                try:
                    page_result = await self._explore_single_page(current_url, exploration_results)
                    
                    # INTELLIGENT LINK DISCOVERY: Separate session-visited from unexplored pages
                    discovered_links = page_result.get('discovered_links', [])
                    truly_unvisited_pages = self._filter_unvisited_pages(discovered_links, visited_page_urls)
                    
                    # Add to URL queue only if they represent different page contexts
                    pages_to_visit.extend(truly_unvisited_pages[:3])  # Limit to prevent explosion
                    
                    # STRATEGY 2: Extract unexplored states for SPA exploration
                    current_state_unexplored = self._extract_unexplored_state_transitions()
                    unexplored_states.update(current_state_unexplored)
                
                except Exception as e:
                    logger.error(f"Error exploring page {current_url}: {e}")
                    exploration_results["warnings"].append({
                        "url": current_url,
                        "error": str(e),
                        "type": "navigation_error"
                    })
            
            # STRATEGY 2: State-based exploration (for SPA state transitions)
            elif unexplored_states:
                state_fingerprint = unexplored_states.pop()
                try:
                    await self._explore_state_transitions(state_fingerprint, exploration_results)
                except Exception as e:
                    logger.error(f"Error exploring state {state_fingerprint}: {e}")
        
        exploration_results['end_time'] = time.time()
        exploration_results['duration'] = exploration_results['end_time'] - exploration_results['start_time']
        
        return exploration_results
    
    def _should_continue_exploration(self, pages_to_visit: List[str], unexplored_states: set) -> bool:
        """
        Intelligent completion detection using multiple criteria.
        
        Args:
            pages_to_visit: URL-based exploration queue
            unexplored_states: State-based exploration queue
            
        Returns:
            True if exploration should continue, False if complete
        """
        # Safety limits
        if not self.state_store.should_continue_exploring(self.max_actions, self.max_actions_per_page):
            return False
        
        # Continue if we have work in either queue
        if pages_to_visit or unexplored_states:
            logger.debug(f"Continuing: {len(pages_to_visit)} pages, {len(unexplored_states)} states queued")
            return True
        
        # GRAPH COMPLETENESS ANALYSIS
        if hasattr(self, 'state_graph') and self.state_graph:
            # Check if we have unexplored state transitions
            for state_fingerprint in self.state_graph.states.keys():
                unexplored_transitions = self.state_graph.get_unexplored_transitions(state_fingerprint)
                if unexplored_transitions:
                    logger.debug(f"Continuing: State {state_fingerprint} has {len(unexplored_transitions)} unexplored transitions")
                    # Populate the unexplored_states queue with this state
                    unexplored_states.add(state_fingerprint)
                    return True
        
        # ELEMENT COMPLETENESS ANALYSIS WITH TRACKING VERIFICATION
        site_summary = self.state_store.get_site_exploration_summary()
        if site_summary['exploration_percentage'] < 85.0:  # Higher threshold for thorough exploration
            logger.debug(f"Low exploration percentage detected: {site_summary['exploration_percentage']:.1f}%")
            
            # CRITICAL FIX: Verify if there's actually actionable work available
            # before deciding to continue, to prevent infinite loops
            
            actionable_work_found = False
            
            # Try to find unexplored pages from known pages
            known_pages = self.state_store.get_known_pages()
            logger.debug(f"Checking {len(known_pages)} known pages for unexplored elements")
            
            for page_url in known_pages[:5]:  # Limit checking to prevent performance issues
                unexplored_elements = self.state_store.get_unexplored_elements(page_url)
                if unexplored_elements:
                    logger.debug(f"Found {len(unexplored_elements)} unexplored elements on {page_url}")
                    # Verify these are actually actionable elements
                    actionable_elements = [e for e in unexplored_elements 
                                         if e.get('type') in ['button', 'link', 'input', 'select', 'textarea']]
                    if actionable_elements:
                        logger.debug(f"Re-queuing page {page_url} with {len(actionable_elements)} actionable unexplored elements")
                        pages_to_visit.append(page_url)
                        actionable_work_found = True
                        break
            
            # Try to find unexplored state transitions
            if not actionable_work_found and hasattr(self, 'state_graph') and self.state_graph:
                logger.debug(f"Checking {len(self.state_graph.states)} states for unexplored transitions")
                for state_fingerprint in list(self.state_graph.states.keys())[:5]:  # Limit checking
                    unexplored_transitions = self.state_graph.get_unexplored_transitions(state_fingerprint)
                    if unexplored_transitions:
                        logger.debug(f"Found {len(unexplored_transitions)} unexplored transitions in state {state_fingerprint}")
                        unexplored_states.add(state_fingerprint)
                        actionable_work_found = True
                        break
            
            if actionable_work_found:
                logger.debug(f"Continuing exploration: found actionable work despite {site_summary['exploration_percentage']:.1f}% completion")
                return True
            else:
                # No actionable work found despite low percentage - this indicates a tracking issue
                logger.warning(f"🛑 TRACKING MISMATCH DETECTED: Low exploration percentage ({site_summary['exploration_percentage']:.1f}%) "
                              f"but no actionable work found. This suggests the tracking system is counting non-interactive "
                              f"elements or has stale data. Stopping exploration to prevent infinite loop.")
                logger.info(f"📊 Final stats: {site_summary['total_elements_discovered']} total elements, "
                           f"{site_summary['total_elements_explored']} explored, "
                           f"{len(known_pages)} pages discovered")
                return False
        
        logger.info(f"✅ Exploration complete: {site_summary['exploration_percentage']:.1f}% coverage, "
                   f"{len(self.state_graph.states) if hasattr(self, 'state_graph') else 0} states mapped")
        return False
    
    def _filter_unvisited_pages(self, discovered_links: List[str], visited_page_urls: set) -> List[str]:
        """
        Filter discovered links to find truly unvisited PAGE contexts (not session visits).
        
        Args:
            discovered_links: URLs found during exploration
            visited_page_urls: URLs that have been explored as distinct pages
            
        Returns:
            List of URLs representing unvisited page contexts
        """
        unvisited_pages = []
        
        for link in discovered_links:
            # Skip external domains
            if not is_same_domain(link, self.start_url):
                continue
                
            # Skip if we've already explored this as a PAGE context
            if link in visited_page_urls:
                continue
                
            # For SPAs: Check if this represents a different page context
            # (not just a different state within the same page)
            if self._represents_different_page_context(link):
                unvisited_pages.append(link)
        
        return unvisited_pages
    
    def _represents_different_page_context(self, url: str) -> bool:
        """
        Determine if a URL represents a different page context vs same-page state change.
        
        Uses heuristics to distinguish between:
        - Different pages: /login, /dashboard, /admin (different contexts)
        - Same page states: /?tab=profile, /#section2 (same context)
        
        Args:
            url: URL to analyze
            
        Returns:
            True if represents different page context
        """
        # Remove protocol and domain for analysis
        path = url.split('//')[1].split('/', 1)[1] if '//' in url else url.split('/', 1)[1] if '/' in url else ''
        base_path = path.split('?')[0].split('#')[0]  # Remove query params and fragments
        
        # Different page indicators
        different_page_indicators = [
            '/login', '/signin', '/auth',
            '/dashboard', '/admin', '/settings',
            '/profile', '/account', '/user',
            '/docs', '/help', '/support',
            '/about', '/contact', '/privacy'
        ]
        
        # Same page indicators (query params, fragments, modals)
        same_page_indicators = [
            '?', '#', 'modal', 'popup', 'overlay',
            'tab=', 'section=', 'view='
        ]
        
        # If the base path has meaningful differences, it's likely a different page
        if any(indicator in base_path.lower() for indicator in different_page_indicators):
            return True
            
        # If it's just query params or fragments, likely same page
        if any(indicator in url.lower() for indicator in same_page_indicators):
            return False
            
        # If the path depth changed significantly, likely different page
        current_depth = len([p for p in base_path.split('/') if p])
        start_depth = len([p for p in self.start_url.split('/')[3:] if p]) if '//' in self.start_url else 0
        
        return current_depth != start_depth
    
    async def _explore_single_page(self, url: str, exploration_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Explore a single page context thoroughly.
        
        Args:
            url: URL to explore
            exploration_results: Shared exploration results
            
        Returns:
            Page exploration results
        """
        logger.info(f"🌐 Exploring page context: {url}")
        
        # Navigate to page
        await self._navigate_to_url(url)
            
        # Track the initial URL
        current_page_url = self.page.url
        logger.debug(f"Initial page URL: {current_page_url}")
        
        # Wait for page to load (optimized timing)
        await self.page.wait_for_load_state('domcontentloaded')
        wait_time = self.performance_optimizer.get_minimal_wait_time('goto')
        await asyncio.sleep(wait_time)
        await asyncio.sleep(2)  # Extra wait for dynamic content
            
        # Extract page information
        html_content = await self.page.content()
        page_info = extract_page_info(html_content, url)
            
        # Extract interactive elements
        interactive_elements = extract_interactive_elements(html_content, url)
        
        # STATE-BASED EXPLORATION: Extract current UI state with interactive elements
        current_ui_state = self.state_extractor.extract_ui_state(
            self.page, url, page_info, 
            console_logs=self.console_logs,
            network_errors=self.network_errors,
            interactive_elements=interactive_elements
        )
        state_fingerprint = self.state_graph.add_state(current_ui_state)
        self.current_state_fingerprint = state_fingerprint
        
        logger.info(f"Current UI state: {current_ui_state.get_state_type()} (fingerprint: {state_fingerprint})")
        
        # Record page exploration in persistent mapping
        self.state_store.record_page_exploration(url, page_info, interactive_elements)
        
        # NOTE: Don't mark URL as visited in session state here - that's for session tracking
            
            # Evaluate page health
            page_health = self.evaluator.evaluate_page_health(page_info)
        page_result = {
            'url': url,
            'actions_performed': [],
            'bugs_found': [],
            'warnings': [],
            'discovered_links': [],
            'page_health': page_health,
            'exploration_strategy': self.state_store.get_exploration_strategy(url),
            'comparison_results': {}
        }
            
            # Collect links for future exploration
            links = [elem['href'] for elem in interactive_elements if elem['type'] == 'link']
            page_result['discovered_links'] = links
            
        # STATE-BASED EXPLORATION: Get unexplored transitions from current state
        unexplored_elements = self.state_graph.get_unexplored_transitions(self.current_state_fingerprint)
        if not unexplored_elements:
            # If no unexplored transitions from state graph, fall back to persistent store
            if self.state_store.get_exploration_strategy(url)['recommendation'] == 'incremental_exploration':
                unexplored_elements = self.state_store.get_unexplored_elements(url)
            else:
                unexplored_elements = interactive_elements
        
        # PERFORMANCE: Prioritize and optimize element exploration
        modal_present = self.performance_optimizer.detect_modal_state_efficiently(page_info)
        prioritized_elements = self.performance_optimizer.prioritize_elements(unexplored_elements)
        
        logger.info(f"High-speed exploration: testing {len(prioritized_elements)} prioritized elements "
                   f"(modal_present: {modal_present}) from state {self.current_state_fingerprint}")
        
        # Perform optimized interactions with performance tracking
        page_actions = await self._perform_optimized_interactions(prioritized_elements, page_info, modal_present)
        
            page_result['actions_performed'] = page_actions
            
        # Compare with previous exploration results if this is a known page
        if self.state_store.get_exploration_strategy(url)['is_known_page']:
            comparison_results = self._compare_with_previous_exploration(url, interactive_elements, page_actions)
            page_result['comparison_results'] = comparison_results
            
            # Log significant changes or regressions
            if comparison_results.get('significant_changes'):
                logger.warning(f"Significant changes detected on {url}: {comparison_results['changes_summary']}")
            elif comparison_results.get('potential_regressions'):
                logger.error(f"Potential regressions detected on {url}: {comparison_results['regression_summary']}")
            
            # Collect bugs and warnings from actions
            for action_result in page_actions:
                if action_result.get('evaluation', {}).get('status') == 'BUG':
                    page_result['bugs_found'].append(action_result)
                elif action_result.get('evaluation', {}).get('status') == 'WARNING':
                    page_result['warnings'].append(action_result)
            
        logger.info(f"Page exploration completed: {len(page_actions)} actions, "
                   f"{len(page_result['bugs_found'])} bugs found")
        
        # Update exploration results
        exploration_results['pages_visited'].append(page_result)
        exploration_results['urls_visited'].add(url)
        
        return page_result
    
    def _extract_unexplored_state_transitions(self) -> set:
        """
        Extract state fingerprints that have unexplored transitions for SPA exploration.
        
        Returns:
            Set of state fingerprints with unexplored transitions
        """
        unexplored_states = set()
        
        if hasattr(self, 'state_graph') and self.state_graph:
            for state_fingerprint in self.state_graph.states.keys():
                unexplored_transitions = self.state_graph.get_unexplored_transitions(state_fingerprint)
                if unexplored_transitions:
                    unexplored_states.add(state_fingerprint)
        
        return unexplored_states
    
    async def _explore_state_transitions(self, state_fingerprint: str, exploration_results: Dict[str, Any]) -> None:
        """
        Explore unexplored transitions from a specific state (for SPA exploration).
        
        Args:
            state_fingerprint: State to explore transitions from
            exploration_results: Shared exploration results
        """
        logger.info(f"🔄 Exploring state transitions from {state_fingerprint}")
        
        # Get the state data
        state_data = self.state_graph.states.get(state_fingerprint)
        if not state_data:
            logger.warning(f"State {state_fingerprint} not found in graph")
            return
        
        # Navigate to the state's URL if needed
        if hasattr(state_data, 'url') and state_data.url != self.page.url:
            await self._navigate_to_url(state_data.url)
            await asyncio.sleep(1)  # Brief wait for navigation
        
        # Get unexplored transitions
        unexplored_transitions = self.state_graph.get_unexplored_transitions(state_fingerprint)
        
        if unexplored_transitions:
            # Prioritize and execute unexplored transitions
            prioritized_elements = self.performance_optimizer.prioritize_elements(unexplored_transitions)
            
            logger.info(f"Testing {len(prioritized_elements)} unexplored transitions from state {state_fingerprint}")
            
            # Perform interactions to explore state transitions
            page_info = {'title': 'State Transition Exploration'}  # Minimal page info for state exploration
            state_actions = await self._perform_optimized_interactions(prioritized_elements, page_info, False)
            
            # Update exploration results
            exploration_results['actions_performed'].extend(state_actions)

    async def _perform_optimized_interactions(self, 
                                            prioritized_elements: List[Dict[str, Any]], 
                                            page_info: Dict[str, Any],
                                            modal_present: bool = False) -> List[Dict[str, Any]]:
        """
        PERFORMANCE OPTIMIZED: Fast interactions with intelligent batching and adaptive timeouts.
        
        Args:
            prioritized_elements: Elements sorted by priority (high-value first)
            page_info: Page information
            modal_present: Whether modal is currently blocking interactions
            
        Returns:
            List of action results with performance tracking
        """
        logger.info(f"Starting high-speed optimized interactions (modal_blocking: {modal_present})")
        action_results = []
        
        # Create execution batches for optimal throughput
        batches = self.performance_optimizer.create_execution_batches(prioritized_elements)
        
        for batch_idx, batch in enumerate(batches):
            logger.debug(f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch)} elements")
            
            for element in batch:
                # Skip elements that consistently fail
                if self.performance_optimizer.should_skip_element(element, modal_present):
                    logger.debug(f"Skipping {element.get('type')} element due to performance optimization")
                    continue
                
                # STATE-BASED CONSOLE TRACKING: Capture before state
                before_state = self.current_state_fingerprint
                before_console = self._capture_console_state_snapshot()
                
                # Create action with adaptive timeout
                action = self._create_systematic_action(element)
                if not action:
                    continue
                
                # Get adaptive timeout based on learned performance
                adaptive_timeout = self.performance_optimizer.get_adaptive_timeout(
                    action, element.get('type', ''), modal_present
                )
                
                # Execute with performance tracking
                start_time = time.time()
                action_result = await self._execute_action_with_adaptive_timeout(action, adaptive_timeout)
                duration = time.time() - start_time
                
                # STATE-BASED CONSOLE TRACKING: Detect console changes
                console_delta = self._get_console_delta(before_console)
                if console_delta['has_new_activity']:
                    action_result['console_changes'] = console_delta
                    logger.debug(f"Action triggered {len(console_delta['new_console_logs'])} console logs, "
                               f"{len(console_delta['new_network_errors'])} network errors")
                
                # STATE TRANSITION RECORDING: Extract state after action and record transition
                try:
                    html_content = await self.page.content()
                    new_page_info = extract_page_info(html_content, self.page.url)
                    
                    # Extract new UI state with console activity
                    new_ui_state = self.state_extractor.extract_ui_state(
                        self.page, self.page.url, new_page_info, 
                        self.console_logs, self.network_errors
                    )
                    after_state = self.state_graph.add_state(new_ui_state)
                    
                    # Record state transition if states changed
                    if before_state != after_state:
                        transition = StateTransition(
                            from_state=before_state,
                            to_state=after_state,
                            action=action,
                            success=action_result.get('success', False),
                            observable_changes=console_delta.get('new_console_logs', []),
                            execution_time=duration,
                            timestamp=datetime.now().isoformat()
                        )
                        self.state_graph.add_transition(transition)
                        
                        logger.info(f"State transition: {before_state} -> {after_state} via {action.get('action')}")
                    else:
                        logger.debug(f"No state change after {action.get('action')} on {element.get('type')}")
                    
                    # Update current state
                    self.current_state_fingerprint = after_state
                    
                except Exception as e:
                    logger.debug(f"State transition recording error: {e}")
                
                # Record performance for learning
                success = action_result.get('success', False)
                timed_out = 'timeout' in str(action_result.get('error', '')).lower()
                
                self.performance_optimizer.record_action_performance(
                    action, element, duration, success, timed_out
                )
                
                action_results.append(action_result)
                
                # MODAL HANDLING: Check if action opened a modal and handle it
                if success:
                    try:
                        # Check for modal after successful action
                        modal_check = await self._check_modal_presence()
                        if modal_check.get('has_modal', False):
                            logger.info(f"🔍 Modal detected after successful {action.get('action')} - attempting to handle")
                            
                            # Try to handle the modal (close it or interact with it intelligently)
                            modal_handled = await self._handle_modals_and_popups()
                            
                            if modal_handled:
                                logger.info("✅ Modal successfully handled, continuing exploration")
                            else:
                                # If we can't close the modal, try exploring it briefly
                                logger.info("🔍 Modal couldn't be closed, exploring modal content")
                                try:
                                    modal_results = await self._explore_modal_recursively()
                                    if modal_results:
                                        action_results.extend(modal_results)
                                        logger.info(f"🔍 Modal exploration completed: {len(modal_results)} actions")
                                except Exception as modal_error:
                                    logger.warning(f"Modal exploration failed: {modal_error}")
                            
                            # Verify modal is gone after handling
                            final_modal_check = await self._check_modal_presence()
                            if final_modal_check.get('has_modal', False):
                                logger.warning("⚠️ Modal still present after handling - may block future interactions")
                            else:
                                logger.info("✅ Modal successfully dismissed")
                        
                    except Exception as e:
                        logger.debug(f"Modal handling error (non-critical): {e}")
                
                # Adaptive wait based on action type and learned performance
                wait_time = self.performance_optimizer.get_minimal_wait_time(action.get('action', 'click'))
                await asyncio.sleep(wait_time)
                
                # Re-extract state only every few actions (performance optimization)
                if len(action_results) % self.performance_optimizer.batch_config['state_check_interval'] == 0:
                    try:
                        # Update modal state for next batch
                        html_content = await self.page.content()
                        new_page_info = extract_page_info(html_content, self.page.url)
                        modal_present = self.performance_optimizer.detect_modal_state_efficiently(new_page_info)
                        
                        # Store console state mapping for current state
                        if self.current_state_fingerprint:
                            self.console_states[self.current_state_fingerprint] = self._capture_console_state_snapshot()
                            
                    except Exception as e:
                        logger.debug(f"State update error (non-critical): {e}")
            
            # Minimal inter-batch delay
            if batch_idx < len(batches) - 1:
                await asyncio.sleep(self.performance_optimizer.batch_config['batch_delay'])
        
        # Log performance summary
        perf_summary = self.performance_optimizer.get_performance_summary()
        logger.info(f"Optimized interactions completed: {len(action_results)} actions, "
                   f"success_rate: {perf_summary.get('overall_success_rate', 0):.2f}, "
                   f"timeout_rate: {perf_summary.get('overall_timeout_rate', 0):.2f}")
        
        return action_results

    async def _execute_action_with_adaptive_timeout(self, action: Dict[str, Any], timeout_ms: int) -> Dict[str, Any]:
        """
        Execute action with adaptive timeout for performance optimization.
        
        Args:
            action: Action to execute
            timeout_ms: Adaptive timeout in milliseconds
            
        Returns:
            Action result with performance metadata
        """
        try:
            # Temporarily set adaptive timeout for this action
            original_timeout = getattr(self.page, 'default_timeout', 30000)
            self.page.set_default_timeout(timeout_ms)
            
            # Execute with performance monitoring
            result = await self._execute_action(action)
            result['adaptive_timeout_used'] = timeout_ms
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'action': action,
                'adaptive_timeout_used': timeout_ms,
                'performance_optimized': True
            }
        finally:
            # Restore original timeout
            self.page.set_default_timeout(original_timeout if 'original_timeout' in locals() else 30000)

    def _compare_with_previous_exploration(self, url: str, current_elements: List[Dict[str, Any]], 
                                         current_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare current exploration results with previous exploration to detect changes and regressions.
        
        Args:
            url: URL being explored
            current_elements: Currently discovered interactive elements
            current_actions: Results of current action executions
            
        Returns:
            Dictionary with comparison results and change detection
        """
        # Get previous exploration data from state store
        previous_data = self.state_store.get_page_exploration_data(url)
        
        if not previous_data:
            return {'is_first_exploration': True, 'significant_changes': False}
        
        comparison = {
            'is_first_exploration': False,
            'significant_changes': False,
            'potential_regressions': False,
            'changes_summary': [],
            'regression_summary': [],
            'new_elements': [],
            'missing_elements': [],
            'behavior_changes': []
        }
        
        # Compare element counts and types
        prev_elements = previous_data.get('all_elements', [])
        current_element_sigs = set(self.state_store._generate_element_signature(elem) for elem in current_elements)
        prev_element_sigs = set(elem.get('signature') for elem in prev_elements if elem.get('signature'))
        
        # Detect new and missing elements
        new_sigs = current_element_sigs - prev_element_sigs
        missing_sigs = prev_element_sigs - current_element_sigs
        
        if new_sigs:
            comparison['new_elements'] = [elem for elem in current_elements 
                                        if self.state_store._generate_element_signature(elem) in new_sigs]
            comparison['changes_summary'].append(f"{len(new_sigs)} new interactive elements detected")
        
        if missing_sigs:
            comparison['missing_elements'] = list(missing_sigs)
            comparison['changes_summary'].append(f"{len(missing_sigs)} previously available elements are missing")
            comparison['potential_regressions'] = True
            comparison['regression_summary'].append(f"Missing elements may indicate broken functionality")
        
        # Compare action success rates for common elements
        prev_explored = previous_data.get('explored_elements', [])
        for current_action in current_actions:
            current_sig = current_action.get('action', {}).get('target')
            if current_sig:
                # Find matching previous action
                prev_action = next((elem for elem in prev_explored 
                                  if elem.get('signature') == current_sig), None)
                
                if prev_action:
                    prev_success = prev_action.get('action_result', {}).get('success', False)
                    current_success = current_action.get('success', False)
                    
                    # Detect regression: previously working now broken
                    if prev_success and not current_success:
                        comparison['potential_regressions'] = True
                        comparison['regression_summary'].append(
                            f"Element {current_sig} was working but now fails"
                        )
                        comparison['behavior_changes'].append({
                            'element': current_sig,
                            'change': 'success_to_failure',
                            'previous_result': prev_action.get('action_result'),
                            'current_result': current_action
                        })
        
        # Mark as significant if we have substantial changes
        comparison['significant_changes'] = (
            len(comparison['changes_summary']) > 0 or 
            len(comparison['behavior_changes']) > 0
        )
        
        return comparison
    
    async def _perform_page_interactions(self, 
                                       interactive_elements: List[Dict[str, Any]], 
                                       page_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform interactions on the current page using the specified exploration mode.
        
        Args:
            interactive_elements: List of interactive elements found on the page
            page_info: Information about the current page
            
        Returns:
            List of action results
        """
        if self.exploration_mode == "discovery":
            return await self._perform_systematic_interactions(interactive_elements, page_info)
        else:
            return await self._perform_intelligent_interactions(interactive_elements, page_info)
    
    async def _perform_systematic_interactions(self, 
                                             interactive_elements: List[Dict[str, Any]], 
                                             page_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform systematic BFS/DFS exploration of all interactive elements.
        
        Args:
            interactive_elements: List of interactive elements found on the page
            page_info: Information about the current page
            
        Returns:
            List of action results
        """
        logger.info(f"Starting systematic discovery mode on {self.current_url}")
        action_results = []
        actions_on_page = 0
        
        # Check for and handle modals/popups first
        await self._handle_modals_and_popups()
        
        # Add all new elements to the queue (BFS approach)
        for element in interactive_elements:
            element_key = f"{element['type']}:{element['selector']}:{self.current_url}"
            if element_key not in self.visited_elements:
                self.element_queue.append({
                    'element': element,
                    'url': self.current_url,
                    'key': element_key
                })
        
        # Process elements systematically
        while (self.element_queue and 
               actions_on_page < self.max_actions_per_page and 
               self.state_store.should_continue_exploring(self.max_actions, self.max_actions_per_page, self.current_url)):
            
            current_item = self.element_queue.pop(0)  # BFS: first in, first out
            element = current_item['element']
            element_key = current_item['key']
            
            # Skip if already tested
            if element_key in self.visited_elements:
                continue
            
            # Check for modals before each action
            modal_handled = await self._handle_modals_and_popups()
            if modal_handled:
                # Re-extract elements as page structure may have changed
                html_content = await self.page.content()
                interactive_elements = extract_interactive_elements(html_content, self.current_url)
                # Add new elements to queue but continue with current action
            
            # Create action based on element type
            action = self._create_systematic_action(element)
            if not action:
                self.visited_elements.add(element_key)
                continue
            
            # Execute the action with retry logic for blocked elements
            try:
                logger.info(f"Systematic test: {action['action']} on {element['type']} - {element.get('text', element.get('selector', ''))[:50]}")
                action_result = await self._execute_action_with_retry(action)
                action_results.append(action_result)
                actions_on_page += 1
                
                # Check if this action opened a modal and explore it recursively
                if action_result.get('success') and self._action_opened_modal(action_result):
                    logger.info("🔍 Modal detected after action - starting recursive modal exploration")
                    modal_results = await self._explore_modal_recursively()
                    action_results.extend(modal_results)
                    actions_on_page += len(modal_results)
                
                # Record the action
                self.state_store.record_action(action, self.current_url, action_result)
                
                # Record element exploration in persistent mapping
                self.state_store.record_element_exploration(self.current_url, element, action_result)
                
            except Exception as e:
                logger.warning(f"Skipping element due to error: {e}")
                # Still mark as visited to avoid infinite retry
                action_result = {
                    'action': action,
                    'success': False,
                    'error': str(e),
                    'evaluation': {'status': 'SKIPPED', 'summary': f'Element interaction failed: {str(e)}'}
                }
                action_results.append(action_result)
                self.state_store.record_action(action, self.current_url, action_result)
            
            # Mark as visited
            self.visited_elements.add(element_key)
            
            # Brief pause between actions
            await asyncio.sleep(0.5)  # Faster for systematic testing
        
        logger.info(f"Systematic discovery completed: {actions_on_page} actions performed, {len(self.element_queue)} elements remaining")
        return action_results
    
    def _action_opened_modal(self, action_result: Dict[str, Any]) -> bool:
        """
        Check if an action resulted in opening a modal.
        
        Args:
            action_result: Result from action execution
            
        Returns:
            True if a modal was opened by this action
        """
        try:
            before_state = action_result.get('before_state', {})
            after_state = action_result.get('after_state', {})
            
            modal_before = before_state.get('modal_present', {})
            modal_after = after_state.get('modal_present', {})
            
            if isinstance(modal_before, dict) and isinstance(modal_after, dict):
                return not modal_before.get('has_modal', False) and modal_after.get('has_modal', False)
            
            return False
        except:
            return False
    
    async def _explore_modal_recursively(self) -> List[Dict[str, Any]]:
        """
        Recursively explore interactive elements within a modal.
        
        Returns:
            List of action results from modal exploration
        """
        modal_action_results = []
        max_modal_actions = 5  # Limit actions within each modal
        modal_actions_count = 0
        
        try:
            logger.info("🔍 Starting recursive modal exploration")
            
            # Wait for modal to be fully loaded
            await asyncio.sleep(1)
            
            # First, let's check what modal detection shows us
            modal_check = await self._check_modal_presence()
            logger.info(f"Modal detection status: {modal_check}")
            
            # If no modal is actually detected, exit early
            if not modal_check.get('has_modal', False):
                logger.warning("❌ No modal detected during recursive exploration - exiting")
                return modal_action_results
            
            # Extract interactive elements from the current page (which now includes modal content)
            html_content = await self.page.content()
            all_elements = extract_interactive_elements(html_content, self.current_url)
            
            logger.info(f"Total interactive elements found on page: {len(all_elements)}")
            
            # Filter to only modal-specific elements by checking if they're within modal containers
            modal_elements = await self._extract_modal_elements(all_elements)
            
            logger.info(f"Filtered modal elements: {len(modal_elements)}")
            
            # Log the first few modal elements for debugging
            for i, element in enumerate(modal_elements[:3]):
                logger.info(f"  Modal element {i+1}: {element.get('type', 'unknown')} - '{element.get('text', 'no text')[:50]}' - {element.get('selector', 'no selector')[:100]}")
            
            # Create queue for modal elements
            modal_queue = []
            for element in modal_elements:
                element_key = f"modal:{element['type']}:{element['selector']}:{self.current_url}"
                if element_key not in self.visited_elements:
                    modal_queue.append({
                        'element': element,
                        'url': self.current_url,
                        'key': element_key
                    })
            
            logger.info(f"Modal exploration queue: {len(modal_queue)} elements")
            
            # If no elements in queue, exit early
            if not modal_queue:
                logger.warning("❌ No modal elements to explore - modal might be empty or already explored")
                return modal_action_results
            
            # Process modal elements
            while (modal_queue and 
                   modal_actions_count < max_modal_actions and 
                   self.state_store.should_continue_exploring(self.max_actions, self.max_actions_per_page, self.current_url)):
                
                current_item = modal_queue.pop(0)
                element = current_item['element']
                element_key = current_item['key']
                
                # Skip if already tested
                if element_key in self.visited_elements:
                    continue
                
                # Create action for modal element
                action = self._create_modal_action(element)
                if not action:
                    logger.debug(f"No action created for modal element: {element.get('text', 'no text')[:30]}")
                    self.visited_elements.add(element_key)
                    continue
                
                try:
                    logger.info(f"🔍 Modal test: {action['action']} on {element['type']} - {element.get('text', element.get('selector', ''))[:50]}")
                    
                    # Check if modal is still present before action
                    pre_action_modal_check = await self._check_modal_presence()
                    if not pre_action_modal_check.get('has_modal', False):
                        logger.info("Modal disappeared before action - stopping modal exploration")
                        break
                    
                    action_result = await self._execute_action_with_retry(action)
                    modal_action_results.append(action_result)
                    modal_actions_count += 1
                    
                    # Mark as visited immediately
                    self.visited_elements.add(element_key)
                    
                    # Check if modal is still present after action
                    post_action_modal_check = await self._check_modal_presence()
                    if not post_action_modal_check.get('has_modal', False):
                        logger.info("Modal closed after action - stopping modal exploration")
                        break
                    
                    # Record the action
                    self.state_store.record_action(action, self.current_url, action_result)
                    
                    # Record element exploration in persistent mapping
                    self.state_store.record_element_exploration(self.current_url, element, action_result)
                    
                    # If this action closed the modal, we're done with modal exploration
                    if self._action_closed_modal(action_result):
                        logger.info("🔍 Modal was closed by action - modal exploration complete")
                        break
                    
                    # Brief pause between modal actions
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Modal element interaction failed: {e}")
                    # Mark as visited even if failed to avoid infinite retry
                    self.visited_elements.add(element_key)
                    
                    # If we can't interact with modal elements, stop trying
                    consecutive_failures = getattr(self, '_modal_failures', 0) + 1
                    self._modal_failures = consecutive_failures
                    
                    if consecutive_failures >= 3:
                        logger.warning("Too many consecutive modal interaction failures - stopping modal exploration")
                        break
                    
                    continue
            
            # Reset failure counter on successful completion
            self._modal_failures = 0
            
            logger.info(f"🔍 Modal exploration completed: tested {modal_actions_count} elements, {len(modal_action_results)} successful actions")
            
        except Exception as e:
            logger.error(f"Error in recursive modal exploration: {e}")
        
        return modal_action_results
    
    async def _extract_modal_elements(self, all_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract interactive elements from the current page when a modal is present.
        
        Args:
            all_elements: All interactive elements on the page (unused - we re-extract)
            
        Returns:
            List of interactive elements found on the current page
        """
        try:
            logger.debug("Re-extracting elements from current page with modal present")
            
            # Wait a bit for modal content to fully load
            await asyncio.sleep(1)
            
            # First, try the standard approach
            html_content = await self.page.content()
            modal_elements = extract_interactive_elements(html_content, self.current_url)
            
            # Now look for the actual modal container (not the button wrapper)
            modal_containers = [
                '[role="dialog"]',
                '.fixed',
                'div[style*="position: fixed"]',
                'div[style*="z-index"]',
                '[aria-modal="true"]',
                '.modal',
                '.overlay',
                '.popup'
            ]
            
            found_modal_elements = []
            
            for container_selector in modal_containers:
                try:
                    containers = await self.page.locator(container_selector).all()
                    for container in containers:
                        if await container.is_visible():
                            # Check if this container has wallet-related content
                            container_html = await container.inner_html()
                            if len(container_html) > 100:  # Substantial content
                                wallet_indicators = ['wallet', 'metamask', 'connect', 'coinbase', 'walletconnect', 'argent', 'braavos']
                                if any(indicator in container_html.lower() for indicator in wallet_indicators):
                                    logger.info(f"Found wallet modal container with '{container_selector}'")
                                    
                                    # Extract ALL potentially clickable elements from this container
                                    all_potential_elements = await container.locator('*').all()
                                    
                                    for potential_elem in all_potential_elements:
                                        try:
                                            if await potential_elem.is_visible():
                                                text = await potential_elem.text_content() or ""
                                                tag_name = await potential_elem.evaluate('el => el.tagName.toLowerCase()')
                                                
                                                # Look for wallet-related text or clickable indicators
                                                clickable_indicators = ['metamask', 'walletconnect', 'coinbase', 'phantom', 'connect', 'wallet', 'argent', 'braavos']
                                                
                                                is_clickable = False
                                                
                                                # Check for wallet-related text
                                                if any(indicator in text.lower() for indicator in clickable_indicators):
                                                    is_clickable = True
                                                
                                                # Check for traditional interactive elements
                                                if tag_name in ['button', 'a'] or await potential_elem.get_attribute('role') == 'button':
                                                    is_clickable = True
                                                
                                                # Check for clickable divs (common in modern wallets)
                                                if tag_name == 'div' and len(text.strip()) > 3 and len(text.strip()) < 100:
                                                    # Check if it has click behavior indicators
                                                    class_attr = await potential_elem.get_attribute('class') or ""
                                                    if any(hint in class_attr.lower() for hint in ['button', 'clickable', 'option', 'item']):
                                                        is_clickable = True
                                                
                                                if is_clickable:
                                                    # Create a more robust selector for this element
                                                    try:
                                                        # Clean text for selector (remove quotes and special chars)
                                                        clean_text = text.strip()[:20].replace('"', '').replace("'", "").replace('\\', '').replace('\n', ' ')
                                                        
                                                        # Try multiple selector strategies
                                                        selectors_to_try = []
                                                        
                                                        # Strategy 1: Use ID if available
                                                        elem_id = await potential_elem.get_attribute('id')
                                                        if elem_id:
                                                            selectors_to_try.append(f"#{elem_id}")
                                                        
                                                        # Strategy 2: Use data attributes if available
                                                        for attr in ['data-testid', 'data-id', 'aria-label']:
                                                            attr_value = await potential_elem.get_attribute(attr)
                                                            if attr_value:
                                                                selectors_to_try.append(f"[{attr}=\"{attr_value}\"]")
                                                        
                                                        # Strategy 3: Use text-based selector with cleaned text
                                                        if clean_text and len(clean_text) > 2:
                                                            selectors_to_try.append(f"{tag_name}:has-text(\"{clean_text}\")")
                                                        
                                                        # Strategy 4: Use class-based selector if available
                                                        class_attr = await potential_elem.get_attribute('class')
                                                        if class_attr and len(class_attr.split()) <= 3:  # Not too many classes
                                                            class_selector = '.' + '.'.join(class_attr.split())
                                                            selectors_to_try.append(class_selector)
                                                        
                                                        # Use the first available selector
                                                        best_selector = selectors_to_try[0] if selectors_to_try else f"{tag_name}:nth-of-type(1)"
                                                        
                                                        found_modal_elements.append({
                                                            'type': 'modal_element',
                                                            'selector': best_selector,
                                                            'text': text.strip(),
                                                            'tag': tag_name,
                                                            'href': await potential_elem.get_attribute('href') if tag_name == 'a' else None
                                                        })
                                                    except Exception as e:
                                                        logger.debug(f"Error creating selector for modal element: {e}")
                                                        continue
                                        except:
                                            continue
                                    
                                    # If we found modal elements, we're done
                                    if found_modal_elements:
                                        break
                    
                    if found_modal_elements:
                        break
                        
                except Exception as e:
                    logger.debug(f"Error checking modal container {container_selector}: {e}")
                    continue
            
            # Combine standard elements with modal-specific elements
            all_found_elements = modal_elements + found_modal_elements
            
            # Remove duplicates based on selector
            seen_selectors = set()
            unique_elements = []
            for element in all_found_elements:
                selector = element.get('selector', '')
                if selector and selector not in seen_selectors:
                    seen_selectors.add(selector)
                    unique_elements.append(element)
            
            logger.info(f"Modal element extraction: found {len(found_modal_elements)} modal-specific + {len(modal_elements)} standard = {len(unique_elements)} total unique elements")
            
            # Log the modal elements found for debugging
            for i, elem in enumerate(found_modal_elements[:5]):
                logger.info(f"  Modal element {i+1}: [{elem.get('tag', 'unknown')}] '{elem.get('text', 'no text')[:50]}' - {elem.get('selector', 'no selector')[:100]}")
            
            return unique_elements
            
        except Exception as e:
            logger.warning(f"Error extracting modal elements: {e}")
            # Fallback: return first few elements from the original list
            return all_elements[:5]
    
    def _create_modal_action(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a systematic action for a modal element with modal-specific considerations.
        
        Args:
            element: Element dictionary with type and selector information
            
        Returns:
            Action dictionary or None if no action should be performed
        """
        element_type = element.get('type')
        selector = element.get('selector')
        text = element.get('text', '').lower()
        tag = element.get('tag', '')
        
        # Handle new modal_element type (div elements found in wallet modals)
        if element_type == 'modal_element':
            if tag == 'div' and any(wallet in text for wallet in ['wallet', 'metamask', 'connect', 'coinbase', 'argent', 'braavos']):
                return {
                    'action': 'click',
                    'target': selector,
                    'reasoning': f"Modal wallet option test: {element.get('text', 'no text')[:50]}"
                }
        
        # For modal elements, we're more cautious about navigation
        if element_type == 'button':
            return {
                'action': 'click',
                'target': selector,
                'reasoning': f"Modal test of button: {element.get('text', 'no text')}"
            }
        
        elif element_type == 'link':
            # For modal links, be more selective - avoid external navigation
            href = element.get('href', '').lower()
            if any(keyword in text for keyword in ['close', 'cancel', 'dismiss', 'back']):
                return {
                    'action': 'click',
                    'target': selector,
                    'reasoning': f"Modal test of close/cancel link: {element.get('text', href)}"
                }
            elif 'javascript:' in href or '#' in href:
                return {
                    'action': 'click',
                    'target': selector,
                    'reasoning': f"Modal test of non-navigating link: {element.get('text', href)}"
                }
        
        elif element_type == 'input':
            input_type = element.get('input_type', 'text')
            if input_type in ['text', 'email', 'search', 'tel', 'url']:
                test_value = self._get_test_value_for_input_type(input_type)
                return {
                    'action': 'fill',
                    'target': selector,
                    'value': test_value,
                    'reasoning': f"Modal test of {input_type} input"
                }
        
        elif element_type == 'select':
            options = element.get('options', [])
            if options and len(options) > 1:
                test_value = options[1].get('value', options[1].get('text', ''))
                return {
                    'action': 'select',
                    'target': selector,
                    'value': test_value,
                    'reasoning': f"Modal test of select dropdown"
                }
        
        # Skip elements that don't have safe modal actions
        return None
    
    def _action_closed_modal(self, action_result: Dict[str, Any]) -> bool:
        """
        Check if an action resulted in closing a modal.
        
        Args:
            action_result: Result from action execution
            
        Returns:
            True if the modal was closed by this action
        """
        try:
            before_state = action_result.get('before_state', {})
            after_state = action_result.get('after_state', {})
            
            modal_before = before_state.get('modal_present', {})
            modal_after = after_state.get('modal_present', {})
            
            if isinstance(modal_before, dict) and isinstance(modal_after, dict):
                return modal_before.get('has_modal', False) and not modal_after.get('has_modal', False)
            
            return False
        except:
            return False
    
    async def _cleanup_browser(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")

    def _handle_console_message(self, msg) -> None:
        """Handle browser console messages."""
        if msg.type in ['error', 'warning']:
            self.console_logs.append(f"[{msg.type}] {msg.text}")
            logger.debug(f"Console {msg.type}: {msg.text}")

    def _handle_page_error(self, error) -> None:
        """Handle page errors."""
        error_msg = str(error)
        self.console_logs.append(f"[page_error] {error_msg}")
        logger.warning(f"Page error: {error_msg}")

    def _handle_request_failed(self, request) -> None:
        """Handle failed network requests with categorization."""
        url = str(request.url)
        failure = str(request.failure)
        
        # Categorize the failed request
        category, log_level, context = self._categorize_failed_request(url, failure)
        
        # Create contextual error message
        error_msg = f"[{category}] Request failed: {url} - {failure}"
        if context:
            error_msg += f" ({context})"
        
        self.network_errors.append({
            'url': url,
            'failure': failure,
            'category': category,
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        
        # Log at appropriate level
        if log_level == 'DEBUG':
            logger.debug(error_msg)
        elif log_level == 'INFO':
            logger.info(error_msg)
                else:
            logger.warning(error_msg)
        
    def _categorize_failed_request(self, url: str, failure: str) -> tuple[str, str, str]:
        """
        Categorize failed requests for better logging context.
            
        Returns:
            tuple: (category, log_level, context_message)
        """
        url_lower = url.lower()
        
        # Google Analytics & Tracking
        if 'google-analytics.com' in url_lower or 'googletagmanager.com' in url_lower:
            return ('ANALYTICS', 'DEBUG', 'Expected in headless mode - analytics tracking blocked')
        
        # Other tracking services
        if any(tracker in url_lower for tracker in ['mixpanel', 'segment', 'amplitude', 'hotjar', 'facebook.com/tr']):
            return ('TRACKING', 'DEBUG', 'Expected in headless mode - tracking service blocked')
        
        # Static assets (JS/CSS/Images/Fonts)
        if url_lower.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf')):
            if '_next/static/' in url_lower:
                return ('NEXTJS_ASSET', 'INFO', 'Next.js static asset failed - may affect site functionality')
            else:
                return ('STATIC_ASSET', 'INFO', 'Static asset failed - may affect visual appearance')
        
        # Audio/Video files
        if url_lower.endswith(('.wav', '.mp3', '.mp4', '.webm', '.ogg')):
            return ('MEDIA', 'INFO', 'Media file failed - affects audio/visual experience')
        
        # API endpoints
        if any(api_indicator in url_lower for api_indicator in ['/api/', '/_rsc=', '.json', '/graphql']):
            return ('API', 'WARNING', 'API endpoint failed - may indicate functional issues')
        
        # CDN or external resources
        if any(cdn in url_lower for cdn in ['cdn.', 'assets.', 'static.']):
            return ('CDN', 'INFO', 'CDN resource failed - may affect performance')
        
        # Network errors that might indicate connectivity issues
        if 'net::err_connection' in failure.lower() or 'net::err_timeout' in failure.lower():
            return ('NETWORK', 'WARNING', 'Network connectivity issue detected')
        
        # Aborted requests (common in automation)
        if 'net::err_aborted' in failure.lower():
            return ('ABORTED', 'DEBUG', 'Expected in automated testing - request cancelled by browser')
        
        # Protocol errors
        if 'quic_protocol_error' in failure.lower():
            return ('PROTOCOL', 'INFO', 'HTTP/3 QUIC protocol issue - site may have connectivity problems')
        
        # Default category for unclassified failures
        return ('UNKNOWN', 'WARNING', 'Unclassified request failure')

    async def _navigate_to_url(self, url: str) -> None:
        """Navigate to a specific URL and handle any errors."""
        try:
            response = await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            if response and response.status >= 400:
                logger.warning(f"HTTP {response.status} when navigating to {url}")
            
            self.current_url = self.page.url
            logger.debug(f"Navigated to: {self.current_url}")
            
        except Exception as e:
            logger.error(f"Navigation to {url} failed: {e}")
            raise
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific action using Playwright.
        
        Args:
            action: Action dictionary from GPT agent
            
        Returns:
            Dictionary containing action execution results
        """
        action_result = {
            'action': action,
            'success': False,
            'error': None,
            'evaluation': {},
            'before_state': {},
            'after_state': {}
        }
        
        try:
            # Capture before state
            before_html = await self.page.content()
            action_result['before_state'] = extract_page_info(before_html, self.current_url)
            
            # Capture modal state before action
            modal_before = await self._check_modal_presence()
            action_result['before_state']['modal_present'] = modal_before
            
            # Clear previous console logs
            self.console_logs.clear()
            self.network_errors.clear()
            
            # Execute the action
            await self._perform_playwright_action(action)
            
            # Wait for any changes to take effect
            await asyncio.sleep(2)
            
            # Capture after state
            after_html = await self.page.content()
            self.current_url = self.page.url
            action_result['after_state'] = extract_page_info(after_html, self.current_url)
            
            # Capture modal state after action
            modal_after = await self._check_modal_presence()
            action_result['after_state']['modal_present'] = modal_after
            
            action_result['success'] = True
            
            # Evaluate the result
            evaluation = self.evaluator.evaluate_action_result(
                action,
                action_result['before_state'],
                action_result['after_state'],
                self.console_logs.copy()
            )
            action_result['evaluation'] = evaluation
            
            logger.info(f"Action executed: {action.get('action')} on {action.get('target')} - Result: {evaluation.get('status')}")
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            action_result['error'] = str(e)
            action_result['evaluation'] = {
                'status': 'ERROR',
                'summary': f"Action execution failed: {str(e)}"
            }
        
        return action_result
    
    async def _perform_playwright_action(self, action: Dict[str, Any]) -> None:
        """
        Perform the actual Playwright action.
        
        Args:
            action: Action dictionary containing type, target, and value
        """
        action_type = action.get('action')
        target = action.get('target')
        value = action.get('value', '')
        
        if action_type == 'navigate':
            # For navigation, target is the URL to navigate to
            await self.page.goto(target)
            return
        
        # For all other actions, locate the element first
        element = self.page.locator(target)
        
        # Wait for element to be available
        await element.wait_for(timeout=10000)
        
        if action_type == 'click':
            await element.click()
        
        elif action_type == 'type':
            await element.fill('')  # Clear first
            await element.type(value)
        
        elif action_type == 'fill':
            await element.fill(value)
        
        elif action_type == 'select':
            await element.select_option(value)
        
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    async def _check_modal_presence(self) -> Dict[str, Any]:
        """
        Check for the presence of modals, dialogs, or overlays on the current page.
        
        Returns:
            Dictionary with modal detection information
        """
        modal_info = {
            'has_modal': False,
            'modal_types': [],
            'modal_selectors_found': []
        }
        
        try:
            # Common modal overlay selectors
            modal_selectors = [
                ('[data-state="open"]', 'react-modal'),
                ('.fixed.inset-0', 'fixed-overlay'), 
                ('[role="dialog"]', 'aria-dialog'),
                ('[aria-modal="true"]', 'aria-modal'),
                ('.modal', 'generic-modal'),
                ('.popup', 'popup'),
                ('.overlay', 'overlay'),
                ('div[style*="position: fixed"]', 'inline-fixed'),
                ('div[style*="z-index"]', 'high-z-index')
            ]
            
            for selector, modal_type in modal_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            modal_info['has_modal'] = True
                            modal_info['modal_types'].append(modal_type)
                            modal_info['modal_selectors_found'].append(selector)
                            break
                except:
                    continue
            
            # Additional check for elements that might be modal content
            if not modal_info['has_modal']:
                # Check for elements with modal-like text content
                modal_text_selectors = [
                    ':has-text("Connect")',
                    ':has-text("Sign In")', 
                    ':has-text("Login")',
                    ':has-text("Confirm")',
                    ':has-text("Close")',
                    ':has-text("Cancel")'
                ]
                
                for text_selector in modal_text_selectors:
                    try:
                        elements = await self.page.locator(text_selector).all()
                        for element in elements:
                            if await element.is_visible():
                                # Check if this element is in a modal-like container
                                parent = element.locator('xpath=..')
                                parent_class = await parent.get_attribute('class') or ''
                                parent_style = await parent.get_attribute('style') or ''
                                
                                if any(indicator in parent_class.lower() for indicator in ['modal', 'dialog', 'popup', 'overlay']):
                                    modal_info['has_modal'] = True
                                    modal_info['modal_types'].append('text-based-modal')
                                    modal_info['modal_selectors_found'].append(text_selector)
                                    break
                                
                                if 'position: fixed' in parent_style or 'z-index' in parent_style:
                                    modal_info['has_modal'] = True
                                    modal_info['modal_types'].append('styled-modal')
                                    modal_info['modal_selectors_found'].append(text_selector)
                                    break
                    except:
                        continue
            
        except Exception as e:
            logger.debug(f"Error checking modal presence: {e}")
        
        return modal_info

    def _create_systematic_action(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a systematic action for an element based on its type.
        
        Args:
            element: Element dictionary with type and selector information
            
        Returns:
            Action dictionary or None if no action should be performed
        """
        element_type = element.get('type')
        selector = element.get('selector')
        
        if element_type == 'button':
            return {
                'action': 'click',
                'target': selector,
                'reasoning': f"Systematic test of button: {element.get('text', 'no text')}"
            }
        
        elif element_type == 'link':
            href = element.get('href', '')
            # Only click internal links in discovery mode
            if href and is_same_domain(href, self.start_url):
                return {
                    'action': 'click', 
                    'target': selector,
                    'reasoning': f"Systematic test of internal link: {element.get('text', href)}"
                }
        
        elif element_type == 'input':
            input_type = element.get('input_type', 'text')
            if input_type in ['text', 'email', 'search', 'tel', 'url']:
                # Use simple test values for systematic testing
                test_value = self._get_test_value_for_input_type(input_type)
                return {
                    'action': 'fill',
                    'target': selector,
                    'value': test_value,
                    'reasoning': f"Systematic test of {input_type} input"
                }
        
        elif element_type == 'select':
            options = element.get('options', [])
            if options and len(options) > 1:
                # Pick the second option (avoid default)
                test_value = options[1].get('value', options[1].get('text', ''))
                return {
                    'action': 'select',
                    'target': selector,
                    'value': test_value,
                    'reasoning': f"Systematic test of select dropdown"
                }
        
        # Skip elements that don't have systematic actions
        return None

    def _get_test_value_for_input_type(self, input_type: str) -> str:
        """Get appropriate test values for different input types."""
        test_values = {
            'text': 'Test Input',
            'email': 'test@example.com',
            'search': 'search test',
            'tel': '555-1234',
            'url': 'https://example.com',
            'password': 'TestPass123'
        }
        return test_values.get(input_type, 'test')

    def _capture_console_state_snapshot(self) -> Dict[str, Any]:
        """
        Capture current console state for state-based tracking.
        
        Returns:
            Dictionary containing current console logs and network errors
        """
        return {
            'console_logs': self.console_logs.copy(),
            'network_errors': self.network_errors.copy(),
            'timestamp': datetime.now().isoformat()
        }

    def _get_console_delta(self, before_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get console changes that occurred between snapshots.
        
        Args:
            before_snapshot: Console state before action
            
        Returns:
            Dictionary containing new console logs and errors
        """
        before_console_count = len(before_snapshot.get('console_logs', []))
        before_network_count = len(before_snapshot.get('network_errors', []))
        
        new_console_logs = self.console_logs[before_console_count:]
        new_network_errors = self.network_errors[before_network_count:]
        
        return {
            'new_console_logs': new_console_logs,
            'new_network_errors': new_network_errors,
            'has_new_activity': bool(new_console_logs or new_network_errors)
        }

    async def _handle_modals_and_popups(self) -> bool:
        """
        Detect and handle modal dialogs, popups, and overlays.
        
        Returns:
            True if a modal was handled, False otherwise
        """
        try:
            # Common modal overlay selectors
            modal_selectors = [
                '[data-state="open"]',  # Common React modal pattern
                '.fixed.inset-0',       # Fixed overlay pattern
                '[role="dialog"]',      # ARIA dialog role
                '[aria-modal="true"]',  # ARIA modal
                '.modal',               # Generic modal class
                '.popup',               # Generic popup class
                '.overlay'              # Generic overlay class
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    modal = self.page.locator(selector).first
                    if await modal.is_visible():
                        logger.info(f"Modal detected with selector: {selector}")
                        
                        # Try to find and click close button
                        close_buttons = [
                            'button:has-text("Close")',
                            'button:has-text("✕")',
                            'button:has-text("×")',
                            '[aria-label="Close"]',
                            '[data-dismiss="modal"]',
                            '.close-button',
                            'button.close'
                        ]
                        
                        button_closed = False
                        for close_selector in close_buttons:
                            try:
                                close_btn = modal.locator(close_selector).first
                                if await close_btn.is_visible():
                                    await close_btn.click()
                                    await asyncio.sleep(1)  # Wait for modal to close
                                    logger.info(f"Closed modal using close button: {close_selector}")
                                    button_closed = True
                                    modal_found = True
                                    break
                            except:
                                continue
                        
                        # If no close button found, try pressing Escape
                        if not button_closed:
                            try:
                                await self.page.keyboard.press('Escape')
                                await asyncio.sleep(1)
                                logger.info("Closed modal using Escape key")
                                modal_found = True
                            except:
                                pass
                        
                        break  # Only handle one modal at a time
                        
                except:
                    continue
            
            return modal_found
            
        except Exception as e:
            logger.debug(f"Error handling modals: {e}")
            return False
    
    def _calculate_session_duration(self) -> float:
        """Calculate session duration in seconds."""
        if hasattr(self, 'exploration_start_time'):
            return time.time() - self.exploration_start_time
        return 0.0
    
    def _generate_final_report(self, exploration_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the final exploration report.
        
        Args:
            exploration_results: Results from the exploration loop
            
        Returns:
            Complete exploration report
        """
        # Get site exploration summary
        site_summary = self.state_store.get_site_exploration_summary()
        
        # Calculate totals
        total_pages = len(exploration_results.get('pages_visited', []))
        total_actions = sum(
            len(page.get('actions_performed', [])) 
            for page in exploration_results.get('pages_visited', [])
        )
        total_bugs = sum(
            len(page.get('bugs_found', [])) 
            for page in exploration_results.get('pages_visited', [])
        )
        total_warnings = sum(
            len(page.get('warnings', [])) 
            for page in exploration_results.get('pages_visited', [])
        )
        
        # Generate summary with accurate URL tracking
        # Track unique URLs from state graph (more accurate than pages_visited count)
        unique_urls = set()
        if hasattr(self, 'state_graph') and self.state_graph:
            for state_data in self.state_graph.states.values():
                # Handle UIState object properly
                if hasattr(state_data, 'url'):
                    unique_urls.add(state_data.url)
                elif isinstance(state_data, dict) and 'url' in state_data:
                    unique_urls.add(state_data['url'])
        
        exploration_summary = {
            'total_pages_visited': len(unique_urls) if unique_urls else total_pages,  # URLs visited during exploration
            'total_actions_performed': total_actions,
            'bugs_found': total_bugs,
            'warnings': total_warnings,
            'exploration_mode': self.exploration_mode,
            'session_duration': self._calculate_session_duration(),
            'persistent_mapping': site_summary,
            'state_statistics': {
                'total_states_discovered': len(self.state_graph.states) if hasattr(self, 'state_graph') and self.state_graph else 0,
                'total_state_transitions': len(self.state_graph.transitions) if hasattr(self, 'state_graph') and self.state_graph else 0,
                'unique_state_fingerprints': len(set(self.state_graph.states.keys())) if hasattr(self, 'state_graph') and self.state_graph else 0,
                'unique_urls_visited': list(unique_urls) if unique_urls else []
            }
        }
        
        # Create final report
        final_report = {
            'exploration_summary': exploration_summary,
            'pages_explored': exploration_results.get('pages_visited', []),
            'state_store_stats': self.state_store.get_stats(),
            'timestamp': datetime.now().isoformat()
        }
        
        return final_report
    
    async def _perform_intelligent_interactions(self, 
                                              interactive_elements: List[Dict[str, Any]], 
                                              page_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform AI-guided interactions on the current page (original logic).
        
        Args:
            interactive_elements: List of interactive elements found on the page
            page_info: Information about the current page
            
        Returns:
            List of action results
        """
        action_results = []
        actions_on_page = 0
        
        while (actions_on_page < self.max_actions_per_page and 
               self.state_store.should_continue_exploring(self.max_actions, self.max_actions_per_page, self.current_url)):
            
            # Get action history for context
            previous_actions = self.state_store.get_action_history(self.current_url, limit=5)
            
            # Ask GPT-4 what to do next
            chosen_action = self.gpt_agent.choose_action(
                interactive_elements, 
                page_info, 
                previous_actions
            )
            
            # Check if we should stop
            if chosen_action.get('action') == 'wait':
                logger.info(f"GPT suggested to wait: {chosen_action.get('reasoning', '')}")
                break
            
            # Check if action has been performed before
            if self.state_store.has_performed_action(chosen_action, self.current_url):
                logger.debug("Action already performed, choosing different action")
                continue
            
            # Perform the action
            action_result = await self._execute_action(chosen_action)
            action_results.append(action_result)
            actions_on_page += 1
            
            # Record the action
            self.state_store.record_action(chosen_action, self.current_url, action_result)
            
            # Brief pause between actions
            await asyncio.sleep(1)
        
        return action_results

    async def _execute_action_with_retry(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute action with retry logic for common issues like blocked elements.
        
        Args:
            action: Action dictionary
            
        Returns:
            Action result dictionary
        """
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return await self._execute_action(action)
            
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle specific common errors
                if "strict mode violation" in error_msg and "resolved to" in error_msg:
                    # Multiple elements found - modify selector to be more specific
                    original_selector = action.get('target', '')
                    if ':has-text(' in original_selector:
                        # Make the selector more specific by adding .first
                        action['target'] = f"({original_selector}).first"
                        logger.info(f"Retry {attempt + 1}: Using more specific selector: {action['target']}")
                        continue
            
                elif "intercepts pointer events" in error_msg:
                    # Element is blocked by modal/overlay
                    logger.info(f"Retry {attempt + 1}: Element blocked, trying to handle modals")
                    await self._handle_modals_and_popups()
                    await asyncio.sleep(1)
                    continue
                
                elif attempt < max_retries - 1:
                    logger.info(f"Retry {attempt + 1}: General error, waiting and retrying: {e}")
                    await asyncio.sleep(2)
                    continue
                else:
                    # Final attempt failed
                    raise e
        
        # This shouldn't be reached, but just in case
        raise Exception("Max retries exceeded")

    async def explore(self) -> Dict[str, Any]:
        """Main exploration method with enhanced session management."""
        logger.info(f"🚀 Starting website exploration of {self.base_url}")
        start_time = time.time()
        
        try:
            await self._setup_browser()
            await self._navigate_to_url(self.base_url)
            
            # Main exploration logic
            await self._systematic_exploration()
            
            # Clean up
            await self._cleanup_browser()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Generate comprehensive results
            results = self._generate_comprehensive_results(start_time, end_time, duration)
            
            # Save results using session manager
            domain = urlparse(self.base_url).netloc.replace(':', '_').replace('.', '_')
            xml_content = self._generate_xml_sitemap(domain)
            
            # Save sitemap and session report
            self.session_manager.save_sitemap(xml_content, domain)
            report_path = self.session_manager.save_session_report(results)
            
            logger.info(f"✅ Exploration completed in {duration:.1f}s")
            logger.info(f"📁 Session saved: {self.session_manager.session_dir}")
            
            return results
            
        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            logger.error(traceback.format_exc())
            
            # Capture exploration failure screenshot
            if self.page and self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "exploration_failure",
                    str(e)[:50],
                    self.page.url if self.page else self.base_url
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Generate results even for failed exploration
            results = self._generate_comprehensive_results(start_time, end_time, duration)
            results['exploration_status'] = 'failed'
            results['error'] = str(e)
            
            # Save partial results
            try:
                domain = urlparse(self.base_url).netloc.replace(':', '_').replace('.', '_')
                xml_content = self._generate_xml_sitemap(domain)
                self.session_manager.save_sitemap(xml_content, domain)
                self.session_manager.save_session_report(results)
            except:
                pass
                
            return results
        
        finally:
            if self.browser:
                await self._cleanup_browser()

    def _generate_comprehensive_results(self, start_time: float, end_time: float, duration: float) -> Dict[str, Any]:
        """Generate comprehensive exploration results."""
        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'exploration_status': 'completed',
            'base_url': self.base_url,
            'domain': self.domain,
            'exploration_summary': {
                'total_pages_visited': len(self.visited_urls),
                'total_actions_performed': len(self.explored_actions),
                'bugs_found': len(self.bugs_found),
                'warnings': len(self.warnings),
                'console_messages': len(self.console_messages),
                'state_statistics': {
                    'total_states_discovered': len(self.state_fingerprints),
                    'total_state_transitions': len(self.state_transitions),
                    'unique_state_fingerprints': len(self.state_fingerprints)
                }
            },
            'state_fingerprints': list(self.state_fingerprints),
            'state_details': self.state_details,
            'state_transitions': self.state_transitions,
            'bugs_found': self.bugs_found,
            'warnings': self.warnings,
            'console_messages': self.console_messages,
            'visited_urls': list(self.visited_urls),
            'session_info': self.session_manager.get_session_info() if self.session_manager else {}
        }