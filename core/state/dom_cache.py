#!/usr/bin/env python3
"""
DOM Operation Cache System

Eliminates redundant HTML extractions and element scanning operations.
"""

import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DOMSnapshot:
    """Cached snapshot of DOM state and extracted data."""
    html_content: str
    html_hash: str
    page_info: Dict[str, Any]
    interactive_elements: List[Dict[str, Any]]
    modal_state: Dict[str, Any]
    timestamp: float
    url: str
    
    def is_stale(self, max_age_seconds: float = 30.0) -> bool:
        """Check if snapshot is stale based on age."""
        return time.time() - self.timestamp > max_age_seconds
    
    def get_age(self) -> float:
        """Get age of snapshot in seconds."""
        return time.time() - self.timestamp


class DOMCache:
    """
    Intelligent caching system for DOM operations.
    
    Eliminates redundant HTML extractions and element scanning by:
    1. Caching DOM snapshots with content-based invalidation
    2. Batching multiple extractions into single DOM reads
    3. Smart invalidation based on action types
    """
    
    def __init__(self):
        self._snapshots: Dict[str, DOMSnapshot] = {}
        self._pending_invalidations: set = set()
        
        # Performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._dom_reads_saved = 0
    
    def _generate_cache_key(self, url: str, context: str = "default") -> str:
        """Generate cache key for URL and context."""
        return f"{url}#{context}"
    
    def _calculate_html_hash(self, html_content: str) -> str:
        """Calculate hash of HTML content for change detection."""
        # Focus on content that matters for element detection
        # Remove timestamps, dynamic IDs that don't affect functionality
        normalized = html_content.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    async def get_dom_snapshot(self, page, url: str, context: str = "default", 
                              force_refresh: bool = False) -> DOMSnapshot:
        """
        Get cached DOM snapshot or create new one if needed.
        
        Args:
            page: Playwright page object
            url: Current URL
            context: Context identifier (e.g., 'before_action', 'after_action')
            force_refresh: Force fresh extraction even if cached
            
        Returns:
            DOMSnapshot with all extracted data
        """
        cache_key = self._generate_cache_key(url, context)
        
        # Check if we have a valid cached snapshot
        if not force_refresh and cache_key in self._snapshots:
            snapshot = self._snapshots[cache_key]
            
            # Check if snapshot is still valid
            if not snapshot.is_stale() and cache_key not in self._pending_invalidations:
                logger.debug(f"DOM cache HIT: {cache_key} (age: {snapshot.get_age():.1f}s)")
                self._cache_hits += 1
                return snapshot
        
        # Cache miss - need to extract fresh data
        logger.debug(f"DOM cache MISS: {cache_key} - extracting fresh DOM data")
        self._cache_misses += 1
        
        # Single DOM read with all data we need
        snapshot = await self._extract_full_snapshot(page, url)
        
        # Cache the snapshot
        self._snapshots[cache_key] = snapshot
        
        # Clear any pending invalidation for this key
        self._pending_invalidations.discard(cache_key)
        
        return snapshot
    
    async def _extract_full_snapshot(self, page, url: str) -> DOMSnapshot:
        """
        Extract complete DOM snapshot in a single operation.
        
        This replaces multiple separate calls to:
        - page.content()
        - extract_page_info()
        - extract_interactive_elements()
        - modal detection
        """
        # Single comprehensive DOM extraction
        dom_data = await page.evaluate("""() => {
            // Extract everything we need in one go
            const html = document.documentElement.outerHTML;
            
            // Page info extraction
            const pageInfo = {
                title: document.title || '',
                url: location.href,
                has_nav: !!document.querySelector('nav, [role="navigation"]'),
                has_footer: !!document.querySelector('footer, [role="contentinfo"]'),
                forms: Array.from(document.forms).map(form => ({
                    action: form.action || '',
                    method: form.method || 'GET',
                    fields: form.elements.length
                })),
                headings: Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => h.textContent?.trim() || ''),
                error_indicators: Array.from(document.querySelectorAll('[class*="error"], [class*="alert"], [role="alert"]')).map(el => el.textContent?.trim() || ''),
                loading_indicators: Array.from(document.querySelectorAll('[class*="loading"], [class*="spinner"]')).length > 0
            };
            
            // Interactive elements extraction  
            const interactiveElements = [];
            
            // Buttons
            document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]').forEach((el, index) => {
                if (el.offsetParent !== null) { // Visible elements only
                    interactiveElements.push({
                        type: 'button',
                        text: el.textContent?.trim() || el.value || '',
                        selector: `button:nth-of-type(${index + 1})`,
                        id: el.id || '',
                        class: el.className || '',
                        disabled: el.disabled || false
                    });
                }
            });
            
            // Links
            document.querySelectorAll('a[href]').forEach((el, index) => {
                if (el.offsetParent !== null && el.href) {
                    interactiveElements.push({
                        type: 'link',
                        text: el.textContent?.trim() || '',
                        href: el.href,
                        selector: `a:nth-of-type(${index + 1})`,
                        id: el.id || '',
                        class: el.className || ''
                    });
                }
            });
            
            // Form inputs
            document.querySelectorAll('input, textarea, select').forEach((el, index) => {
                if (el.offsetParent !== null) {
                    interactiveElements.push({
                        type: el.tagName.toLowerCase() === 'select' ? 'select' : 'input',
                        input_type: el.type || 'text',
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        selector: `${el.tagName.toLowerCase()}:nth-of-type(${index + 1})`,
                        id: el.id || '',
                        required: el.required || false,
                        disabled: el.disabled || false
                    });
                }
            });
            
            // Modal detection
            const modalState = {
                has_modal: document.querySelectorAll('[role="dialog"], [aria-modal="true"], .modal:not([style*="display: none"])').length > 0,
                modal_types: Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"]')).map(el => 
                    el.getAttribute('aria-labelledby') || el.className || 'dialog'
                ),
                overlay_present: !!document.querySelector('.modal-overlay, .backdrop, [class*="overlay"]:not([style*="display: none"])'),
                modal_count: document.querySelectorAll('[role="dialog"], [aria-modal="true"]').length
            };
            
            return {
                html,
                pageInfo,
                interactiveElements,
                modalState
            };
        }""")
        
        # Calculate HTML hash for change detection
        html_hash = self._calculate_html_hash(dom_data['html'])
        
        # Import here to avoid circular imports
        from utils import extract_page_info, extract_interactive_elements
        
        # Create snapshot with batched data
        snapshot = DOMSnapshot(
            html_content=dom_data['html'],
            html_hash=html_hash,
            page_info=dom_data['pageInfo'],
            interactive_elements=dom_data['interactiveElements'],
            modal_state=dom_data['modalState'],
            timestamp=time.time(),
            url=url
        )
        
        logger.debug(f"DOM snapshot created: {len(snapshot.interactive_elements)} elements, "
                    f"modal: {snapshot.modal_state['has_modal']}")
        
        return snapshot
    
    def invalidate_cache(self, url: str, context: str = None) -> None:
        """
        Mark cache entries for invalidation.
        
        Args:
            url: URL to invalidate
            context: Specific context to invalidate, or None for all contexts
        """
        if context:
            cache_key = self._generate_cache_key(url, context)
            self._pending_invalidations.add(cache_key)
            logger.debug(f"DOM cache invalidated: {cache_key}")
        else:
            # Invalidate all contexts for this URL
            keys_to_invalidate = [key for key in self._snapshots.keys() if key.startswith(f"{url}#")]
            self._pending_invalidations.update(keys_to_invalidate)
            logger.debug(f"DOM cache invalidated for URL: {url} ({len(keys_to_invalidate)} entries)")
    
    def should_invalidate_after_action(self, action: Dict[str, Any]) -> bool:
        """
        Determine if cache should be invalidated after an action.
        
        Args:
            action: Action that was performed
            
        Returns:
            True if cache should be invalidated
        """
        # Actions that definitely change DOM
        dom_changing_actions = ['click', 'type', 'fill', 'select', 'submit']
        
        action_type = action.get('action', '').lower()
        return action_type in dom_changing_actions
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': hit_rate,
            'dom_reads_saved': self._cache_hits,  # Each hit saves a DOM read
            'cached_snapshots': len(self._snapshots),
            'pending_invalidations': len(self._pending_invalidations)
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._snapshots.clear()
        self._pending_invalidations.clear()
        logger.info("DOM cache cleared")


# Global cache instance
_dom_cache = DOMCache()


def get_dom_cache() -> DOMCache:
    """Get the global DOM cache instance."""
    return _dom_cache 