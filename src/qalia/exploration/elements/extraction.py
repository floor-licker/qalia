"""
Element Extraction Utility

Handles discovery and extraction of interactive elements from web pages.
Supports both static HTML parsing and live page element discovery.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ElementExtractor:
    """
    Extracts interactive elements from web pages using multiple strategies.
    
    Combines static HTML parsing with live page element discovery
    to provide comprehensive element detection.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        
        # Element type configurations
        self.button_selectors = [
            'button',
            'input[type="button"]',
            'input[type="submit"]', 
            'input[type="reset"]',
            '[role="button"]',
            '.btn',
            '.button',
            '[data-testid*="button"]'
        ]
        
        self.input_selectors = [
            'input[type="text"]',
            'input[type="email"]',
            'input[type="password"]',
            'input[type="search"]',
            'input[type="tel"]',
            'input[type="url"]',
            'input[type="number"]',
            'textarea'
        ]
        
        self.link_selectors = [
            'a[href]'
        ]
        
        self.select_selectors = [
            'select'
        ]
    
    async def extract_from_page(self, page) -> List[Dict[str, Any]]:
        """
        Extract interactive elements from a live Playwright page.
        
        Args:
            page: Playwright page instance
            
        Returns:
            List of element dictionaries
        """
        elements = []
        url = page.url
        
        try:
            # Get page content for fingerprinting
            content = await page.content()
            state_hash = self._generate_state_hash(content)
            
            # Extract different element types
            buttons = await self._extract_buttons_live(page, url, state_hash)
            links = await self._extract_links_live(page, url, state_hash)
            inputs = await self._extract_inputs_live(page, url, state_hash)
            selects = await self._extract_selects_live(page, url, state_hash)
            
            elements.extend(buttons)
            elements.extend(links)
            elements.extend(inputs)
            elements.extend(selects)
            
            # Remove duplicates and filter
            elements = self._deduplicate_elements(elements)
            
            logger.info(f"📋 Extracted {len(elements)} interactive elements from live page")
            self._log_element_summary(elements)
            
            return elements
            
        except Exception as e:
            logger.error(f"Live element extraction failed: {e}")
            return []
    
    def extract_from_html(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract interactive elements from static HTML content.
        
        Args:
            html_content: Raw HTML content
            url: Page URL for context
            
        Returns:
            List of element dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            state_hash = self._generate_state_hash(html_content)
            
            elements = []
            
            # Extract different element types
            buttons = self._extract_buttons_static(soup, url, state_hash)
            links = self._extract_links_static(soup, url, state_hash)
            inputs = self._extract_inputs_static(soup, url, state_hash)
            selects = self._extract_selects_static(soup, url, state_hash)
            
            elements.extend(buttons)
            elements.extend(links)
            elements.extend(inputs)
            elements.extend(selects)
            
            # Remove duplicates and filter
            elements = self._deduplicate_elements(elements)
            
            logger.info(f"📋 Extracted {len(elements)} interactive elements from HTML")
            self._log_element_summary(elements)
            
            return elements
            
        except Exception as e:
            logger.error(f"HTML element extraction failed: {e}")
            return []
    
    async def _extract_buttons_live(self, page, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract button elements from live page."""
        buttons = []
        
        for selector in self.button_selectors:
            try:
                elements = await page.locator(selector).all()
                for i, button in enumerate(elements):
                    if await button.is_visible():
                        text = (await button.inner_text() or 
                               await button.get_attribute('value') or 
                               await button.get_attribute('aria-label') or 
                               f"button_{i}")
                        
                        # Generate robust selector
                        robust_selector = await self._generate_robust_selector(button, text, 'button')
                        
                        buttons.append({
                            'type': 'button',
                            'text': text.strip()[:100],
                            'selector': robust_selector,
                            'index': i,
                            'url': url,
                            'state_hash': state_hash,
                            'base_selector': selector
                        })
            except Exception as e:
                logger.debug(f"Error extracting buttons with selector {selector}: {e}")
        
        return buttons
    
    async def _extract_links_live(self, page, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract link elements from live page."""
        links = []
        
        try:
            elements = await page.locator('a[href]').all()
            for i, link in enumerate(elements):
                if await link.is_visible():
                    href = await link.get_attribute('href')
                    text = await link.inner_text() or href
                    
                    if href and not href.startswith('#') and not href.startswith('javascript:'):
                        full_href = urljoin(url, href)
                        
                        # Generate robust selector
                        robust_selector = await self._generate_robust_selector(link, text, 'link')
                        
                        links.append({
                            'type': 'link',
                            'text': text.strip()[:100],
                            'href': full_href,
                            'selector': robust_selector,
                            'index': i,
                            'url': url,
                            'state_hash': state_hash
                        })
        except Exception as e:
            logger.debug(f"Error extracting links: {e}")
        
        return links
    
    async def _extract_inputs_live(self, page, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract input elements from live page."""
        inputs = []
        
        try:
            elements = await page.locator('input, textarea').all()
            for i, input_elem in enumerate(elements):
                if await input_elem.is_visible():
                    input_type = await input_elem.get_attribute('type') or 'text'
                    name = await input_elem.get_attribute('name') or f"input_{i}"
                    placeholder = await input_elem.get_attribute('placeholder') or ''
                    
                    if input_type in ['text', 'email', 'password', 'search', 'tel', 'url', 'number'] or input_elem.tag_name == 'textarea':
                        # Generate robust selector
                        robust_selector = await self._generate_robust_selector(input_elem, name, 'input')
                        
                        inputs.append({
                            'type': 'input',
                            'input_type': input_type,
                            'name': name,
                            'placeholder': placeholder,
                            'selector': robust_selector,
                            'index': i,
                            'url': url,
                            'state_hash': state_hash
                        })
        except Exception as e:
            logger.debug(f"Error extracting inputs: {e}")
        
        return inputs
    
    async def _extract_selects_live(self, page, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract select elements from live page."""
        selects = []
        
        try:
            elements = await page.locator('select').all()
            for i, select in enumerate(elements):
                if await select.is_visible():
                    name = await select.get_attribute('name') or f"select_{i}"
                    
                    # Extract options
                    options = []
                    option_elements = await select.locator('option').all()
                    for opt in option_elements:
                        value = await opt.get_attribute('value') or ''
                        text = await opt.inner_text() or value
                        options.append({'value': value, 'text': text.strip()})
                    
                    # Generate robust selector
                    robust_selector = await self._generate_robust_selector(select, name, 'select')
                    
                    selects.append({
                        'type': 'select',
                        'name': name,
                        'selector': robust_selector,
                        'options': options,
                        'index': i,
                        'url': url,
                        'state_hash': state_hash
                    })
        except Exception as e:
            logger.debug(f"Error extracting selects: {e}")
        
        return selects
    
    def _extract_buttons_static(self, soup: BeautifulSoup, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract buttons from static HTML."""
        buttons = []
        
        button_tags = soup.find_all(['button', 'input'])
        for i, button in enumerate(button_tags):
            if button.name == 'input' and button.get('type') not in ['button', 'submit', 'reset']:
                continue
            
            text = (button.get_text(strip=True) or 
                   button.get('value') or 
                   button.get('aria-label') or 
                   f"button_{i}")
            
            selector = self._generate_static_selector(button, text, 'button')
            
            buttons.append({
                'type': 'button',
                'text': text[:100],
                'selector': selector,
                'index': i,
                'url': url,
                'state_hash': state_hash,
                'attributes': dict(button.attrs)
            })
        
        return buttons
    
    def _extract_links_static(self, soup: BeautifulSoup, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract links from static HTML."""
        links = []
        
        link_tags = soup.find_all('a', href=True)
        for i, link in enumerate(link_tags):
            href = link.get('href')
            text = link.get_text(strip=True) or href
            
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                full_href = urljoin(url, href)
                selector = self._generate_static_selector(link, text, 'link')
                
                links.append({
                    'type': 'link',
                    'text': text[:100],
                    'href': full_href,
                    'selector': selector,
                    'index': i,
                    'url': url,
                    'state_hash': state_hash,
                    'attributes': dict(link.attrs)
                })
        
        return links
    
    def _extract_inputs_static(self, soup: BeautifulSoup, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract inputs from static HTML."""
        inputs = []
        
        input_tags = soup.find_all(['input', 'textarea'])
        for i, input_elem in enumerate(input_tags):
            input_type = input_elem.get('type', 'text')
            name = input_elem.get('name', f"input_{i}")
            placeholder = input_elem.get('placeholder', '')
            
            if input_type in ['text', 'email', 'password', 'search', 'tel', 'url', 'number'] or input_elem.name == 'textarea':
                selector = self._generate_static_selector(input_elem, name, 'input')
                
                inputs.append({
                    'type': 'input',
                    'input_type': input_type,
                    'name': name,
                    'placeholder': placeholder,
                    'selector': selector,
                    'index': i,
                    'url': url,
                    'state_hash': state_hash,
                    'attributes': dict(input_elem.attrs)
                })
        
        return inputs
    
    def _extract_selects_static(self, soup: BeautifulSoup, url: str, state_hash: str) -> List[Dict[str, Any]]:
        """Extract selects from static HTML."""
        selects = []
        
        select_tags = soup.find_all('select')
        for i, select in enumerate(select_tags):
            name = select.get('name', f"select_{i}")
            
            # Extract options
            options = []
            for opt in select.find_all('option'):
                value = opt.get('value', '')
                text = opt.get_text(strip=True) or value
                options.append({'value': value, 'text': text})
            
            selector = self._generate_static_selector(select, name, 'select')
            
            selects.append({
                'type': 'select',
                'name': name,
                'selector': selector,
                'options': options,
                'index': i,
                'url': url,
                'state_hash': state_hash,
                'attributes': dict(select.attrs)
            })
        
        return selects
    
    async def _generate_robust_selector(self, element, text: str, element_type: str) -> str:
        """Generate robust selector for live element."""
        try:
            # Try ID first
            elem_id = await element.get_attribute('id')
            if elem_id:
                return f"#{elem_id}"
            
            # Try test attributes
            test_attrs = ['data-testid', 'data-test', 'data-cy']
            for attr in test_attrs:
                value = await element.get_attribute(attr)
                if value:
                    return f"[{attr}='{value}']"
            
            # Try name attribute
            name = await element.get_attribute('name')
            if name:
                tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                return f"{tag_name}[name='{name}']"
            
            # Try text-based selectors
            if text and len(text.strip()) < 50:
                clean_text = text.strip().replace('"', '\\"')
                tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                
                if element_type == 'button':
                    return f'button:has-text("{clean_text}")'
                elif element_type == 'link':
                    return f'a:has-text("{clean_text}")'
            
            # Fallback to tag + nth-child
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            return f"{tag_name}"
            
        except Exception as e:
            logger.debug(f"Error generating selector: {e}")
            return f"{element_type}"
    
    def _generate_static_selector(self, element, text: str, element_type: str) -> str:
        """Generate selector for static HTML element."""
        # Try ID first
        if element.get('id'):
            return f"#{element['id']}"
        
        # Try test attributes
        for attr in ['data-testid', 'data-test', 'data-cy']:
            if element.get(attr):
                return f"[{attr}='{element[attr]}']"
        
        # Try name attribute
        if element.get('name'):
            return f"{element.name}[name='{element['name']}']"
        
        # Try text-based selectors
        if text and len(text.strip()) < 50:
            clean_text = text.strip().replace('"', '\\"')
            if element_type == 'button':
                return f'button:has-text("{clean_text}")'
            elif element_type == 'link':
                return f'a:has-text("{clean_text}")'
        
        # Fallback
        return element.name
    
    def _generate_state_hash(self, content: str) -> str:
        """Generate hash for page state."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _deduplicate_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate elements based on selector and text."""
        seen = set()
        unique_elements = []
        
        for element in elements:
            # Create deduplication key
            key = f"{element['type']}:{element['selector']}:{element.get('text', element.get('name', ''))[:30]}"
            
            if key not in seen:
                seen.add(key)
                unique_elements.append(element)
        
        return unique_elements
    
    def _log_element_summary(self, elements: List[Dict[str, Any]]) -> None:
        """Log summary of extracted elements."""
        summary = {}
        for element in elements:
            elem_type = element['type']
            summary[elem_type] = summary.get(elem_type, 0) + 1
        
        summary_parts = [f"{count} {elem_type}s" for elem_type, count in summary.items()]
        logger.info(f"   📊 Found: {', '.join(summary_parts)}")
    
    def filter_elements_by_criteria(self, elements: List[Dict[str, Any]], **criteria) -> List[Dict[str, Any]]:
        """Filter elements by various criteria."""
        filtered = elements
        
        if 'element_type' in criteria:
            filtered = [e for e in filtered if e['type'] == criteria['element_type']]
        
        if 'has_text' in criteria:
            filtered = [e for e in filtered if criteria['has_text'].lower() in e.get('text', '').lower()]
        
        if 'url_pattern' in criteria:
            filtered = [e for e in filtered if criteria['url_pattern'] in e.get('href', '')]
        
        return filtered 