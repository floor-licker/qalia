"""
State management system to track visited URLs, performed actions, and prevent infinite loops.
Includes persistent site mapping for cross-session knowledge building.
"""

import json
import hashlib
import os
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class StateStore:
    """
    Manages the state of the crawling session to avoid revisiting pages and repeating actions.
    Now includes persistent site mapping across sessions.
    """
    
    def __init__(self, state_file: str = "state_store.json"):
        """
        Initialize the state store.
        
        Args:
            state_file: Path to the JSON file for persisting state
        """
        self.state_file = state_file
        self.visited_urls: Set[str] = set()
        self.performed_actions: List[Dict[str, Any]] = []
        self.page_states: Dict[str, Dict[str, Any]] = {}
        self.session_start = datetime.now().isoformat()
        self.total_actions = 0
        
        # Persistent site mapping
        self.site_maps_dir = "site_maps"
        self.current_site_domain = None
        self.site_map: Dict[str, Any] = {}
        
        self._ensure_site_maps_directory()
        self._load_state()
    
    def _ensure_site_maps_directory(self) -> None:
        """Ensure the site maps directory exists."""
        if not os.path.exists(self.site_maps_dir):
            os.makedirs(self.site_maps_dir)
            logger.info(f"Created site maps directory: {self.site_maps_dir}")
    
    def set_target_site(self, start_url: str) -> None:
        """
        Set the target site and load its persistent mapping.
        
        Args:
            start_url: Starting URL for the exploration
        """
        parsed_url = urlparse(start_url)
        self.current_site_domain = parsed_url.netloc
        
        # Load existing site map if available
        self._load_site_map()
        
        logger.info(f"Target site set to: {self.current_site_domain}")
        if self.site_map:
            logger.info(f"Loaded existing site map with {len(self.site_map.get('pages', {}))} known pages")
    
    def _get_site_map_filename(self) -> str:
        """Get the filename for the current site's map."""
        if not self.current_site_domain:
            return None
        
        # Create safe filename from domain
        safe_domain = "".join(c for c in self.current_site_domain if c.isalnum() or c in ".-_")
        return os.path.join(self.site_maps_dir, f"{safe_domain}_sitemap.json")
    
    def _load_site_map(self) -> None:
        """Load the site map for the current domain."""
        site_map_file = self._get_site_map_filename()
        if not site_map_file or not os.path.exists(site_map_file):
            self.site_map = self._create_empty_site_map()
            return
        
        try:
            with open(site_map_file, 'r') as f:
                self.site_map = json.load(f)
            
            # Validate and migrate old format if needed
            if 'version' not in self.site_map:
                self.site_map = self._migrate_site_map(self.site_map)
            
            logger.info(f"Loaded site map from: {site_map_file}")
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not load site map {site_map_file}: {e}")
            self.site_map = self._create_empty_site_map()
    
    def _save_site_map(self) -> None:
        """Save the current site map."""
        site_map_file = self._get_site_map_filename()
        if not site_map_file:
            return
        
        try:
            self.site_map['last_updated'] = datetime.now().isoformat()
            self.site_map['total_explorations'] = self.site_map.get('total_explorations', 0) + 1
            
            with open(site_map_file, 'w') as f:
                json.dump(self.site_map, f, indent=2)
            
            logger.debug(f"Saved site map to: {site_map_file}")
            
        except Exception as e:
            logger.error(f"Could not save site map {site_map_file}: {e}")
    
    def _create_empty_site_map(self) -> Dict[str, Any]:
        """Create an empty site map structure."""
        return {
            'version': '1.0',
            'domain': self.current_site_domain,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'total_explorations': 0,
            'pages': {},
            'site_structure': {
                'navigation_patterns': [],
                'common_elements': [],
                'form_patterns': [],
                'modal_patterns': []
            },
            'change_tracking': {
                'page_hashes': {},
                'last_change_detected': None
            }
        }
    
    def _migrate_site_map(self, old_map: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate old site map format to current version."""
        new_map = self._create_empty_site_map()
        new_map['pages'] = old_map.get('pages', {})
        return new_map
    
    def has_explored_page_recently(self, url: str, max_age_hours: int = 24) -> bool:
        """
        Check if a page has been explored recently.
        
        Args:
            url: URL to check
            max_age_hours: Maximum age in hours to consider "recent"
            
        Returns:
            True if page was explored recently, False otherwise
        """
        normalized_url = url.split('#')[0]
        page_data = self.site_map.get('pages', {}).get(normalized_url)
        
        if not page_data:
            return False
        
        last_explored = page_data.get('last_explored')
        if not last_explored:
            return False
        
        try:
            last_explored_dt = datetime.fromisoformat(last_explored)
            age = datetime.now() - last_explored_dt
            return age < timedelta(hours=max_age_hours)
        except:
            return False
    
    def get_known_pages(self) -> List[str]:
        """Get list of all known pages for the current site."""
        return list(self.site_map.get('pages', {}).keys())
    
    def get_unexplored_elements(self, url: str) -> List[Dict[str, Any]]:
        """
        Get interactive elements that haven't been tested on a page.
        
        Args:
            url: URL to check
            
        Returns:
            List of element information for unexplored elements
        """
        normalized_url = url.split('#')[0]
        page_data = self.site_map.get('pages', {}).get(normalized_url, {})
        explored_elements = set(page_data.get('explored_elements', []))
        
        # This would be populated during page analysis
        all_elements = page_data.get('all_elements', [])
        
        unexplored = []
        for element in all_elements:
            element_sig = self._generate_element_signature(element)
            if element_sig not in explored_elements:
                unexplored.append(element)
        
        return unexplored
    
    def record_page_exploration(self, url: str, page_info: Dict[str, Any], 
                              interactive_elements: List[Dict[str, Any]]) -> None:
        """
        Record comprehensive information about a page exploration.
        
        Args:
            url: URL that was explored
            page_info: Page information extracted
            interactive_elements: List of interactive elements found
        """
        normalized_url = url.split('#')[0]
        
        # Calculate page content hash for change detection
        page_hash = self._calculate_page_hash(page_info)
        
        # Check if page has changed since last exploration
        old_hash = self.site_map.get('change_tracking', {}).get('page_hashes', {}).get(normalized_url)
        page_changed = old_hash != page_hash
        
        if page_changed and old_hash:
            logger.info(f"Page content changed detected: {normalized_url}")
            self.site_map['change_tracking']['last_change_detected'] = datetime.now().isoformat()
        
        # Update page data
        page_data = {
            'url': normalized_url,
            'title': page_info.get('title', ''),
            'last_explored': datetime.now().isoformat(),
            'exploration_count': self.site_map.get('pages', {}).get(normalized_url, {}).get('exploration_count', 0) + 1,
            'page_hash': page_hash,
            'page_changed': page_changed,
            'all_elements': interactive_elements,
            'explored_elements': self.site_map.get('pages', {}).get(normalized_url, {}).get('explored_elements', []),
            'navigation_links': [elem['href'] for elem in interactive_elements if elem['type'] == 'link'],
            'forms': page_info.get('forms', []),
            'has_modals': False,  # Will be updated if modals are detected
            'page_health': {}  # Will be populated by evaluator
        }
        
        self.site_map.setdefault('pages', {})[normalized_url] = page_data
        
        # Update change tracking
        self.site_map.setdefault('change_tracking', {}).setdefault('page_hashes', {})[normalized_url] = page_hash
        
        # Also update the session state
        self.mark_url_visited(url, page_info)
        
        # Save the updated site map
        self._save_site_map()
    
    def record_element_exploration(self, url: str, element: Dict[str, Any], 
                                 action_result: Dict[str, Any]) -> None:
        """
        Record that an element was explored/tested.
        
        Args:
            url: URL where element was tested
            element: Element information
            action_result: Result of testing the element
        """
        normalized_url = url.split('#')[0]
        element_sig = self._generate_element_signature(element)
        
        # Add to explored elements
        page_data = self.site_map.setdefault('pages', {}).setdefault(normalized_url, {})
        explored_elements = set(page_data.get('explored_elements', []))
        explored_elements.add(element_sig)
        page_data['explored_elements'] = list(explored_elements)
        
        # Update modal detection if applicable
        if action_result.get('after_state', {}).get('modal_present', {}).get('has_modal'):
            page_data['has_modals'] = True
            
            # Record modal pattern
            modal_pattern = {
                'trigger_element': element_sig,
                'modal_type': action_result.get('after_state', {}).get('modal_present', {}).get('modal_types', []),
                'detected_at': datetime.now().isoformat()
            }
            self.site_map.setdefault('site_structure', {}).setdefault('modal_patterns', []).append(modal_pattern)
        
        self._save_site_map()
    
    def _generate_element_signature(self, element: Dict[str, Any]) -> str:
        """Generate a unique signature for an interactive element."""
        signature_data = {
            'type': element.get('type', ''),
            'selector': element.get('selector', ''),
            'text': element.get('text', '')[:50],  # Limit text length
        }
        
        # Add specific attributes based on element type
        if element.get('type') == 'link':
            signature_data['href'] = element.get('href', '')
        elif element.get('type') == 'input':
            signature_data['input_type'] = element.get('input_type', '')
            signature_data['name'] = element.get('name', '')
        
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()[:12]  # Short hash
    
    def _calculate_page_hash(self, page_info: Dict[str, Any]) -> str:
        """Calculate a hash of page content for change detection."""
        # Use key content that would change if page structure changes
        content_data = {
            'title': page_info.get('title', ''),
            'headings': page_info.get('headings', []),
            'forms_count': len(page_info.get('forms', [])),
            'has_nav': page_info.get('has_nav', False),
            'has_footer': page_info.get('has_footer', False)
        }
        
        content_str = json.dumps(content_data, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def get_exploration_strategy(self, url: str) -> Dict[str, Any]:
        """
        Get recommended exploration strategy for a URL based on historical data.
        This now focuses on comparison and change detection rather than skipping exploration.
        
        Args:
            url: URL to get strategy for
            
        Returns:
            Dictionary with exploration recommendations
        """
        normalized_url = url.split('#')[0]
        page_data = self.site_map.get('pages', {}).get(normalized_url, {})
        
        strategy = {
            'is_known_page': bool(page_data),
            'has_changed': page_data.get('page_changed', True),
            'last_explored': page_data.get('last_explored'),
            'exploration_count': page_data.get('exploration_count', 0),
            'has_modals': page_data.get('has_modals', False),
            'unexplored_elements_count': len(self.get_unexplored_elements(url)),
            'previous_elements_count': len(page_data.get('all_elements', [])),
            'previous_explored_count': len(page_data.get('explored_elements', [])),
            'recommendation': 'full_exploration'  # Default: always explore
        }
        
        # ALWAYS EXPLORE - but provide context for comparison
        if strategy['is_known_page']:
            if strategy['has_changed']:
                strategy['recommendation'] = 'discovery_exploration'  # Force discovery
                strategy['context'] = 'DEMO: Forced discovery mode to showcase state-based console tracking'
            elif strategy['unexplored_elements_count'] > 0:
                strategy['recommendation'] = 'discovery_exploration'  # Force discovery
                strategy['context'] = f'DEMO: Forced discovery mode - testing {strategy["unexplored_elements_count"]} elements'
            else:
                strategy['recommendation'] = 'discovery_exploration'  # Force discovery
                strategy['context'] = 'DEMO: Forced discovery mode for state-based console tracking demonstration'
        else:
            strategy['recommendation'] = 'discovery_exploration'
            strategy['context'] = 'First-time exploration of unknown page'
        
        return strategy

    def get_page_exploration_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed exploration data for a specific page.
        
        Args:
            url: URL to get exploration data for
            
        Returns:
            Dictionary with page exploration data or None if not found
        """
        normalized_url = url.split('#')[0]
        return self.site_map.get('pages', {}).get(normalized_url)

    def get_site_exploration_summary(self) -> Dict[str, Any]:
        """Get a summary of the site exploration progress."""
        pages = self.site_map.get('pages', {})
        
        total_pages = len(pages)
        total_elements = sum(len(page.get('all_elements', [])) for page in pages.values())
        explored_elements = sum(len(page.get('explored_elements', [])) for page in pages.values())
        pages_with_modals = sum(1 for page in pages.values() if page.get('has_modals', False))
        
        return {
            'domain': self.current_site_domain,
            'total_pages_discovered': total_pages,
            'total_elements_discovered': total_elements,
            'total_elements_explored': explored_elements,
            'exploration_percentage': (explored_elements / total_elements * 100) if total_elements > 0 else 0,
            'pages_with_modals': pages_with_modals,
            'last_updated': self.site_map.get('last_updated'),
            'total_explorations': self.site_map.get('total_explorations', 0)
        }
    
    def _load_state(self) -> None:
        """Load state from the JSON file if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    
                self.visited_urls = set(data.get('visited_urls', []))
                self.performed_actions = data.get('performed_actions', [])
                self.page_states = data.get('page_states', {})
                self.total_actions = data.get('total_actions', 0)
                
                logger.info(f"Loaded state: {len(self.visited_urls)} URLs, {len(self.performed_actions)} actions")
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load state file {self.state_file}: {e}")
                self._reset_state()
        else:
            logger.info("No existing state file found, starting fresh")
    
    def _save_state(self) -> None:
        """Save current state to the JSON file."""
        try:
            data = {
                'visited_urls': list(self.visited_urls),
                'performed_actions': self.performed_actions,
                'page_states': self.page_states,
                'total_actions': self.total_actions,
                'session_start': self.session_start,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save state file {self.state_file}: {e}")
    
    def _reset_state(self) -> None:
        """Reset all state to empty."""
        self.visited_urls = set()
        self.performed_actions = []
        self.page_states = {}
        self.total_actions = 0
        self.session_start = datetime.now().isoformat()
    
    def has_visited_url(self, url: str) -> bool:
        """
        Check if a URL has been visited before.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL has been visited, False otherwise
        """
        # Normalize URL by removing fragment
        normalized_url = url.split('#')[0]
        return normalized_url in self.visited_urls
    
    def mark_url_visited(self, url: str, page_info: Dict[str, Any] = None) -> None:
        """
        Mark a URL as visited and optionally store page information.
        
        Args:
            url: URL that was visited
            page_info: Optional page information to store
        """
        normalized_url = url.split('#')[0]
        self.visited_urls.add(normalized_url)
        
        if page_info:
            self.page_states[normalized_url] = {
                'page_info': page_info,
                'visited_at': datetime.now().isoformat()
            }
        
        self._save_state()
        logger.debug(f"Marked URL as visited: {normalized_url}")
    
    def has_performed_action(self, action: Dict[str, Any], url: str) -> bool:
        """
        Check if a specific action has been performed on a page.
        
        Args:
            action: Action dictionary containing type, target, value
            url: URL where action would be performed
            
        Returns:
            True if action has been performed, False otherwise
        """
        action_signature = self._generate_action_signature(action, url)
        
        for performed_action in self.performed_actions:
            if performed_action.get('signature') == action_signature:
                return True
        
        return False
    
    def record_action(self, action: Dict[str, Any], url: str, result: Dict[str, Any] = None) -> None:
        """
        Record that an action was performed.
        
        Args:
            action: Action dictionary containing type, target, value
            url: URL where action was performed
            result: Optional result of the action
        """
        action_record = {
            'action': action.copy(),
            'url': url,
            'signature': self._generate_action_signature(action, url),
            'timestamp': datetime.now().isoformat(),
            'result': result or {}
        }
        
        self.performed_actions.append(action_record)
        self.total_actions += 1
        self._save_state()
        
        logger.debug(f"Recorded action: {action['action']} on {action.get('target', 'unknown')} at {url}")
    
    def _generate_action_signature(self, action: Dict[str, Any], url: str) -> str:
        """
        Generate a unique signature for an action on a specific page.
        
        Args:
            action: Action dictionary
            url: URL where action is performed
            
        Returns:
            Unique signature string
        """
        # Create a canonical representation of the action
        canonical_action = {
            'type': action.get('action', ''),
            'target': action.get('target', ''),
            'url': url.split('#')[0]  # Remove fragment
        }
        
        # Include value for input actions only
        if action.get('action') in ['type', 'fill']:
            canonical_action['value'] = action.get('value', '')
        
        # Create hash of the canonical representation
        action_str = json.dumps(canonical_action, sort_keys=True)
        return hashlib.md5(action_str.encode()).hexdigest()
    
    def get_page_state(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get stored page state information.
        
        Args:
            url: URL to get state for
            
        Returns:
            Page state dictionary or None if not found
        """
        normalized_url = url.split('#')[0]
        return self.page_states.get(normalized_url)
    
    def get_action_history(self, url: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get history of performed actions.
        
        Args:
            url: Optional URL to filter actions by
            limit: Maximum number of actions to return
            
        Returns:
            List of action records
        """
        actions = self.performed_actions
        
        if url:
            normalized_url = url.split('#')[0]
            actions = [a for a in actions if a['url'].split('#')[0] == normalized_url]
        
        return actions[-limit:] if limit else actions
    
    def should_continue_exploring(self, max_total_actions: int = 1000, max_actions_per_page: int = 50, current_url: str = None) -> bool:
        """
        Determine if exploration should continue based on intelligent completion criteria.
        
        Args:
            max_total_actions: Safety limit for total actions (high value)
            max_actions_per_page: Safety limit for actions per page (high value)
            current_url: Current URL to check page-specific limits
            
        Returns:
            True if exploration should continue, False otherwise
        """
        # Safety limits (should be high enough to not interfere with natural completion)
        if self.total_actions >= max_total_actions:
            logger.info(f"Reached safety limit for total actions: {max_total_actions}")
            return False
        
        # Check per-page safety limit
        if current_url:
            page_actions = len(self.get_action_history(current_url, limit=None))
            if page_actions >= max_actions_per_page:
                logger.info(f"Reached safety limit for actions per page: {max_actions_per_page}")
                return False
        
        # INTELLIGENT COMPLETION: Check if we have meaningful work left to do
        site_summary = self.get_site_exploration_summary()
        
        # Continue if exploration percentage is low (less than 80% of elements explored)
        if site_summary['exploration_percentage'] < 80.0:
            logger.debug(f"Continuing exploration: {site_summary['exploration_percentage']:.1f}% elements explored")
            return True
        
        # Continue if there are known pages with unexplored elements
        known_pages = self.get_known_pages()
        for page_url in known_pages:
            unexplored = len(self.get_unexplored_elements(page_url))
            if unexplored > 0:
                logger.debug(f"Continuing exploration: {page_url} has {unexplored} unexplored elements")
        return True
        
        # If we get here, exploration is likely complete
        logger.info(f"Natural exploration completion: {site_summary['exploration_percentage']:.1f}% elements explored across {len(known_pages)} pages")
        return False
    
    def get_unvisited_links(self, discovered_links: List[str]) -> List[str]:
        """
        Filter out already visited links from a list of discovered links.
        
        Args:
            discovered_links: List of URLs discovered on the current page
            
        Returns:
            List of unvisited URLs
        """
        unvisited = []
        for link in discovered_links:
            if not self.has_visited_url(link):
                unvisited.append(link)
        
        return unvisited
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current crawling session.
        
        Returns:
            Dictionary with session statistics
        """
        return {
            'visited_urls_count': len(self.visited_urls),
            'total_actions': self.total_actions,
            'session_start': self.session_start,
            'pages_with_errors': len([
                url for url, state in self.page_states.items()
                if state.get('page_info', {}).get('error_indicators')
            ]),
            'most_recent_actions': self.performed_actions[-5:] if self.performed_actions else []
        }
    
    def clear_state(self) -> None:
        """
        Clear all state and delete the state file.
        """
        self._reset_state()
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        logger.info("State cleared")
    
    def export_session_report(self, output_file: str = None) -> str:
        """
        Export a detailed session report.
        
        Args:
            output_file: Optional file path to save report
            
        Returns:
            Report content as string
        """
        stats = self.get_stats()
        
        report_lines = [
            "=== QA Automation Session Report ===",
            f"Session Start: {self.session_start}",
            f"Total URLs Visited: {stats['visited_urls_count']}",
            f"Total Actions Performed: {stats['total_actions']}",
            f"Pages with Errors: {stats['pages_with_errors']}",
            "",
            "=== Visited URLs ===",
        ]
        
        for url in sorted(self.visited_urls):
            state = self.page_states.get(url, {})
            page_info = state.get('page_info', {})
            error_count = len(page_info.get('error_indicators', []))
            
            report_lines.append(f"- {url}")
            if error_count > 0:
                report_lines.append(f"  └── ⚠️  {error_count} error(s) detected")
        
        report_lines.extend([
            "",
            "=== Recent Actions ===",
        ])
        
        for action in self.performed_actions[-10:]:
            timestamp = action['timestamp']
            action_type = action['action'].get('action', 'unknown')
            target = action['action'].get('target', 'unknown')
            url = action['url']
            
            report_lines.append(f"- {timestamp}: {action_type} on {target} at {url}")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            logger.info(f"Session report saved to: {output_file}")
        
        return report_content 