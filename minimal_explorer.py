#!/usr/bin/env python3
"""
Minimal Web Explorer with Session Management
"""

import asyncio
import logging
import hashlib
import time
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from session_manager import SessionManager

logger = logging.getLogger(__name__)

@dataclass
class MinimalWebExplorer:
    """Minimal web explorer with comprehensive element discovery."""
    
    base_url: str
    max_actions_per_page: int = 50
    action_timeout: int = 5000
    headless: bool = True
    
    session_manager: Optional[SessionManager] = None
    browser = None
    context = None
    page = None
    
    visited_urls: Set[str] = field(default_factory=set)
    discovered_elements: List[Dict[str, Any]] = field(default_factory=list)
    state_fingerprints: Set[str] = field(default_factory=set)
    console_messages: List[Dict[str, Any]] = field(default_factory=list)
    bugs_found: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    executed_actions: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.session_manager is None:
            self.session_manager = SessionManager(self.base_url)
        self.domain = urlparse(self.base_url).netloc

    async def _setup_browser(self) -> None:
        """Initialize browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()
        
        # Event handlers
        self.page.on('console', self._handle_console_message)
        self.page.on('response', self._handle_response)
        logger.info("Browser setup completed")

    async def _cleanup_browser(self) -> None:
        """Clean up browser."""
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
            logger.warning(f"Cleanup error: {e}")

    async def _handle_response(self, response):
        """Handle HTTP responses."""
        try:
            if response.status >= 400:
                error_type = f"{response.status}_error"
                logger.warning(f"HTTP {response.status}: {response.url}")
                
                if self.session_manager:
                    await self.session_manager.capture_error_screenshot(
                        self.page, error_type, f"HTTP_{response.status}", response.url
                    )
                
                error_record = {
                    'type': 'http_error',
                    'status_code': response.status,
                    'url': response.url,
                    'timestamp': time.time()
                }
                
                if response.status >= 500:
                    self.bugs_found.append(error_record)
                else:
                    self.warnings.append(error_record)
        except Exception as e:
            logger.error(f"Response handler error: {e}")

    async def _handle_console_message(self, msg):
        """Handle console messages."""
        try:
            message_data = {
                'type': msg.type,
                'text': msg.text,
                'timestamp': time.time()
            }
            self.console_messages.append(message_data)
            
            if msg.type in ['error', 'assert'] and self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page, f"console_{msg.type}", msg.text[:100], self.page.url
                )
                
                error_record = {
                    'type': 'console_error',
                    'message': msg.text,
                    'timestamp': time.time()
                }
                self.bugs_found.append(error_record)
        except Exception as e:
            logger.error(f"Console handler error: {e}")

    async def _navigate_to_url(self, url: str) -> bool:
        """Navigate to URL."""
        try:
            logger.info(f"Navigating to: {url}")
            response = await self.page.goto(url, timeout=15000, wait_until='domcontentloaded')
            
            if response and response.status >= 400:
                return False
            
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page, "navigation_error", str(e)[:50], url
                )
            return False

    async def _extract_interactive_elements(self) -> List[Dict[str, Any]]:
        """Extract interactive elements."""
        elements = []
        
        try:
            content = await self.page.content()
            state_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            self.state_fingerprints.add(state_hash)
            url = self.page.url
            
            # Extract buttons
            button_selectors = [
                'button', 'input[type="button"]', 'input[type="submit"]',
                '[role="button"]', '.btn', '.button'
            ]
            
            for selector in button_selectors:
                try:
                    buttons = await self.page.locator(selector).all()
                    for i, button in enumerate(buttons):
                        if await button.is_visible():
                            text = await button.inner_text() or f"button_{i}"
                            elements.append({
                                'type': 'button',
                                'text': text.strip()[:100],
                                'selector': f'{selector}:nth-of-type({i+1})',
                                'url': url,
                                'state_hash': state_hash
                            })
                except:
                    continue
            
            # Extract links
            links = await self.page.locator('a[href]').all()
            for i, link in enumerate(links):
                try:
                    if await link.is_visible():
                        href = await link.get_attribute('href')
                        text = await link.inner_text() or href
                        
                        if href and not href.startswith('#'):
                            elements.append({
                                'type': 'link',
                                'text': text.strip()[:100],
                                'href': urljoin(url, href),
                                'selector': f'a:nth-of-type({i+1})',
                                'url': url,
                                'state_hash': state_hash
                            })
                except:
                    continue
            
            # Extract inputs
            inputs = await self.page.locator('input, textarea').all()
            for i, input_elem in enumerate(inputs):
                try:
                    if await input_elem.is_visible():
                        input_type = await input_elem.get_attribute('type') or 'text'
                        name = await input_elem.get_attribute('name') or f"input_{i}"
                        
                        elements.append({
                            'type': 'input',
                            'input_type': input_type,
                            'name': name,
                            'selector': f'input:nth-of-type({i+1})',
                            'url': url,
                            'state_hash': state_hash
                        })
                except:
                    continue
            
            # Remove duplicates
            unique_elements = []
            seen = set()
            for elem in elements:
                sig = f"{elem['type']}:{elem.get('text', elem.get('name', ''))}"
                if sig not in seen:
                    unique_elements.append(elem)
                    seen.add(sig)
            
            buttons = [e for e in unique_elements if e['type'] == 'button']
            links = [e for e in unique_elements if e['type'] == 'link']
            inputs = [e for e in unique_elements if e['type'] == 'input']
            
            logger.info(f"Found: {len(buttons)} buttons, {len(links)} links, {len(inputs)} inputs")
            return unique_elements
            
        except Exception as e:
            logger.error(f"Element extraction error: {e}")
            return []

    async def _execute_action(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action on element."""
        result = {
            'element': element,
            'timestamp': time.time(),
            'success': False
        }
        
        try:
            selector = element['selector']
            element_type = element['type']
            
            logger.info(f"Testing {element_type}: {element.get('text', element.get('name', ''))[:50]}")
            
            locator = self.page.locator(selector).first
            await locator.wait_for(timeout=self.action_timeout)
            
            if element_type == 'button':
                await locator.click(timeout=self.action_timeout)
                result['action'] = 'click'
                
            elif element_type == 'link':
                href = element.get('href', '')
                if self._is_same_domain(href):
                    await locator.click(timeout=self.action_timeout)
                    result['action'] = 'click'
                else:
                    result['action'] = 'skipped_external'
                    result['success'] = True
                    return result
                    
            elif element_type == 'input':
                input_type = element.get('input_type', 'text')
                if input_type in ['text', 'email', 'search']:
                    await locator.fill('test input', timeout=self.action_timeout)
                    result['action'] = 'fill'
                else:
                    result['action'] = 'skipped'
                    result['success'] = True
                    return result
            
            result['success'] = True
            await asyncio.sleep(1)
            
        except Exception as e:
            result['error'] = str(e)
            logger.warning(f"Action failed: {e}")
            
            if self.session_manager:
                await self.session_manager.capture_error_screenshot(
                    self.page, "action_error", str(e)[:30], self.page.url
                )
        
        return result

    def _is_same_domain(self, url: str) -> bool:
        """Check if same domain."""
        try:
            base_domain = urlparse(self.base_url).netloc
            url_domain = urlparse(url).netloc
            return url_domain == base_domain or url_domain == ''
        except:
            return False

    async def _systematic_exploration(self) -> None:
        """Systematic exploration."""
        logger.info("Starting systematic exploration")
        
        elements = await self._extract_interactive_elements()
        self.discovered_elements.extend(elements)
        
        if not elements:
            logger.warning("No interactive elements found!")
            return
        
        tested = 0
        successful = 0
        
        for element in elements:
            if tested >= self.max_actions_per_page:
                break
                
            try:
                result = await self._execute_action(element)
                self.executed_actions.append(result)
                
                tested += 1
                if result['success']:
                    successful += 1
                
                # Check for new page
                current_url = self.page.url
                if current_url != self.base_url and current_url not in self.visited_urls:
                    self.visited_urls.add(current_url)
                    logger.info(f"New page: {current_url}")
                    
                    await asyncio.sleep(2)
                    await self._navigate_to_url(self.base_url)
                    await asyncio.sleep(2)
                
                if tested % 10 == 0:
                    logger.info(f"Progress: {tested}/{len(elements)} ({successful} successful)")
                    
            except Exception as e:
                logger.error(f"Error testing element: {e}")
        
        logger.info(f"Completed: {tested} elements tested, {successful} successful")

    def _generate_xml_sitemap(self, domain: str) -> str:
        """Generate XML sitemap."""
        buttons = [e for e in self.discovered_elements if e['type'] == 'button']
        links = [e for e in self.discovered_elements if e['type'] == 'link']
        inputs = [e for e in self.discovered_elements if e['type'] == 'input']
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ApplicationStateFingerprint domain="{domain}" total_elements="{len(self.discovered_elements)}">
  <ElementSummary>
    <Buttons count="{len(buttons)}"/>
    <Links count="{len(links)}"/>
    <Inputs count="{len(inputs)}"/>
  </ElementSummary>
  <States>
    <State fingerprint="main" url="{self.base_url}">
      <InteractiveElements count="{len(self.discovered_elements)}">
        <Buttons count="{len(buttons)}"/>
        <Links count="{len(links)}"/>
        <Inputs count="{len(inputs)}"/>
      </InteractiveElements>
    </State>
  </States>
</ApplicationStateFingerprint>'''
        
        return xml

    async def explore(self) -> Dict[str, Any]:
        """Main exploration method."""
        logger.info(f"Starting exploration of {self.base_url}")
        start_time = time.time()
        
        try:
            await self._setup_browser()
            
            if not await self._navigate_to_url(self.base_url):
                raise Exception("Failed to navigate to base URL")
            
            self.visited_urls.add(self.base_url)
            await self._systematic_exploration()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Generate results
            buttons = [e for e in self.discovered_elements if e['type'] == 'button']
            results = {
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'exploration_status': 'completed',
                'base_url': self.base_url,
                'exploration_summary': {
                    'total_elements': len(self.discovered_elements),
                    'actions_performed': len(self.executed_actions)
                },
                'discovered_elements': self.discovered_elements,
                'executed_actions': self.executed_actions,
                'bugs_found': self.bugs_found,
                'warnings': self.warnings,
                'session_info': self.session_manager.get_session_info()
            }
            
            # Save results
            domain = self.domain.replace('.', '_')
            xml_content = self._generate_xml_sitemap(domain)
            
            self.session_manager.save_sitemap(xml_content, domain)
            self.session_manager.save_session_report(results)
            
            logger.info(f"Exploration completed in {duration:.1f}s")
            logger.info(f"Session saved: {self.session_manager.session_dir}")
            
            return results
            
        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            return {'error': str(e)}
            
        finally:
            await self._cleanup_browser() 