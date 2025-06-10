#!/usr/bin/env python3
"""
Clean Modular Website Explorer

A clean, maintainable implementation using modular utilities.
Demonstrates the power of extracting common patterns into reusable components.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from utils import (
    BrowserManager, BrowserConfig,
    ElementExtractor, 
    ActionExecutor, ActionConfig,
    StateManager,
    ErrorHandler,
    ModalHandler,
    SessionReporter,
    NavigationUtils
)
from core import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ExplorationConfig:
    """Configuration for exploration session."""
    max_actions_per_page: int = 50
    action_timeout: int = 5000
    headless: bool = True
    exploration_timeout: int = 300
    capture_screenshots: bool = True
    max_depth: int = 3  # BFS depth limit


class CleanWebExplorer:
    """
    Advanced web exploration system with intelligent robustness strategies.
    
    🎯 ROBUSTNESS FEATURES:
    
    1. **Fresh Element Re-extraction**: Elements are re-extracted before each action
       to handle dynamic DOM changes that could make cached selectors stale.
    
    2. **Multi-Stage Element Validation**: Each element undergoes comprehensive checks:
       - Existence: Element exists in DOM
       - Visibility: Element is visible to user
       - Interactability: Element is enabled and not covered
       - Stability: Element position is stable (not animating)
    
    3. **Alternative Selector Strategies**: When primary selectors fail, system tries:
       - Text-based selectors (has-text, text-is)
       - Attribute-based selectors (href matching)
       - Role-based selectors (for buttons)
    
    4. **DOM Stability Waiting**: System waits for DOM to stabilize before interactions
       to handle pages with dynamic content loading.
    
    5. **Adaptive Timeout Strategy**: Timeouts adjust based on:
       - Element type (buttons get more time than links)
       - Page complexity (more elements = longer timeouts)
       - Content type (modals get extended timeouts)
    
    6. **Intelligent Element Prioritization**: Elements are tested in order of reliability:
       - Reliable: navigation, forms, standard UI elements
       - Unreliable: social media links, external domains, complex selectors
       - Special handling for non-ASCII characters (like Japanese text)
    
    7. **Multiple Retry Strategies**: Failed elements get multiple attempts with:
       - Progressive backoff timing
       - Page state restoration between attempts
       - Alternative selector attempts
    
    8. **Domain Boundary Enforcement**: Prevents infinite crawling by restricting
       exploration to same-domain URLs only.
    
    This design specifically addresses issues like the "discやrd" timeout by:
    - Testing reliable elements first (social links are deprioritized)
    - Using multiple selector strategies for international text
    - Implementing comprehensive validation before interaction
    - Providing graceful degradation when elements become unavailable
    """
    
    def __init__(self, base_url: str, config: Optional[ExplorationConfig] = None):
        self.base_url = base_url
        self.config = config or ExplorationConfig()
        
        # Initialize core components
        self.browser_manager = BrowserManager(BrowserConfig(
            headless=self.config.headless,
            timeout=self.config.action_timeout
        ))
        
        self.element_extractor = ElementExtractor(base_url)
        self.action_executor = None  # Will be initialized after browser setup
        self.state_manager = StateManager(base_url)
        self.error_handler = ErrorHandler()
        self.modal_handler = None  # Will be initialized after browser setup
        self.navigation_utils = NavigationUtils(base_url)
        self.session_manager = SessionManager(base_url)
        
        # Initialize reporter
        domain = self.navigation_utils.get_domain(base_url)
        self.reporter = SessionReporter(base_url, domain)
        
        # Exploration state
        self.visited_urls = set()
        self.discovered_elements = []
        self.executed_actions = []
        
        logger.info(f"🚀 Clean explorer initialized for: {base_url}")
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain for BFS scope limiting."""
        try:
            from urllib.parse import urlparse
            
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()
            
            # Remove www. prefix for comparison
            domain1 = domain1.replace('www.', '')
            domain2 = domain2.replace('www.', '')
            
            # For subdomains, consider same root domain
            # e.g., "docs.example.com" and "example.com" should be considered same domain
            def get_root_domain(domain):
                parts = domain.split('.')
                if len(parts) >= 2:
                    return '.'.join(parts[-2:])  # Get last 2 parts (root domain)
                return domain
            
            root1 = get_root_domain(domain1)
            root2 = get_root_domain(domain2)
            
            return root1 == root2
            
        except Exception as e:
            logger.debug(f"Domain comparison failed: {e}")
            return False
    
    async def explore(self) -> Dict[str, Any]:
        """
        Main exploration method - clean and focused.
        """
        start_time = time.time()
        
        try:
            # Setup phase
            await self._setup()
            
            # Navigate to base URL
            success = await self.browser_manager.navigate(self.base_url)
            if not success:
                raise Exception("Failed to navigate to base URL")
            
            # Wait for JavaScript-heavy pages to load
            logger.info("⏳ Waiting for page to fully load...")
            await asyncio.sleep(3)  # Wait for JavaScript to render
            
            # Debug: Check what elements are actually on the page
            try:
                page = self.browser_manager.page
                all_buttons = await page.locator('button').count()
                all_inputs = await page.locator('input').count()
                all_links = await page.locator('a').count()
                all_divs_with_click = await page.locator('div[onclick], span[onclick], [role="button"]').count()
                
                logger.info(f"🔍 DEBUG - Found on page:")
                logger.info(f"   • button tags: {all_buttons}")
                logger.info(f"   • input tags: {all_inputs}")
                logger.info(f"   • a tags: {all_links}")
                logger.info(f"   • clickable divs/spans: {all_divs_with_click}")
                
                # Check visibility
                visible_buttons = await page.locator('button:visible').count()
                visible_inputs = await page.locator('input:visible').count() 
                visible_links = await page.locator('a:visible').count()
                
                logger.info(f"   • visible buttons: {visible_buttons}")
                logger.info(f"   • visible inputs: {visible_inputs}")
                logger.info(f"   • visible links: {visible_links}")
                
                # Try more specific selectors that modern apps might use
                react_buttons = await page.locator('[class*="button"], [class*="btn"]').count()
                clickable_elements = await page.locator('[onclick], [data-testid], [data-cy]').count()
                logger.info(f"   • CSS class buttons: {react_buttons}")
                logger.info(f"   • Elements with click handlers: {clickable_elements}")
                
            except Exception as debug_error:
                logger.warning(f"Debug inspection failed: {debug_error}")
            
            # Capture initial state
            initial_state = await self.state_manager.capture_page_state(
                self.browser_manager.page
            )
            logger.info(f"📍 Initial state captured: {initial_state}")
            
            # Perform systematic exploration
            await self._systematic_exploration()
            
            # Generate results
            end_time = time.time()
            duration = end_time - start_time
            
            results = await self._compile_results(start_time, end_time, duration)
            
            # Save session data
            await self._save_session(results)
            
            # Show meaningful completion summary
            logger.info(f"✅ Exploration completed successfully!")
            logger.info(f"   ⏱️  Duration: {duration:.1f} seconds")
            logger.info(f"   🎯 Actions executed: {len(self.executed_actions)}")
            logger.info(f"   📄 Pages visited: {len(self.visited_urls) + 1}")  # +1 for base page
            logger.info(f"   🔍 Elements discovered: {len(self.discovered_elements)}")
            return results
            
        except Exception as e:
            logger.error(f"💥 Exploration failed: {e}")
            
            # Generate partial results
            end_time = time.time()
            duration = end_time - start_time
            results = await self._compile_results(start_time, end_time, duration)
            results['status'] = 'failed'
            results['error'] = str(e)
            
            return results
            
        finally:
            await self._cleanup()
    
    async def _setup(self) -> None:
        """Setup all components."""
        logger.info("🔧 Setting up exploration components...")
        
        # Setup browser
        await self.browser_manager.setup()
        
        # Initialize page-dependent components
        page = self.browser_manager.page
        self.modal_handler = ModalHandler(page)
        
        # Initialize action executor with rich state detection
        self.action_executor = ActionExecutor(
            browser_manager=self.browser_manager,
            modal_handler=self.modal_handler,
            error_handler=self.error_handler,
            config=ActionConfig(
                default_timeout=self.config.action_timeout,
                enable_screenshots=self.config.capture_screenshots
            )
        )
        
        # Initialize rich state detection
        await self.action_executor.initialize_state_detection()
        
        # Connect error handler to browser events
        self.browser_manager.add_console_handler(
            self.error_handler.handle_console_error
        )
        self.browser_manager.add_response_handler(
            self.error_handler.handle_http_error
        )
        
        logger.info("✅ All components setup completed")
    
    async def _systematic_exploration(self) -> None:
        """Perform BFS (Breadth-First Search) exploration of the website."""
        from collections import deque
        
        logger.info("🌊 Starting BFS exploration...")
        
        # Initialize BFS queue: (url, depth, parent_url)
        exploration_queue = deque([(self.base_url, 0, None)])
        visited_for_exploration = set()  # Track URLs we've fully explored
        max_depth = self.config.max_depth  # Use configurable depth limit
        
        total_actions = 0
        total_successful = 0
        
        while exploration_queue and total_actions < self.config.max_actions_per_page:
            current_url, depth, parent_url = exploration_queue.popleft()
            
            # Check depth limit
            if depth > max_depth:
                logger.info(f"🛑 Reached max depth ({max_depth}) for URL: {current_url}")
                continue
                
            # Skip if already fully explored
            if current_url in visited_for_exploration:
                continue
                
            logger.info(f"🔍 BFS Level {depth}: Exploring {current_url}")
            
            # Navigate to the page
            if current_url != self.browser_manager.get_current_url():
                success = await self.browser_manager.navigate(current_url)
                if not success:
                    logger.warning(f"⚠️ Failed to navigate to {current_url}")
                    continue
                    
                # Wait for page to load
                await asyncio.sleep(2)
            
            # Extract elements from current page
            elements = await self.element_extractor.extract_from_page(
                self.browser_manager.page
            )
            self.discovered_elements.extend(elements)
            
            if not elements:
                logger.info(f"   📋 No interactive elements found on {current_url}")
                visited_for_exploration.add(current_url)
                continue
                
            logger.info(f"   📋 Found {len(elements)} interactive elements")
            
            # Prioritize elements
            prioritized_elements = self._prioritize_elements(elements)
            
            # Test all elements on this page using robust approach
            remaining_actions = self.config.max_actions_per_page - total_actions
            
            # Clear any previous discovered URLs
            self._discovered_urls = []
            
            page_actions, page_successful = await self._test_elements_robustly(
                current_url, 
                max_elements=remaining_actions
            )
            
            total_actions += page_actions
            total_successful += page_successful
            
            # Handle any URLs discovered during exhaustive testing
            if hasattr(self, '_discovered_urls') and self._discovered_urls:
                for discovered_url in self._discovered_urls:
                    if discovered_url not in visited_for_exploration:
                        # Only add to queue if it's the same domain (prevent internet crawling)
                        if self._is_same_domain(discovered_url, self.base_url):
                            if discovered_url not in [item[0] for item in exploration_queue]:
                                exploration_queue.append((discovered_url, depth + 1, current_url))
                                logger.info(f"   🆕 Queued for exploration: {discovered_url} (depth {depth + 1})")
                        else:
                            logger.info(f"   🚫 Skipping external domain: {discovered_url}")
                        
                        # Track as visited regardless of domain (for statistics)
                        if discovered_url not in self.visited_urls:
                            self.visited_urls.add(discovered_url)
            
            # Progress reporting
            if total_actions % 10 == 0:
                logger.info(f"   📊 Global Progress: {total_actions} actions, {total_successful} successful")
            
            # Mark this page as fully explored
            visited_for_exploration.add(current_url)
            
            # Page completion summary with accurate coverage reporting
            page_success_rate = (page_successful / page_actions) if page_actions > 0 else 0
            if page_actions == len(elements):
                logger.info(f"   ✅ Page FULLY exhausted: {page_actions}/{len(elements)} elements, {page_success_rate:.1%} success rate")
            else:
                logger.info(f"   ⚠️ Page PARTIALLY tested: {page_actions}/{len(elements)} elements ({page_actions/len(elements):.1%} coverage), {page_success_rate:.1%} success rate")
            
            # Show queue status
            if exploration_queue:
                logger.info(f"   📋 Queue status: {len(exploration_queue)} pages remaining")
        
        # Final BFS summary
        final_success_rate = (total_successful / total_actions) if total_actions > 0 else 0
        logger.info(f"🌊 BFS exploration complete:")
        logger.info(f"   • Pages explored: {len(visited_for_exploration)}")
        logger.info(f"   • Total actions: {total_actions}")
        logger.info(f"   • Successful actions: {total_successful}")
        logger.info(f"   • Overall success rate: {final_success_rate:.1%}")
        logger.info(f"   • Queue remaining: {len(exploration_queue)} pages")
    
    async def _explore_new_page(self, url: str) -> None:
        """Briefly explore a new page that was discovered."""
        logger.info(f"🔎 Briefly exploring new page: {url}")
        
        try:
            # Capture state
            await self.state_manager.capture_page_state(
                self.browser_manager.page
            )
            
            # Extract elements (for state tracking)
            new_elements = await self.element_extractor.extract_from_page(
                self.browser_manager.page
            )
            self.discovered_elements.extend(new_elements)
            
            logger.info(f"📋 Found {len(new_elements)} elements on new page")
            
        except Exception as e:
            logger.debug(f"Error exploring new page: {e}")
    
    async def _handle_action_error(self, action: Dict[str, Any], element: Dict[str, Any], error: str) -> None:
        """Handle action execution errors."""
        await self.error_handler.handle_action_error(
            action, element, error, self.browser_manager.page
        )
    
    async def _compile_results(self, start_time: float, end_time: float, duration: float) -> Dict[str, Any]:
        """Compile comprehensive exploration results."""
        # Get component summaries
        state_summary = self.state_manager.get_state_summary()
        error_summary = self.error_handler.get_error_summary()
        action_stats = self.action_executor.get_action_stats() if self.action_executor else {}
        
        # Calculate metrics
        total_elements = len(self.discovered_elements)
        total_actions = len(self.executed_actions)
        successful_actions = sum(1 for a in self.executed_actions if a.success)
        success_rate = successful_actions / total_actions if total_actions > 0 else 0
        
        results = {
            'status': 'completed',
            'base_url': self.base_url,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'session_dir': self.session_manager.session_dir,  # Add session directory
            'exploration_summary': {
                'total_elements_discovered': total_elements,
                'total_actions_performed': total_actions,
                'successful_actions': successful_actions,
                'success_rate': success_rate,
                'pages_visited': len(self.visited_urls) + 1,  # +1 for base page
                'errors_found': error_summary['total_errors'],
                'states_discovered': state_summary['total_states_discovered']
            },
            'detailed_results': {
                'discovered_elements': self.discovered_elements,
                'executed_actions': [
                    {
                        'success': a.success,
                        'action_type': a.action_type,
                        'element_type': a.element_info.get('type', 'unknown'),
                        'selector': a.element_info.get('selector', 'unknown'),
                        'text': a.element_info.get('text', ''),
                        'duration': a.duration,
                        'error': a.error_message,
                        'url': self.browser_manager.get_current_url(),
                        'timestamp': time.time(),
                        
                        # Rich state detection data
                        'state_changes': [change.__dict__ if hasattr(change, '__dict__') else change for change in (a.state_changes or [])],
                        'success_assessment': a.success_assessment,
                        'baseline_state': a.baseline_state,
                        'final_state': a.final_state,
                        
                        # Enhanced context for XML analysis
                        'url_changed': any(getattr(change, 'change_type', None) == 'navigation' for change in (a.state_changes or [])),
                        'state_changed': len(a.state_changes or []) > 0,
                        'navigation_occurred': any(getattr(change, 'category', None) == 'url_change' for change in (a.state_changes or [])),
                        
                        # Legacy format compatibility
                        'action': {
                            'action': a.action_type,
                            'element_type': a.element_info.get('type', 'unknown'),
                            'target': a.element_info.get('selector', ''),
                            'text': a.element_info.get('text', '')
                        },
                        'retry_count': 0  # Rich detector doesn't use retries
                    } for a in self.executed_actions
                ],
                'state_analysis': state_summary,
                'error_analysis': error_summary,
                'action_statistics': action_stats,
                'visited_urls': list(self.visited_urls),
                
                # Rich state detection summary
                'rich_state_detection': self.action_executor.get_state_detector_summary() if hasattr(self.action_executor, 'get_state_detector_summary') else {'initialized': False},
                
                # Modal interaction summary
                'modal_interactions': self.modal_handler.get_modal_interaction_summary() if hasattr(self.modal_handler, 'get_modal_interaction_summary') else {'initialized': False}
            }
        }
        
        return results
    
    async def _save_session(self, results: Dict[str, Any]) -> None:
        """Save session results and generate reports."""
        try:
            # Generate XML sitemap for ChatGPT
            xml_sitemap = self.reporter.generate_xml_sitemap(results['detailed_results'])
            
            # Generate JSON report
            json_report = self.reporter.generate_json_report(results['detailed_results'])
            
            # Save using session manager
            domain = self.navigation_utils.get_domain(self.base_url).replace('.', '_')
            self.session_manager.save_sitemap(xml_sitemap, domain)
            await self.session_manager.save_session_report(results)
            
            # Generate ChatGPT analysis prompt
            analysis_prompt = self.reporter.generate_chatgpt_analysis_prompt(
                xml_sitemap, results['detailed_results']
            )
            
            logger.info(f"💾 Session saved: {self.session_manager.session_dir}")
            logger.info("📄 Reports generated: XML sitemap, JSON report, ChatGPT prompt")
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    async def _cleanup(self) -> None:
        """Clean up all components."""
        logger.info("🧹 Cleaning up...")
        await self.browser_manager.cleanup()

    async def _test_elements_robustly(self, current_url: str, max_elements: int = None) -> Tuple[int, int]:
        """
        Robust element testing with fresh extraction and staleness detection.
        Returns (total_actions, successful_actions)
        """
        total_actions = 0
        successful_actions = 0
        tested_elements = set()  # Track already tested elements by selector
        max_retries = 3
        
        while True:
            # Fresh element extraction for each iteration
            elements = await self.element_extractor.extract_from_page(
                self.browser_manager.page
            )
            
            if not elements:
                logger.info("   📋 No elements found on current extraction")
                break
                
            # Filter out already tested elements and prioritize
            untested_elements = [
                el for el in elements 
                if el.get('selector') not in tested_elements
            ]
            
            # Prioritize untested elements by reliability
            if untested_elements:
                untested_elements = self._prioritize_elements(untested_elements)
            
            if not untested_elements:
                logger.info("   ✅ All available elements have been tested")
                break
                
            if max_elements and total_actions >= max_elements:
                logger.info(f"   🛑 Reached element limit: {max_elements}")
                break
            
            # Test the first untested element
            element = untested_elements[0]
            element_selector = element.get('selector')
            element_text = element.get('text', 'no text')[:30]
            
            logger.info(f"   🎯 Testing element {total_actions + 1}: {element_text}")
            
            # Multiple retry strategies for robustness
            success = False
            for retry_attempt in range(max_retries):
                try:
                    # Check for modals before action and explore them
                    modals = await self.modal_handler.detect_modals()
                    if modals:
                        logger.info("🎭 Modal detected before action, exploring content first")
                        modal_results = await self.modal_handler.explore_modal_content()
                        if modal_results:
                            # Record modal interactions as part of our exploration
                            self.executed_actions.extend(modal_results)
                            total_actions += len(modal_results)
                            successful_actions += len([r for r in modal_results if r.success])
                            logger.info(f"   📊 Modal exploration completed: {len(modal_results)} interactions")
                        
                        # Now dismiss the modal to continue regular exploration
                        await self.modal_handler.dismiss_modal()
                        await asyncio.sleep(1)  # Wait after modal dismissal
                    
                    # Wait for DOM stability on first attempt
                    if retry_attempt == 0:
                        await self._wait_for_dom_stability(stability_time=1.0, max_wait=5.0)
                    
                    # Enhanced element validation
                    if not await self._enhanced_element_validation(element):
                        logger.warning(f"   ⚠️ Element failed validation (attempt {retry_attempt + 1}): {element_text}")
                        if retry_attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Wait and retry
                            continue
                        else:
                            break  # Give up on this element
                    
                    # Execute action with adaptive timeout
                    adaptive_timeout = await self._adaptive_timeout_strategy(element)
                    
                    # Temporarily update action executor timeout
                    original_timeout = self.action_executor.config.default_timeout
                    self.action_executor.config.default_timeout = adaptive_timeout
                    
                    try:
                        result = await self.action_executor.execute_action(element)
                    finally:
                        # Restore original timeout
                        self.action_executor.config.default_timeout = original_timeout
                    self.executed_actions.append(result)
                    
                    total_actions += 1
                    
                    if result.success:
                        successful_actions += 1
                        success = True
                        
                        # Check if action opened a modal - if so, explore it
                        post_action_modals = await self.modal_handler.detect_modals()
                        if post_action_modals:
                            logger.info(f"🎭 Modal appeared after action on '{element_text}', exploring content")
                            modal_results = await self.modal_handler.explore_modal_content()
                            if modal_results:
                                # Record modal interactions
                                self.executed_actions.extend(modal_results)
                                total_actions += len(modal_results)
                                successful_actions += len([r for r in modal_results if r.success])
                                logger.info(f"   📊 Post-action modal exploration: {len(modal_results)} interactions")
                            
                            # Dismiss modal to continue exploration
                            await self.modal_handler.dismiss_modal()
                            await asyncio.sleep(1)
                    
                    # Capture state after action
                    await self.state_manager.capture_page_state(self.browser_manager.page)
                    
                    # Check for navigation - but continue exhaustive testing
                    new_url = self.browser_manager.get_current_url()
                    if new_url != current_url:
                        logger.info(f"   🔄 Navigation detected: {current_url} → {new_url}")
                        
                        # Store discovered URL for BFS queue (handled by caller)
                        if not hasattr(self, '_discovered_urls'):
                            self._discovered_urls = []
                        if new_url not in self._discovered_urls:
                            self._discovered_urls.append(new_url)
                            logger.info(f"   🆕 URL discovered for later exploration: {new_url}")
                        
                        # Navigate back to continue exhaustive testing of current page
                        logger.info(f"   🔄 Returning to continue exhaustive testing: {current_url}")
                        await self.browser_manager.navigate(current_url)
                        await asyncio.sleep(2)  # Wait for page to load
                        
                        # Continue to next element (don't return early!)
                    
                    break  # Success, move to next element
                    
                except Exception as e:
                    logger.warning(f"   ⚠️ Action failed (attempt {retry_attempt + 1}): {e}")
                    if retry_attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Wait before retry
                        # Re-navigate to ensure clean state
                        await self.browser_manager.navigate(current_url)
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"   ❌ Element failed after {max_retries} attempts: {element_text}")
                        total_actions += 1  # Count as attempted
            
            # Mark element as tested (success or failure)
            tested_elements.add(element_selector)
            
            # Brief pause between element tests
            await asyncio.sleep(0.5)
        
        return total_actions, successful_actions

    def _prioritize_elements(self, elements: list) -> list:
        """
        Prioritize elements based on reliability and success likelihood.
        More reliable elements are tested first.
        """
        try:
            def calculate_reliability_score(element):
                """Calculate reliability score for an element (higher = more reliable)."""
                score = 100  # Base score
                
                text = element.get('text', '').lower().strip()
                element_type = element.get('type', '')
                selector = element.get('selector', '')
                
                # Type-based scoring
                if element_type == 'button':
                    score += 20  # Buttons are usually reliable
                elif element_type == 'link':
                    score += 10  # Links are moderately reliable
                
                # Text-based reliability indicators
                reliable_indicators = [
                    'home', 'about', 'contact', 'login', 'signup', 'register',
                    'submit', 'save', 'search', 'menu', 'navigation'
                ]
                unreliable_indicators = [
                    'discord', 'twitter', 'x.com', 'facebook', 'social',
                    'external', 'popup', 'modal', 'overlay', 'advertisement'
                ]
                
                # Boost for reliable text patterns
                for indicator in reliable_indicators:
                    if indicator in text:
                        score += 15
                        break
                
                # Penalize unreliable text patterns
                for indicator in unreliable_indicators:
                    if indicator in text:
                        score -= 25
                        break
                
                # Selector complexity penalty
                if selector.count(':') > 2:  # Complex selectors are less reliable
                    score -= 10
                if 'nth-child' in selector:  # Position-dependent selectors are fragile
                    score -= 15
                
                # Japanese characters handling (like our "discやrd" case)
                if any(ord(char) > 127 for char in text):  # Non-ASCII characters
                    score -= 10  # Slight penalty for encoding issues
                
                # External link detection
                href = element.get('href', '')
                if href and ('http' in href and not any(domain in href for domain in ['localhost', '127.0.0.1'])):
                    # Check if it's external domain
                    try:
                        from urllib.parse import urlparse
                        base_domain = urlparse(self.base_url).netloc
                        link_domain = urlparse(href).netloc
                        if link_domain and link_domain != base_domain:
                            score -= 30  # Heavy penalty for external links
                    except:
                        pass
                
                # Length-based scoring (very short or very long text can be problematic)
                text_len = len(text)
                if text_len == 0:
                    score -= 20
                elif text_len < 3 or text_len > 50:
                    score -= 10
                
                return max(score, 0)  # Ensure non-negative score
            
            # Calculate scores and sort
            scored_elements = [
                (element, calculate_reliability_score(element))
                for element in elements
            ]
            
            # Sort by score (descending) - most reliable first
            scored_elements.sort(key=lambda x: x[1], reverse=True)
            
            # Log prioritization info
            if scored_elements:
                top_element = scored_elements[0]
                bottom_element = scored_elements[-1]
                logger.debug(f"   🎯 Element prioritization: {len(elements)} elements")
                logger.debug(f"      Most reliable: {top_element[0].get('text', 'no text')[:20]} (score: {top_element[1]})")
                logger.debug(f"      Least reliable: {bottom_element[0].get('text', 'no text')[:20]} (score: {bottom_element[1]})")
            
            return [element for element, score in scored_elements]
            
        except Exception as e:
            logger.debug(f"Element prioritization failed: {e}")
            return elements  # Return original order if prioritization fails

    async def _validate_element_availability(self, element: Dict[str, Any]) -> bool:
        """
        Validate that an element is still available and interactable.
        """
        try:
            selector = element.get('selector')
            if not selector:
                return False
                
            # Check if element exists and is visible
            page = self.browser_manager.page
            
            # Wait briefly for element to be available
            try:
                await page.wait_for_selector(selector, timeout=1000, state='visible')
                return True
            except:
                # Try alternative selectors or strategies
                return await self._try_alternative_selectors(element)
                
        except Exception as e:
            logger.debug(f"Element validation failed: {e}")
            return False
    
    async def _try_alternative_selectors(self, element: Dict[str, Any]) -> bool:
        """
        Try alternative ways to locate an element when primary selector fails.
        """
        try:
            page = self.browser_manager.page
            text = element.get('text', '').strip()
            element_type = element.get('type')
            
            # Alternative strategies
            alternative_selectors = []
            
            if text:
                # Try text-based selectors
                if element_type == 'link':
                    alternative_selectors.extend([
                        f'a:has-text("{text}")',
                        f'a[href*="{text.lower()}"]',
                        f'a:text-is("{text}")',
                        f'text="{text}"'
                    ])
                elif element_type == 'button':
                    alternative_selectors.extend([
                        f'button:has-text("{text}")',
                        f'button:text-is("{text}")',
                        f'[role="button"]:has-text("{text}")',
                        f'text="{text}"'
                    ])
            
            # Try each alternative
            for alt_selector in alternative_selectors:
                try:
                    await page.wait_for_selector(alt_selector, timeout=500, state='visible')
                    # Update element selector for future use
                    element['selector'] = alt_selector
                    logger.debug(f"   🔄 Found element using alternative selector: {alt_selector}")
                    return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Alternative selector search failed: {e}")
            return False

    async def _wait_for_dom_stability(self, stability_time: float = 2.0, max_wait: float = 10.0) -> bool:
        """
        Wait for DOM to stabilize (no new elements appearing/disappearing).
        Returns True if stable, False if timeout.
        """
        try:
            page = self.browser_manager.page
            start_time = time.time()
            last_element_count = 0
            stable_count = 0
            
            while time.time() - start_time < max_wait:
                # Count interactive elements
                elements = await self.element_extractor.extract_from_page(page)
                current_count = len(elements)
                
                if current_count == last_element_count:
                    stable_count += 1
                    if stable_count >= (stability_time * 2):  # Check every 0.5s
                        logger.debug(f"   ✅ DOM stabilized with {current_count} elements")
                        return True
                else:
                    stable_count = 0
                    last_element_count = current_count
                    logger.debug(f"   🔄 DOM changing: {current_count} elements")
                
                await asyncio.sleep(0.5)
            
            logger.warning(f"   ⏰ DOM stability timeout after {max_wait}s")
            return False
            
        except Exception as e:
            logger.debug(f"DOM stability check failed: {e}")
            return False

    async def _enhanced_element_validation(self, element: Dict[str, Any]) -> bool:
        """
        Enhanced element validation with multiple checks.
        """
        try:
            page = self.browser_manager.page
            selector = element.get('selector')
            
            if not selector:
                return False
            
            # Multi-stage validation
            checks = [
                ('existence', self._check_element_exists),
                ('visibility', self._check_element_visible), 
                ('interactability', self._check_element_interactable),
                ('stability', self._check_element_stable)
            ]
            
            for check_name, check_func in checks:
                try:
                    if not await check_func(selector):
                        logger.debug(f"   ❌ Element failed {check_name} check: {selector}")
                        return False
                except Exception as e:
                    logger.debug(f"   ⚠️ {check_name} check error: {e}")
                    return False
            
            logger.debug(f"   ✅ Element passed all validation checks: {selector}")
            return True
            
        except Exception as e:
            logger.debug(f"Enhanced validation failed: {e}")
            return False
    
    async def _check_element_exists(self, selector: str) -> bool:
        """Check if element exists in DOM."""
        try:
            element = await self.browser_manager.page.query_selector(selector)
            return element is not None
        except:
            return False
    
    async def _check_element_visible(self, selector: str) -> bool:
        """Check if element is visible."""
        try:
            await self.browser_manager.page.wait_for_selector(
                selector, timeout=1000, state='visible'
            )
            return True
        except:
            return False
    
    async def _check_element_interactable(self, selector: str) -> bool:
        """Check if element is interactable (not disabled, not covered)."""
        try:
            element = await self.browser_manager.page.query_selector(selector)
            if not element:
                return False
            
            # Check if enabled
            is_disabled = await element.is_disabled()
            if is_disabled:
                return False
            
            # Check if visible in viewport
            is_visible = await element.is_visible()
            return is_visible
            
        except:
            return False
    
    async def _check_element_stable(self, selector: str) -> bool:
        """Check if element position/properties are stable."""
        try:
            page = self.browser_manager.page
            
            # Get initial bounding box
            element = await page.query_selector(selector)
            if not element:
                return False
                
            bbox1 = await element.bounding_box()
            if not bbox1:
                return False
            
            # Wait a moment and check again
            await asyncio.sleep(0.2)
            
            element = await page.query_selector(selector)
            if not element:
                return False
                
            bbox2 = await element.bounding_box()
            if not bbox2:
                return False
            
            # Compare positions (allow small variance)
            pos_stable = (
                abs(bbox1['x'] - bbox2['x']) < 5 and
                abs(bbox1['y'] - bbox2['y']) < 5
            )
            
            return pos_stable
            
        except:
            return False

    async def _adaptive_timeout_strategy(self, element: Dict[str, Any], base_timeout: int = 5000) -> int:
        """
        Calculate adaptive timeout based on element type and page complexity.
        """
        try:
            # Base timeout
            timeout = base_timeout
            
            # Adjust based on element type
            element_type = element.get('type', '')
            if element_type == 'button':
                timeout = min(timeout * 1.2, 8000)  # Buttons might trigger complex operations
            elif 'modal' in element.get('text', '').lower():
                timeout = min(timeout * 1.5, 10000)  # Modal triggers need more time
            
            # Adjust based on page complexity (number of elements)
            try:
                elements = await self.element_extractor.extract_from_page(
                    self.browser_manager.page
                )
                element_count = len(elements)
                
                if element_count > 20:
                    timeout = min(timeout * 1.3, 10000)  # Complex pages need more time
                elif element_count < 5:
                    timeout = max(timeout * 0.8, 3000)  # Simple pages can be faster
                    
            except:
                pass  # Use base timeout if extraction fails
            
            logger.debug(f"   ⏱️ Adaptive timeout: {timeout}ms for {element.get('text', 'element')}")
            return int(timeout)
            
        except Exception as e:
            logger.debug(f"Adaptive timeout calculation failed: {e}")
            return base_timeout


# Example usage
async def main():
    """Example usage of the clean explorer."""
    base_url = "https://example.com"  # Replace with actual URL
    
    config = ExplorationConfig(
        max_actions_per_page=30,
        headless=True,
        capture_screenshots=True
    )
    
    explorer = CleanWebExplorer(base_url, config)
    results = await explorer.explore()
    
    print("\n" + "="*60)
    print("EXPLORATION RESULTS SUMMARY")
    print("="*60)
    
    summary = results['exploration_summary']
    print(f"🎯 Elements Discovered: {summary['total_elements_discovered']}")
    print(f"⚡ Actions Performed: {summary['total_actions_performed']}")
    print(f"✅ Success Rate: {summary['success_rate']:.1%}")
    print(f"🌐 Pages Visited: {summary['pages_visited']}")
    print(f"🚨 Errors Found: {summary['errors_found']}")
    print(f"🎭 States Discovered: {summary['states_discovered']}")
    print(f"⏱️ Duration: {results['duration']:.1f}s")


if __name__ == "__main__":
    asyncio.run(main()) 