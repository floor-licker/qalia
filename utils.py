"""
Utility functions for DOM parsing, element extraction, and helper functions.
"""

from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def extract_interactive_elements(html_content: str, base_url: str) -> List[Dict[str, Any]]:
    """
    Extract interactive elements from HTML content.
    
    Args:
        html_content: Raw HTML content
        base_url: Base URL for resolving relative links
        
    Returns:
        List of dictionaries containing element information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = []
    
    # Extract buttons
    for button in soup.find_all(['button', 'input']):
        if button.name == 'input' and button.get('type') not in ['button', 'submit', 'reset']:
            continue
            
        element_info = {
            'type': 'button',
            'text': get_element_text(button),
            'selector': generate_selector(button),
            'attributes': dict(button.attrs)
        }
        elements.append(element_info)
    
    # Extract input fields
    for input_field in soup.find_all('input'):
        input_type = input_field.get('type', 'text')
        if input_type in ['text', 'email', 'password', 'search', 'tel', 'url']:
            element_info = {
                'type': 'input',
                'input_type': input_type,
                'placeholder': input_field.get('placeholder', ''),
                'name': input_field.get('name', ''),
                'selector': generate_selector(input_field),
                'attributes': dict(input_field.attrs)
            }
            elements.append(element_info)
    
    # Extract textareas
    for textarea in soup.find_all('textarea'):
        element_info = {
            'type': 'textarea',
            'placeholder': textarea.get('placeholder', ''),
            'name': textarea.get('name', ''),
            'selector': generate_selector(textarea),
            'attributes': dict(textarea.attrs)
        }
        elements.append(element_info)
    
    # Extract links
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href and not href.startswith('#') and not href.startswith('javascript:'):
            full_url = urljoin(base_url, href)
            element_info = {
                'type': 'link',
                'text': get_element_text(link),
                'href': full_url,
                'selector': generate_selector(link),
                'attributes': dict(link.attrs)
            }
            elements.append(element_info)
    
    # Extract select dropdowns
    for select in soup.find_all('select'):
        options = [{'value': opt.get('value', ''), 'text': get_element_text(opt)} 
                  for opt in select.find_all('option')]
        element_info = {
            'type': 'select',
            'name': select.get('name', ''),
            'selector': generate_selector(select),
            'options': options,
            'attributes': dict(select.attrs)
        }
        elements.append(element_info)
    
    return elements


def get_element_text(element) -> str:
    """
    Extract visible text from an element.
    
    Args:
        element: BeautifulSoup element
        
    Returns:
        Cleaned text content
    """
    text = element.get_text(strip=True)
    # Fallback to aria-label or title if no text
    if not text:
        text = element.get('aria-label', '') or element.get('title', '')
    return text[:100]  # Limit length


def generate_selector(element) -> str:
    """
    Generate a robust CSS selector for an element that works with modern CSS frameworks.
    
    Args:
        element: BeautifulSoup element
        
    Returns:
        CSS selector string that works with Playwright
    """
    # Try ID first (most reliable)
    if element.get('id'):
        return f"#{element['id']}"
    
    # Try data-testid or other test attributes (very reliable)
    for attr, value in element.attrs.items():
        if attr in ['data-testid', 'data-test', 'data-cy']:
            return f"[{attr}='{value}']"
    
    # Try name attribute (reliable for form elements)
    if element.get('name'):
        return f"{element.name}[name='{element['name']}']"
    
    # For elements with text content, try text-based selectors first
    text = get_element_text(element)
    if text and len(text.strip()) > 0 and len(text.strip()) < 50:
        # Clean text for selector
        clean_text = text.strip().replace('"', '\\"')
        if element.name == 'button':
            return f'button:has-text("{clean_text}")'
        elif element.name == 'a':
            return f'a:has-text("{clean_text}")'
        elif element.name in ['input'] and element.get('type') in ['button', 'submit']:
            return f'input[value="{clean_text}"]'
    
    # Handle classes with attribute selectors (safer for special characters)
    classes = element.get('class', [])
    if classes:
        # Use the first few distinctive classes with attribute selector
        distinctive_classes = []
        for cls in classes[:3]:  # Limit to first 3 classes to avoid overly complex selectors
            if len(cls) > 2 and not cls.startswith('text-') and not cls.startswith('font-'):
                distinctive_classes.append(cls)
        
        if distinctive_classes:
            # Use attribute selector to handle special characters safely
            class_selectors = [f'[class*="{cls}"]' for cls in distinctive_classes[:2]]
            return f"{element.name}{'.'.join(class_selectors)}"
    
    # Try other data attributes
    for attr, value in element.attrs.items():
        if attr.startswith('data-') and len(str(value)) < 50:
            return f"{element.name}[{attr}='{value}']"
    
    # Try role attribute
    if element.get('role'):
        return f"[role='{element['role']}']"
    
    # Try aria-label
    if element.get('aria-label'):
        return f"[aria-label='{element['aria-label']}']"
    
    # Try href for links
    if element.name == 'a' and element.get('href'):
        href = element.get('href')
        if not href.startswith('javascript:') and len(href) < 100:
            return f"a[href='{href}']"
    
    # Try type for inputs
    if element.name == 'input' and element.get('type'):
        input_type = element.get('type')
        placeholder = element.get('placeholder', '')
        if placeholder:
            return f"input[type='{input_type}'][placeholder='{placeholder[:30]}']"
        return f"input[type='{input_type}']"
    
    # Fallback to tag name with position (last resort)
    return element.name


def extract_page_info(html_content: str, url: str) -> Dict[str, Any]:
    """
    Extract general page information for analysis.
    
    Args:
        html_content: Raw HTML content
        url: Current page URL
        
    Returns:
        Dictionary with page information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title = soup.find('title')
    title_text = title.get_text(strip=True) if title else ''
    
    # Extract headings
    headings = []
    for tag in ['h1', 'h2', 'h3']:
        for heading in soup.find_all(tag):
            headings.append(get_element_text(heading))
    
    # Extract error indicators
    error_indicators = check_for_errors(html_content, url)
    
    # Extract forms
    forms = []
    for form in soup.find_all('form'):
        form_info = {
            'action': form.get('action', ''),
            'method': form.get('method', 'get'),
            'inputs': len(form.find_all(['input', 'textarea', 'select']))
        }
        forms.append(form_info)
    
    return {
        'title': title_text,
        'url': url,
        'headings': headings[:5],  # First 5 headings
        'forms': forms,
        'error_indicators': error_indicators,
        'has_nav': bool(soup.find(['nav', '[role="navigation"]'])),
        'has_footer': bool(soup.find('footer')),
        'meta_description': get_meta_description(soup)
    }


def get_meta_description(soup: BeautifulSoup) -> str:
    """Extract meta description from page."""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    return meta_desc.get('content', '') if meta_desc else ''


def check_for_errors(html_content: str, url: str) -> List[str]:
    """
    Check for common error indicators in the page.
    
    Args:
        html_content: Raw HTML content
        url: Current page URL
        
    Returns:
        List of detected error indicators
    """
    errors = []
    content_lower = html_content.lower()
    
    # Common error patterns
    error_patterns = [
        r'404.*not found',
        r'500.*internal server error',
        r'403.*forbidden',
        r'401.*unauthorized',
        r'error.*occurred',
        r'something went wrong',
        r'page not found',
        r'access denied',
        r'server error',
        r'database error',
        r'connection failed'
    ]
    
    for pattern in error_patterns:
        if re.search(pattern, content_lower):
            errors.append(f"Error pattern detected: {pattern}")
    
    # Check URL for error indicators
    if any(error_code in url for error_code in ['404', '500', '403', '401']):
        errors.append(f"Error code in URL: {url}")
    
    return errors


def sanitize_input_value(input_type: str, placeholder: str = "") -> str:
    """
    Generate appropriate test values for different input types.
    
    Args:
        input_type: Type of input field
        placeholder: Placeholder text for hints
        
    Returns:
        Test value string
    """
    test_values = {
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'text': 'Test Input',
        'search': 'test search',
        'tel': '+1234567890',
        'url': 'https://example.com',
        'number': '123'
    }
    
    # Use placeholder as hint if available
    if placeholder:
        placeholder_lower = placeholder.lower()
        if 'email' in placeholder_lower:
            return 'test@example.com'
        elif 'phone' in placeholder_lower or 'tel' in placeholder_lower:
            return '+1234567890'
        elif 'name' in placeholder_lower:
            return 'Test User'
        elif 'password' in placeholder_lower:
            return 'TestPassword123!'
    
    return test_values.get(input_type, 'Test Input')


def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs belong to the same domain.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if same domain, False otherwise
    """
    try:
        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc
        return domain1 == domain2
    except Exception:
        return False


def truncate_html_for_llm(html_content: str, max_length: int = 8000) -> str:
    """
    Truncate HTML content for LLM processing while preserving structure.
    
    Args:
        html_content: Raw HTML content
        max_length: Maximum character length
        
    Returns:
        Truncated HTML content
    """
    if len(html_content) <= max_length:
        return html_content
    
    # Try to preserve meaningful content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove less important elements
    for tag in soup.find_all(['script', 'style', 'noscript', 'meta', 'link']):
        tag.decompose()
    
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
        comment.extract()
    
    truncated = str(soup)
    
    if len(truncated) > max_length:
        return truncated[:max_length] + "... [truncated]"
    
    return truncated 