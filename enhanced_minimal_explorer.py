#!/usr/bin/env python3
"""
Enhanced Minimal Web Explorer with Comprehensive Modal Handling
Includes recursive modal exploration, modal state tracking, and exhaustive UI coverage
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
from modal_explorer import ModalExplorer

logger = logging.getLogger(__name__)

@dataclass
class EnhancedMinimalWebExplorer:
    """
    Enhanced web explorer with comprehensive modal handling and recursive exploration.
    """
    
    base_url: str
    max_actions_per_page: int = 50
    action_timeout: int = 5000
    headless: bool = True
    
    session_manager: Optional[SessionManager] = None
    modal_explorer: Optional[ModalExplorer] = None
    
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
        """Initialize browser and modal explorer."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()
        
        # Initialize modal explorer
        self.modal_explorer = ModalExplorer()
        self.modal_explorer.page = self.page
        self.modal_explorer.session_manager = self.session_manager
        
        # Event handlers
        self.page.on('console', self._handle_console_message)
        self.page.on('response', self._handle_response)
        logger.info("Enhanced browser setup completed with modal exploration")

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
        """Handle HTTP responses with enhanced error tracking."""
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
        """Handle console messages with modal-aware error tracking."""
        try:
            message_data = {
                'type': msg.type,
                'text': msg.text,
                'timestamp': time.time()
            }
            self.console_messages.append(message_data)
            
            if msg.type in ['error', 'assert'] and self.session_manager:
                # Check if we're currently exploring a modal
                context_info = "main_page"
                if self.modal_explorer and self.modal_explorer.modal_stack:
                    context_info = f"modal_{self.modal_explorer.modal_stack[-1]}"
                
                await self.session_manager.capture_error_screenshot(
                    self.page, f"console_{msg.type}", f"{context_info}_{msg.text[:50]}", self.page.url
                )
                
                error_record = {
                    'type': 'console_error',
                    'message': msg.text,
                    'context': context_info,
                    'timestamp': time.time()
                }
                self.bugs_found.append(error_record)
        except Exception as e:
            logger.error(f"Console handler error: {e}")

    async def _navigate_to_url(self, url: str) -> bool:
        """Navigate to URL with modal dismissal."""
        try:
            logger.info(f"Navigating to: {url}")
            
            # First, try to dismiss any existing modals
            if self.modal_explorer:
                await self._dismiss_any_existing_modals()
            
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

    async def _dismiss_any_existing_modals(self):
        """Dismiss any modals that might be blocking navigation."""
        try:
            existing_modals = await self.modal_explorer.detect_modals()
            for modal_info in existing_modals:
                if await self.modal_explorer.quick_dismiss_known_modal(modal_info):
                    logger.info(f"✅ Dismissed existing modal: {modal_info['modal_hash']}")
                else:
                    # Try generic ESC key
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"Error dismissing existing modals: {e}")

    async def _extract_interactive_elements(self) -> List[Dict[str, Any]]:
        """Extract interactive elements with modal awareness."""
        elements = []
        
        try:
            content = await self.page.content()
            state_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            self.state_fingerprints.add(state_hash)
            url = self.page.url
            
            # First, check for modals BEFORE extracting page elements
            modals_detected = await self.modal_explorer.detect_modals()
            
            if modals_detected:
                logger.info(f"🎭 Found {len(modals_detected)} modal(s) on page - will explore modals first")
                
                # Explore each modal recursively
                for modal_info in modals_detected:
                    if await self.modal_explorer.should_explore_modal(modal_info):
                        logger.info(f"🔍 Starting recursive exploration of modal: {modal_info['modal_hash']}")
                        
                        modal_result = await self.modal_explorer.explore_modal_recursively(modal_info)
                        
                        # Add modal exploration results to our session
                        if modal_result.get('elements_tested'):
                            self.executed_actions.extend(modal_result['elements_tested'])
                        
                        if modal_result.get('errors'):
                            self.warnings.extend(modal_result['errors'])
                            
                        logger.info(f"✅ Modal exploration completed: {len(modal_result.get('elements_tested', []))} actions performed")
                    
                    else:
                        # Quick dismiss known modal
                        if await self.modal_explorer.quick_dismiss_known_modal(modal_info):
                            logger.info(f"⚡ Quick dismissed known modal: {modal_info['modal_hash']}")
                
                # After modal exploration, re-extract page content (modals might have changed page state)
                await asyncio.sleep(2)
                content = await self.page.content()
                state_hash = hashlib.md5(content.encode()).hexdigest()[:12]
                self.state_fingerprints.add(state_hash)
            
            # Now extract regular page elements (with modals dismissed)
            logger.info(f"🔍 Extracting main page elements (state: {state_hash})")
            
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
                                'state_hash': state_hash,
                                'context': 'main_page'
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
                                'state_hash': state_hash,
                                'context': 'main_page'
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
                            'state_hash': state_hash,
                            'context': 'main_page'
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
            
            logger.info(f"📊 Main page elements: {len(buttons)} buttons, {len(links)} links, {len(inputs)} inputs")
            
            # Add modal exploration summary
            modal_summary = self.modal_explorer.get_exploration_summary()
            if modal_summary['total_modals_discovered'] > 0:
                logger.info(f"🎭 Modal exploration summary: {modal_summary['modals_fully_explored']}/{modal_summary['total_modals_discovered']} modals explored, {modal_summary['total_modal_elements']} modal elements tested")
            
            return unique_elements
            
        except Exception as e:
            logger.error(f"Element extraction error: {e}")
            return []

    async def _execute_action(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action on element with modal detection."""
        result = {
            'element': element,
            'timestamp': time.time(),
            'success': False,
            'context': element.get('context', 'main_page')
        }
        
        try:
            selector = element['selector']
            element_type = element['type']
            
            logger.info(f"🎯 Testing {element_type}: {element.get('text', element.get('name', ''))[:50]}")
            
            # Before action, check for modals that might block interaction
            existing_modals = await self.modal_explorer.detect_modals()
            if existing_modals:
                logger.info(f"🎭 Modal detected before action - attempting dismissal")
                for modal_info in existing_modals:
                    await self.modal_explorer.quick_dismiss_known_modal(modal_info)
                await asyncio.sleep(1)
            
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
            
            # After action, check for new modals
            await asyncio.sleep(1)
            new_modals = await self.modal_explorer.detect_modals()
            
            if new_modals:
                logger.info(f"🆕 Action triggered {len(new_modals)} modal(s)")
                
                for modal_info in new_modals:
                    if await self.modal_explorer.should_explore_modal(modal_info):
                        logger.info(f"🔍 Action-triggered modal exploration: {modal_info['modal_hash']}")
                        
                        modal_result = await self.modal_explorer.explore_modal_recursively(modal_info)
                        
                        # Track modal results
                        if modal_result.get('elements_tested'):
                            self.executed_actions.extend(modal_result['elements_tested'])
                        
                        result['triggered_modal_exploration'] = {
                            'modal_hash': modal_info['modal_hash'],
                            'elements_tested': len(modal_result.get('elements_tested', [])),
                            'nested_modals': len(modal_result.get('nested_modals_found', []))
                        }
                        
                        logger.info(f"✅ Action-triggered modal exploration completed")
            
        except Exception as e:
            result['error'] = str(e)
            logger.warning(f"Action failed: {e}")
            
            if self.session_manager:
                context_info = element.get('context', 'main_page')
                await self.session_manager.capture_error_screenshot(
                    self.page, "action_error", f"{context_info}_{str(e)[:30]}", self.page.url
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
        """Enhanced systematic exploration with comprehensive modal handling."""
        logger.info("🚀 Starting enhanced systematic exploration with modal handling")
        
        # Phase 1: Extract elements (this includes modal exploration)
        elements = await self._extract_interactive_elements()
        self.discovered_elements.extend(elements)
        
        if not elements:
            logger.warning("No main page interactive elements found after modal exploration!")
            return
        
        # Phase 2: Test main page elements
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
                
                # Check for page navigation
                current_url = self.page.url
                if current_url != self.base_url and current_url not in self.visited_urls:
                    self.visited_urls.add(current_url)
                    logger.info(f"🆕 New page discovered: {current_url}")
                    
                    # Brief exploration of new page (including its modals)
                    await asyncio.sleep(2)
                    new_page_modals = await self.modal_explorer.detect_modals()
                    
                    if new_page_modals:
                        logger.info(f"🎭 New page has {len(new_page_modals)} modal(s) - exploring")
                        for modal_info in new_page_modals:
                            if await self.modal_explorer.should_explore_modal(modal_info):
                                await self.modal_explorer.explore_modal_recursively(modal_info)
                    
                    # Navigate back to main page
                    await self._navigate_to_url(self.base_url)
                    await asyncio.sleep(2)
                
                if tested % 10 == 0:
                    logger.info(f"📊 Progress: {tested}/{len(elements)} ({successful} successful)")
                    
            except Exception as e:
                logger.error(f"Error testing element: {e}")
        
        logger.info(f"✅ Enhanced exploration completed: {tested} main page elements tested, {successful} successful")
        
        # Final modal summary
        modal_summary = self.modal_explorer.get_exploration_summary()
        logger.info(f"🎭 Final modal exploration summary: {modal_summary['modals_fully_explored']} modals fully explored, {modal_summary['total_modal_elements']} total modal elements tested")

    def _generate_xml_sitemap(self, domain: str) -> str:
        """Generate enhanced XML sitemap including modal information."""
        buttons = [e for e in self.discovered_elements if e['type'] == 'button']
        links = [e for e in self.discovered_elements if e['type'] == 'link']
        inputs = [e for e in self.discovered_elements if e['type'] == 'input']
        
        modal_summary = self.modal_explorer.get_exploration_summary()
        
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ApplicationStateFingerprint domain="{domain}" total_elements="{len(self.discovered_elements)}" 
                            total_modals="{modal_summary['total_modals_discovered']}" 
                            modals_explored="{modal_summary['modals_fully_explored']}">
  <MainPageElements>
    <Buttons count="{len(buttons)}"/>
    <Links count="{len(links)}"/>
    <Inputs count="{len(inputs)}"/>
  </MainPageElements>
  
  <ModalExploration>
    <TotalModalsDiscovered>{modal_summary['total_modals_discovered']}</TotalModalsDiscovered>
    <ModalsFullyExplored>{modal_summary['modals_fully_explored']}</ModalsFullyExplored>
    <TotalModalElements>{modal_summary['total_modal_elements']}</TotalModalElements>
    <ModalTypes>'''
        
        for modal_type, count in modal_summary.get('modal_types', {}).items():
            xml += f'\n      <{modal_type.title()} count="{count}"/>'
        
        xml += f'''
    </ModalTypes>
  </ModalExploration>
  
  <States>
    <State fingerprint="main" url="{self.base_url}">
      <InteractiveElements count="{len(self.discovered_elements)}">
        <Buttons count="{len(buttons)}"/>
        <Links count="{len(links)}"/>
        <Inputs count="{len(inputs)}"/>
      </InteractiveElements>
      <ModalStates explored="{modal_summary['modals_fully_explored']}" total="{modal_summary['total_modals_discovered']}"/>
    </State>
  </States>
</ApplicationStateFingerprint>'''
        
        return xml

    async def explore(self) -> Dict[str, Any]:
        """Main enhanced exploration method with comprehensive modal handling."""
        logger.info(f"🚀 Starting enhanced exploration with modal recursion: {self.base_url}")
        start_time = time.time()
        
        try:
            await self._setup_browser()
            
            if not await self._navigate_to_url(self.base_url):
                raise Exception("Failed to navigate to base URL")
            
            self.visited_urls.add(self.base_url)
            await self._systematic_exploration()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Generate comprehensive results
            modal_summary = self.modal_explorer.get_exploration_summary()
            
            results = {
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'exploration_status': 'completed',
                'base_url': self.base_url,
                'exploration_summary': {
                    'total_elements': len(self.discovered_elements),
                    'actions_performed': len(self.executed_actions),
                    'modal_exploration': modal_summary
                },
                'discovered_elements': self.discovered_elements,
                'executed_actions': self.executed_actions,
                'bugs_found': self.bugs_found,
                'warnings': self.warnings,
                'modal_exploration_results': modal_summary,
                'session_info': self.session_manager.get_session_info()
            }
            
            # Save enhanced results
            domain = self.domain.replace('.', '_')
            xml_content = self._generate_xml_sitemap(domain)
            
            self.session_manager.save_sitemap(xml_content, domain)
            self.session_manager.save_session_report(results)
            
            logger.info(f"✅ Enhanced exploration completed in {duration:.1f}s")
            logger.info(f"📊 Total coverage: {len(self.discovered_elements)} main elements + {modal_summary['total_modal_elements']} modal elements")
            logger.info(f"📁 Session saved: {self.session_manager.session_dir}")
            
            return results
            
        except Exception as e:
            logger.error(f"Enhanced exploration failed: {e}")
            return {'error': str(e)}
            
        finally:
            await self._cleanup_browser() 