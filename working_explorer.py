#!/usr/bin/env python3
"""
Working Web Explorer with Session Management and Error Screenshots
Comprehensive UI exploration for state fingerprinting
"""

import asyncio
import logging
import hashlib
import time
import json
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from session_manager import SessionManager

logger = logging.getLogger(__name__)

@dataclass
class WorkingWebExplorer:
    """
    Comprehensive web explorer with session management and error capture.
    """
    
    base_url: str
    max_depth: int = 3
    exploration_timeout: int = 300
    action_timeout: int = 5000
    headless: bool = True
    
    # Session management
    session_manager: Optional[SessionManager] = None
    
    # Exploration state
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    
    # Discovery tracking
    visited_urls: Set[str] = field(default_factory=set)
    discovered_elements: List[Dict[str, Any]] = field(default_factory=list)
    state_fingerprints: Set[str] = field(default_factory=set)
    state_details: Dict[str, Dict] = field(default_factory=dict)
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Error tracking
    console_messages: List[Dict[str, Any]] = field(default_factory=list)
    bugs_found: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize session manager."""
        if self.session_manager is None:
            self.session_manager = SessionManager(self.base_url)
        
        self.domain = urlparse(self.base_url).netloc
        self.explored_actions = []
        
    async def _setup_browser(self) -> None:
        """Initialize Playwright browser."""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (compatible; QA-Bot/1.0; Autonomous Testing Agent)'
        )
        
        self.page = await self.context.new_page()
        
        # Set up event handlers
        self.page.on('console', self._handle_console_message)
        self.page.on('response', self._handle_response)
        
        logger.info("Browser setup completed")

    async def _cleanup_browser(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    async def _handle_response(self, response):
        """Handle HTTP responses and capture error screenshots."""
        try:
            url = response.url
            status = response.status
            
            logger.info(f"Response: {status} {url}")
            
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
        """Map HTTP status codes to error types."""
        error_map = {
            400: "400_bad_request", 401: "401_unauthorized", 403: "403_forbidden",
            404: "404_not_found", 405: "405_method_not_allowed", 408: "408_timeout",
            429: "429_rate_limit", 500: "500_server_error", 502: "502_bad_gateway",
            503: "503_unavailable", 504: "504_gateway_timeout"
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
                error_details = msg.text[:100]
                current_url = self.page.url
                
                screenshot_path = await self.session_manager.capture_error_screenshot(
                    self.page,
                    error_type,
                    error_details,
                    current_url
                )
                
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
        """Navigate to URL with error handling."""
        try:
            logger.info(f"🧭 Navigating to: {url}")
            
            response = await self.page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            
            if response and response.status >= 400:
                logger.warning(f"Navigation resulted in {response.status} error: {url}")
                return False
            
            # Wait for dynamic content
            await asyncio.sleep(2)
            return True
            
        except PlaywrightTimeoutError:
            logger.warning(f"Navigation timeout for: {url}")
            
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "navigation_timeout", 
                    f"timeout_{timeout}ms",
                    url
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Navigation error for {url}: {e}")
            
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "navigation_error",
                    str(e)[:50],
                    url
                )
            
            return False

    async def _extract_interactive_elements(self) -> List[Dict[str, Any]]:
        """Extract all interactive elements from the current page."""
        elements = []
        
        try:
            # Get page content for fingerprinting
            content = await self.page.content()
            url = self.page.url
            
            # Create state fingerprint
            state_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            self.state_fingerprints.add(state_hash)
            
            # Extract buttons
            buttons = await self.page.locator('button, input[type="button"], input[type="submit"], [role="button"]').all()
            for i, button in enumerate(buttons):
                try:
                    if await button.is_visible():
                        text = await button.inner_text() or await button.get_attribute('value') or f"button_{i}"
                        selector = f'button:has-text("{text[:50]}")' if text else f'button >> nth={i}'
                        
                        elements.append({
                            'type': 'button',
                            'text': text.strip()[:100],
                            'selector': selector,
                            'index': i,
                            'url': url,
                            'state_hash': state_hash
                        })
                except Exception as e:
                    logger.debug(f"Error extracting button {i}: {e}")
            
            # Extract links
            links = await self.page.locator('a[href]').all()
            for i, link in enumerate(links):
                try:
                    if await link.is_visible():
                        href = await link.get_attribute('href')
                        text = await link.inner_text() or href
                        
                        if href and not href.startswith('#') and not href.startswith('javascript:'):
                            full_href = urljoin(url, href)
                            
                            elements.append({
                                'type': 'link',
                                'text': text.strip()[:100],
                                'href': full_href,
                                'selector': f'a[href="{href}"]',
                                'index': i,
                                'url': url,
                                'state_hash': state_hash
                            })
                except Exception as e:
                    logger.debug(f"Error extracting link {i}: {e}")
            
            # Extract inputs
            inputs = await self.page.locator('input, textarea, select').all()
            for i, input_elem in enumerate(inputs):
                try:
                    if await input_elem.is_visible():
                        input_type = await input_elem.get_attribute('type') or 'text'
                        placeholder = await input_elem.get_attribute('placeholder') or ''
                        name = await input_elem.get_attribute('name') or f"input_{i}"
                        
                        elements.append({
                            'type': 'input',
                            'input_type': input_type,
                            'name': name,
                            'placeholder': placeholder,
                            'selector': f'input[name="{name}"]' if name else f'input >> nth={i}',
                            'index': i,
                            'url': url,
                            'state_hash': state_hash
                        })
                except Exception as e:
                    logger.debug(f"Error extracting input {i}: {e}")
            
        except Exception as e:
            logger.error(f"Error extracting elements: {e}")
        
        logger.info(f"Extracted {len(elements)} interactive elements from {url}")
        return elements

    async def _execute_action(self, element: Dict[str, Any]) -> bool:
        """Execute action on an element with error handling."""
        try:
            selector = element['selector']
            element_type = element['type']
            
            logger.info(f"🎯 Executing action on {element_type}: {element.get('text', selector)[:50]}")
            
            # Wait for element
            await self.page.wait_for_selector(selector, timeout=self.action_timeout)
            locator = self.page.locator(selector).first
            
            # Execute based on type
            if element_type == 'button':
                await locator.click(timeout=self.action_timeout)
            elif element_type == 'link':
                href = element.get('href', '')
                if href and self._is_same_domain(href):
                    await locator.click(timeout=self.action_timeout)
                else:
                    return False  # Skip external links
            elif element_type == 'input':
                input_type = element.get('input_type', 'text')
                if input_type in ['text', 'email', 'search', 'tel', 'url']:
                    test_value = self._get_test_value(input_type)
                    await locator.fill(test_value, timeout=self.action_timeout)
            
            # Record the action
            self.explored_actions.append({
                'element': element,
                'timestamp': time.time(),
                'success': True
            })
            
            # Wait for state changes
            await asyncio.sleep(1)
            return True
            
        except PlaywrightTimeoutError:
            logger.warning(f"Action timeout: {element_type}")
            
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "action_timeout",
                    f"{element_type}_{element.get('text', 'unknown')[:30]}",
                    self.page.url
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "action_error", 
                    f"{element_type}_{str(e)[:30]}",
                    self.page.url
                )
            
            return False

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL is same domain as base URL."""
        try:
            base_domain = urlparse(self.base_url).netloc
            url_domain = urlparse(url).netloc
            return url_domain == base_domain or url_domain == ''
        except:
            return False

    def _get_test_value(self, input_type: str) -> str:
        """Get test values for different input types."""
        test_values = {
            'text': 'Test Input',
            'email': 'test@example.com',
            'search': 'search test',
            'tel': '555-1234',
            'url': 'https://example.com'
        }
        return test_values.get(input_type, 'test')

    async def _systematic_exploration(self) -> None:
        """Perform systematic exploration of the website."""
        logger.info("🔍 Starting systematic exploration")
        
        # Initial page exploration
        elements = await self._extract_interactive_elements()
        self.discovered_elements.extend(elements)
        
        # Group elements by type for reporting
        buttons = [e for e in elements if e['type'] == 'button']
        links = [e for e in elements if e['type'] == 'link']
        inputs = [e for e in elements if e['type'] == 'input']
        
        logger.info(f"📊 Discovered: {len(buttons)} buttons, {len(links)} links, {len(inputs)} inputs")
        
        # Test buttons systematically
        for button in buttons[:20]:  # Limit to prevent infinite loops
            try:
                success = await self._execute_action(button)
                if success:
                    # Check if we're on a new page/state
                    await asyncio.sleep(2)
                    current_url = self.page.url
                    
                    if current_url not in self.visited_urls:
                        self.visited_urls.add(current_url)
                        logger.info(f"🆕 New page discovered: {current_url}")
                        
                        # Extract elements from new page
                        new_elements = await self._extract_interactive_elements()
                        self.discovered_elements.extend(new_elements)
                        
                        # Record state transition
                        self.state_transitions.append({
                            'from_url': button['url'],
                            'to_url': current_url,
                            'action': 'click',
                            'element': button['text'],
                            'timestamp': time.time()
                        })
            except Exception as e:
                logger.warning(f"Error testing button: {e}")

    def _generate_xml_sitemap(self, domain: str) -> str:
        """Generate comprehensive XML sitemap."""
        # Group elements by type and state
        elements_by_type = {}
        states_info = {}
        
        for element in self.discovered_elements:
            elem_type = element['type']
            state_hash = element.get('state_hash', 'unknown')
            
            if elem_type not in elements_by_type:
                elements_by_type[elem_type] = []
            elements_by_type[elem_type].append(element)
            
            if state_hash not in states_info:
                states_info[state_hash] = {
                    'url': element['url'],
                    'elements': []
                }
            states_info[state_hash]['elements'].append(element)
        
        # Generate XML
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append(f'<ApplicationStateFingerprint domain="{domain}" total_states="{len(states_info)}" total_transitions="{len(self.state_transitions)}">')
        
        # States section
        xml_lines.append('  <States>')
        for state_hash, state_info in states_info.items():
            xml_lines.append(f'    <State fingerprint="{state_hash}" type="page">')
            xml_lines.append(f'      <URL>{state_info["url"]}</URL>')
            xml_lines.append(f'      <PageHash>{state_hash}</PageHash>')
            
            # Count elements by type in this state
            state_elements = {}
            for elem in state_info['elements']:
                elem_type = elem['type']
                state_elements[elem_type] = state_elements.get(elem_type, 0) + 1
            
            xml_lines.append(f'      <InteractiveElements count="{len(state_info["elements"])}">')
            for elem_type, count in state_elements.items():
                xml_lines.append(f'        <{elem_type.title()}s count="{count}"/>')
            xml_lines.append('      </InteractiveElements>')
            xml_lines.append('    </State>')
        xml_lines.append('  </States>')
        
        # Transitions section
        xml_lines.append(f'  <Transitions count="{len(self.state_transitions)}">')
        for transition in self.state_transitions:
            xml_lines.append(f'    <Transition from="{transition["from_url"]}" to="{transition["to_url"]}" action="{transition["action"]}" element="{transition["element"][:50]}"/>')
        xml_lines.append('  </Transitions>')
        
        xml_lines.append('</ApplicationStateFingerprint>')
        
        return '\n'.join(xml_lines)

    async def explore(self) -> Dict[str, Any]:
        """Main exploration method."""
        logger.info(f"🚀 Starting comprehensive exploration of {self.base_url}")
        start_time = time.time()
        
        try:
            await self._setup_browser()
            
            success = await self._navigate_to_url(self.base_url)
            if not success:
                raise Exception("Failed to navigate to base URL")
            
            self.visited_urls.add(self.base_url)
            
            # Perform systematic exploration
            await self._systematic_exploration()
            
            await self._cleanup_browser()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Generate results
            results = self._generate_comprehensive_results(start_time, end_time, duration)
            
            # Save results using session manager
            domain = urlparse(self.base_url).netloc.replace(':', '_').replace('.', '_')
            xml_content = self._generate_xml_sitemap(domain)
            
            self.session_manager.save_sitemap(xml_content, domain)
            report_path = self.session_manager.save_session_report(results)
            
            logger.info(f"✅ Exploration completed in {duration:.1f}s")
            logger.info(f"📁 Session saved: {self.session_manager.session_dir}")
            
            return results
            
        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            
            # Capture failure screenshot
            if self.page and self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "exploration_failure",
                    str(e)[:50],
                    self.page.url if self.page else self.base_url
                )
            
            # Generate partial results
            end_time = time.time()
            duration = end_time - start_time
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
            if hasattr(self, 'browser') and self.browser:
                await self._cleanup_browser()

    def _generate_comprehensive_results(self, start_time: float, end_time: float, duration: float) -> Dict[str, Any]:
        """Generate comprehensive exploration results."""
        # Count elements by type
        buttons = [e for e in self.discovered_elements if e['type'] == 'button']
        links = [e for e in self.discovered_elements if e['type'] == 'link']
        inputs = [e for e in self.discovered_elements if e['type'] == 'input']
        
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
                    'unique_state_fingerprints': len(self.state_fingerprints),
                    'buttons_discovered': len(buttons),
                    'links_discovered': len(links),
                    'inputs_discovered': len(inputs),
                    'total_interactive_elements': len(self.discovered_elements)
                }
            },
            'state_fingerprints': list(self.state_fingerprints),
            'state_transitions': self.state_transitions,
            'bugs_found': self.bugs_found,
            'warnings': self.warnings,
            'console_messages': self.console_messages,
            'visited_urls': list(self.visited_urls),
            'discovered_elements': self.discovered_elements,
            'session_info': self.session_manager.get_session_info() if self.session_manager else {}
        } 