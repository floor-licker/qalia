"""
Systematic Exploration Strategy

Implements BFS/DFS methodical exploration of all interactive elements.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass 
class SystematicConfig:
    """Configuration for systematic exploration."""
    max_actions_per_page: int = 50
    exploration_depth: int = 3
    breadth_first: bool = True  # True for BFS, False for DFS
    prioritize_forms: bool = True
    skip_external_links: bool = True


class SystematicStrategy:
    """
    Systematic exploration using BFS or DFS approach.
    
    Tests all interactive elements methodically without AI guidance.
    """
    
    def __init__(self, config: SystematicConfig = None):
        self.config = config or SystematicConfig()
        self.element_queue = []
        self.visited_elements = set()
        
    async def explore_page(self, page, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Systematically explore all elements on a page.
        
        Args:
            page: Playwright page object
            elements: List of interactive elements
            
        Returns:
            List of action results
        """
        logger.info(f"🔍 Starting systematic exploration of {len(elements)} elements")
        
        # Add elements to queue based on strategy
        self._populate_queue(elements)
        
        action_results = []
        actions_performed = 0
        
        while (self.element_queue and 
               actions_performed < self.config.max_actions_per_page):
            
            # Get next element based on BFS/DFS
            element = self._get_next_element()
            element_key = self._get_element_key(element)
            
            if element_key in self.visited_elements:
                continue
                
            # Create and execute action
            action = self._create_systematic_action(element)
            if action:
                # This would integrate with ActionExecutor
                logger.info(f"Systematic test: {action.get('type')} on {element.get('tag', 'unknown')}")
                actions_performed += 1
                
            self.visited_elements.add(element_key)
            
        logger.info(f"✅ Systematic exploration completed: {actions_performed} actions")
        return action_results
        
    def _populate_queue(self, elements: List[Dict[str, Any]]):
        """Populate the exploration queue with prioritized elements."""
        prioritized = self._prioritize_elements(elements)
        
        if self.config.breadth_first:
            self.element_queue.extend(prioritized)
        else:
            # For DFS, we'll reverse and use as stack
            self.element_queue.extend(reversed(prioritized))
            
    def _prioritize_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize elements for testing."""
        if not self.config.prioritize_forms:
            return elements
            
        # Prioritize interactive elements
        buttons = [e for e in elements if e.get('tag') == 'button']
        forms = [e for e in elements if e.get('tag') in ['input', 'select', 'textarea']]  
        links = [e for e in elements if e.get('tag') == 'a']
        others = [e for e in elements if e not in buttons + forms + links]
        
        return buttons + forms + links + others
        
    def _get_next_element(self) -> Dict[str, Any]:
        """Get next element based on BFS/DFS strategy."""
        if self.config.breadth_first:
            return self.element_queue.pop(0)  # BFS: FIFO
        else:
            return self.element_queue.pop()   # DFS: LIFO
            
    def _get_element_key(self, element: Dict[str, Any]) -> str:
        """Generate unique key for element tracking."""
        return f"{element.get('tag', 'unknown')}:{element.get('selector', 'no-selector')}"
        
    def _create_systematic_action(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create action for systematic testing."""
        tag = element.get('tag', '').lower()
        
        if tag == 'button':
            return {'type': 'click', 'target': element.get('selector')}
        elif tag == 'a' and not self.config.skip_external_links:
            return {'type': 'click', 'target': element.get('selector')}
        elif tag == 'input':
            input_type = element.get('type', 'text')
            if input_type in ['text', 'email', 'search']:
                return {
                    'type': 'fill',
                    'target': element.get('selector'),
                    'value': f'test_{input_type}'
                }
        elif tag == 'select':
            return {'type': 'select', 'target': element.get('selector')}
            
        return None 