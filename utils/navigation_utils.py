"""
Navigation Utilities

Provides URL handling, domain checking, and navigation utilities
for website exploration.
"""

import logging
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional

logger = logging.getLogger(__name__)


class NavigationUtils:
    """
    Utilities for URL handling and navigation during website exploration.
    
    Provides domain checking, URL resolution, and navigation helpers.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base URL."""
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc == self.base_domain or parsed_url.netloc == ''
        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")
            return False
    
    def resolve_url(self, url: str) -> str:
        """Resolve relative URL to absolute URL."""
        try:
            return urljoin(self.base_url, url)
        except Exception as e:
            logger.debug(f"Error resolving URL {url}: {e}")
            return url
    
    def is_valid_navigation_url(self, url: str) -> bool:
        """Check if URL is valid for navigation."""
        if not url:
            return False
        
        # Skip javascript: and mailto: links
        if url.startswith(('javascript:', 'mailto:', 'tel:')):
            return False
        
        # Skip anchors
        if url.startswith('#'):
            return False
        
        return True
    
    def clean_url(self, url: str) -> str:
        """Clean URL by removing fragments and unnecessary parameters."""
        try:
            parsed = urlparse(url)
            # Remove fragment (anchor)
            cleaned = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))
            return cleaned
        except:
            return url
    
    def get_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return None 