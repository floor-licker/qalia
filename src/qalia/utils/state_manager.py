"""
State Management Utility

Manages page state tracking, fingerprinting, and state transition monitoring
for comprehensive website exploration state analysis.
"""

import hashlib
import logging
import time
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class PageState:
    """Represents a unique page state."""
    state_hash: str
    url: str
    content_hash: str
    timestamp: float
    elements_count: int
    interactive_elements: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateTransition:
    """Represents a transition between page states."""
    from_state: str
    to_state: str
    from_url: str
    to_url: str
    trigger_action: Dict[str, Any]
    timestamp: float
    duration: float


class StateManager:
    """
    Manages page state tracking and transitions for exploration analysis.
    
    Provides state fingerprinting, transition tracking, and comprehensive
    state analysis for identifying unique application states.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        
        # State tracking
        self.discovered_states: Dict[str, PageState] = {}
        self.state_transitions: List[StateTransition] = []
        self.current_state: Optional[str] = None
        
        # State fingerprinting
        self.state_fingerprints: Set[str] = set()
        self.url_to_states: Dict[str, Set[str]] = {}
        
        # State analysis
        self.state_visit_counts: Dict[str, int] = {}
        self.state_first_seen: Dict[str, float] = {}
        
        logger.info(f"🎯 State manager initialized for domain: {self.domain}")
    
    async def capture_page_state(self, page, page_content: str = None, 
                               interactive_elements: List[Dict[str, Any]] = None) -> str:
        """
        Capture and fingerprint current page state.
        
        Args:
            page: Playwright page instance
            page_content: HTML content (will fetch if not provided)
            interactive_elements: List of interactive elements (will extract if not provided)
            
        Returns:
            State hash identifier
        """
        try:
            url = page.url
            
            # Get page content
            if page_content is None:
                page_content = await page.content()
            
            # Generate content hash
            content_hash = self._generate_content_hash(page_content)
            
            # Generate comprehensive state hash
            state_hash = await self._generate_state_hash(page, page_content, interactive_elements)
            
            # Check if this is a new state
            if state_hash not in self.discovered_states:
                # Extract interactive elements if not provided
                if interactive_elements is None:
                    interactive_elements = await self._extract_state_elements(page)
                
                # Create new state record
                page_state = PageState(
                    state_hash=state_hash,
                    url=url,
                    content_hash=content_hash,
                    timestamp=time.time(),
                    elements_count=len(interactive_elements),
                    interactive_elements=interactive_elements,
                    metadata=await self._extract_state_metadata(page)
                )
                
                self.discovered_states[state_hash] = page_state
                self.state_fingerprints.add(state_hash)
                self.state_first_seen[state_hash] = time.time()
                
                # Update URL to states mapping
                if url not in self.url_to_states:
                    self.url_to_states[url] = set()
                self.url_to_states[url].add(state_hash)
                
                logger.info(f"🆕 New state discovered: {state_hash} ({len(interactive_elements)} elements)")
            
            # Update visit count
            self.state_visit_counts[state_hash] = self.state_visit_counts.get(state_hash, 0) + 1
            
            # Record state transition if we had a previous state
            if self.current_state and self.current_state != state_hash:
                await self._record_state_transition(self.current_state, state_hash, url)
            
            self.current_state = state_hash
            return state_hash
            
        except Exception as e:
            logger.error(f"Error capturing page state: {e}")
            return self._generate_fallback_hash(page.url if page else "unknown")
    
    async def _generate_state_hash(self, page, content: str, 
                                 elements: List[Dict[str, Any]] = None) -> str:
        """Generate comprehensive state hash using multiple factors."""
        try:
            # Base factors
            url = page.url
            content_hash = self._generate_content_hash(content)
            
            # URL factors
            url_parts = f"{urlparse(url).path}|{urlparse(url).query}"
            
            # Element factors
            if elements:
                element_signature = self._generate_element_signature(elements)
            else:
                element_signature = "no_elements"
            
            # DOM structure factors
            dom_signature = await self._get_dom_signature(page)
            
            # Combine all factors
            state_data = f"{url_parts}|{content_hash[:8]}|{element_signature}|{dom_signature}"
            
            return hashlib.md5(state_data.encode()).hexdigest()[:12]
            
        except Exception as e:
            logger.debug(f"Error generating state hash: {e}")
            return self._generate_fallback_hash(url)
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash from page content."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_element_signature(self, elements: List[Dict[str, Any]]) -> str:
        """Generate signature from interactive elements."""
        # Create signature from element types and counts
        element_counts = {}
        for element in elements:
            elem_type = element.get('type', 'unknown')
            element_counts[elem_type] = element_counts.get(elem_type, 0) + 1
        
        # Sort for consistency
        sorted_counts = sorted(element_counts.items())
        signature = "|".join([f"{t}:{c}" for t, c in sorted_counts])
        
        return hashlib.md5(signature.encode()).hexdigest()[:8]
    
    async def _get_dom_signature(self, page) -> str:
        """Get DOM structure signature."""
        try:
            # JavaScript to get DOM signature
            js_code = """
            () => {
                const tags = Array.from(document.querySelectorAll('*'))
                    .map(el => el.tagName.toLowerCase())
                    .reduce((acc, tag) => {
                        acc[tag] = (acc[tag] || 0) + 1;
                        return acc;
                    }, {});
                
                const sortedTags = Object.keys(tags).sort()
                    .map(tag => `${tag}:${tags[tag]}`)
                    .join('|');
                
                return sortedTags;
            }
            """
            
            dom_data = await page.evaluate(js_code)
            return hashlib.md5(dom_data.encode()).hexdigest()[:8]
            
        except Exception as e:
            logger.debug(f"Error getting DOM signature: {e}")
            return "unknown_dom"
    
    async def _extract_state_elements(self, page) -> List[Dict[str, Any]]:
        """Extract basic interactive elements for state analysis."""
        try:
            elements = []
            
            # Get basic interactive element counts
            button_count = await page.locator('button, input[type="button"], input[type="submit"]').count()
            link_count = await page.locator('a[href]').count()
            input_count = await page.locator('input, textarea').count()
            
            return [
                {'type': 'button', 'count': button_count},
                {'type': 'link', 'count': link_count},
                {'type': 'input', 'count': input_count}
            ]
            
        except Exception as e:
            logger.debug(f"Error extracting state elements: {e}")
            return []
    
    async def _extract_state_metadata(self, page) -> Dict[str, Any]:
        """Extract metadata about page state."""
        try:
            metadata = {
                'title': await page.title(),
                'url': page.url,
                'viewport': page.viewport_size,
                'timestamp': time.time()
            }
            
            # Try to get additional metadata
            try:
                # Get page load state
                metadata['load_state'] = await page.evaluate('document.readyState')
                
                # Get scroll position
                scroll_info = await page.evaluate('''
                    () => ({
                        scrollTop: window.pageYOffset || document.documentElement.scrollTop,
                        scrollLeft: window.pageXOffset || document.documentElement.scrollLeft,
                        scrollHeight: document.documentElement.scrollHeight,
                        clientHeight: document.documentElement.clientHeight
                    })
                ''')
                metadata['scroll_info'] = scroll_info
                
            except:
                pass  # Metadata extraction is optional
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Error extracting state metadata: {e}")
            return {}
    
    def _generate_fallback_hash(self, url: str) -> str:
        """Generate deterministic fallback hash when other methods fail."""
        # Use URL + a constant to ensure deterministic hashing for same URL
        # This prevents the timestamp-based issue that creates different hashes for same state
        fallback_data = f"{url}|FALLBACK_STATE_MARKER"
        return hashlib.md5(fallback_data.encode()).hexdigest()[:12]
    
    async def _record_state_transition(self, from_state: str, to_state: str, to_url: str) -> None:
        """Record a state transition."""
        try:
            from_url = self.discovered_states[from_state].url if from_state in self.discovered_states else "unknown"
            
            transition = StateTransition(
                from_state=from_state,
                to_state=to_state,
                from_url=from_url,
                to_url=to_url,
                trigger_action={},  # Would be filled by caller with action details
                timestamp=time.time(),
                duration=0  # Would be calculated by caller
            )
            
            self.state_transitions.append(transition)
            
            logger.info(f"🔄 State transition: {from_state} → {to_state}")
            
        except Exception as e:
            logger.debug(f"Error recording state transition: {e}")
    
    def record_action_triggered_transition(self, from_state: str, to_state: str, 
                                         action: Dict[str, Any], duration: float) -> None:
        """Record a transition triggered by a specific action."""
        if self.state_transitions:
            # Update the last transition with action details
            last_transition = self.state_transitions[-1]
            if last_transition.from_state == from_state and last_transition.to_state == to_state:
                last_transition.trigger_action = action
                last_transition.duration = duration
    
    def is_new_state(self, state_hash: str) -> bool:
        """Check if state hash represents a new state."""
        return state_hash not in self.discovered_states
    
    def get_state_info(self, state_hash: str) -> Optional[PageState]:
        """Get information about a specific state."""
        return self.discovered_states.get(state_hash)
    
    def get_states_for_url(self, url: str) -> Set[str]:
        """Get all state hashes for a specific URL."""
        return self.url_to_states.get(url, set())
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state analysis summary."""
        total_states = len(self.discovered_states)
        total_transitions = len(self.state_transitions)
        unique_urls = len(self.url_to_states)
        
        # Most visited states
        most_visited = sorted(
            self.state_visit_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Recent states
        recent_states = sorted(
            self.discovered_states.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )[:5]
        
        # URLs with multiple states (complex interactions)
        complex_urls = {
            url: len(states) for url, states in self.url_to_states.items()
            if len(states) > 1
        }
        
        return {
            'total_states_discovered': total_states,
            'total_state_transitions': total_transitions,
            'unique_urls_visited': unique_urls,
            'complex_urls': len(complex_urls),
            'current_state': self.current_state,
            'most_visited_states': [
                {
                    'state_hash': state_hash,
                    'visit_count': count,
                    'url': self.discovered_states[state_hash].url if state_hash in self.discovered_states else 'unknown'
                }
                for state_hash, count in most_visited
            ],
            'recent_states': [
                {
                    'state_hash': state.state_hash,
                    'url': state.url,
                    'elements_count': state.elements_count,
                    'timestamp': state.timestamp
                }
                for state in recent_states
            ],
            'complex_urls_detail': complex_urls
        }
    
    def get_state_graph_data(self) -> Dict[str, Any]:
        """Get data for state transition graph visualization."""
        nodes = []
        edges = []
        
        # Create nodes for each state
        for state_hash, state in self.discovered_states.items():
            nodes.append({
                'id': state_hash,
                'label': f"{state_hash[:8]}",
                'url': state.url,
                'elements_count': state.elements_count,
                'visit_count': self.state_visit_counts.get(state_hash, 0),
                'timestamp': state.timestamp
            })
        
        # Create edges for transitions
        transition_counts = {}
        for transition in self.state_transitions:
            edge_key = f"{transition.from_state}->{transition.to_state}"
            transition_counts[edge_key] = transition_counts.get(edge_key, 0) + 1
        
        for edge_key, count in transition_counts.items():
            from_state, to_state = edge_key.split('->')
            edges.append({
                'from': from_state,
                'to': to_state,
                'count': count,
                'label': f"{count}"
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'total_transitions': len(self.state_transitions)
            }
        }
    
    def export_states_to_dict(self) -> Dict[str, Any]:
        """Export all state data to dictionary format."""
        return {
            'discovered_states': {
                state_hash: {
                    'state_hash': state.state_hash,
                    'url': state.url,
                    'content_hash': state.content_hash,
                    'timestamp': state.timestamp,
                    'elements_count': state.elements_count,
                    'interactive_elements': state.interactive_elements,
                    'metadata': state.metadata
                }
                for state_hash, state in self.discovered_states.items()
            },
            'state_transitions': [
                {
                    'from_state': t.from_state,
                    'to_state': t.to_state,
                    'from_url': t.from_url,
                    'to_url': t.to_url,
                    'trigger_action': t.trigger_action,
                    'timestamp': t.timestamp,
                    'duration': t.duration
                }
                for t in self.state_transitions
            ],
            'url_to_states': {
                url: list(states) for url, states in self.url_to_states.items()
            },
            'state_visit_counts': self.state_visit_counts,
            'summary': self.get_state_summary()
        }
    
    def clear_states(self) -> None:
        """Clear all state tracking data."""
        self.discovered_states.clear()
        self.state_transitions.clear()
        self.state_fingerprints.clear()
        self.url_to_states.clear()
        self.state_visit_counts.clear()
        self.state_first_seen.clear()
        self.current_state = None
        
        logger.info("🧹 All state data cleared") 