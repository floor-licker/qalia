#!/usr/bin/env python3
"""
Coordinated Multi-Agent Web Explorer System

This module implements a distributed approach to web exploration where multiple
agents (browser instances) work together to efficiently map and test web applications.

Key Features:
- Shared state coordination using atomic operations
- Work queue distribution with intelligent load balancing
- Concurrent browser instances with coordination
- Real-time progress tracking and collision avoidance
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from explorer import WebExplorer
from state_store import StateStore
from state_fingerprint import StateGraph, UIState

logger = logging.getLogger(__name__)


@dataclass
class WorkItem:
    """Represents a unit of work for an agent."""
    item_id: str
    item_type: str  # 'url' or 'state_transition'
    target: str     # URL or state fingerprint
    priority: int   # Higher number = higher priority
    estimated_effort: int  # Estimated actions needed
    dependencies: List[str]  # Other work items that should complete first
    created_at: str
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class SharedWorkQueue:
    """Thread-safe work queue for coordinating multiple agents."""
    
    def __init__(self):
        self._queue: List[WorkItem] = []
        self._completed: Dict[str, WorkItem] = {}
        self._in_progress: Dict[str, WorkItem] = {}
        self._lock = threading.RLock()
        self._stats = {
            'total_items_added': 0,
            'total_items_completed': 0,
            'agents_active': 0
        }
    
    def add_work_item(self, work_item: WorkItem) -> None:
        """Add a work item to the queue."""
        with self._lock:
            self._queue.append(work_item)
            self._stats['total_items_added'] += 1
            # Sort by priority (high to low)
            self._queue.sort(key=lambda x: x.priority, reverse=True)
            logger.debug(f"Added work item: {work_item.item_type}:{work_item.target} (priority: {work_item.priority})")
    
    def claim_next_work(self, agent_id: str) -> Optional[WorkItem]:
        """Atomically claim the next available work item."""
        with self._lock:
            # Find the highest priority item that's ready to work on
            for i, item in enumerate(self._queue):
                if self._is_item_ready(item):
                    # Remove from queue and mark as in progress
                    claimed_item = self._queue.pop(i)
                    claimed_item.claimed_by = agent_id
                    claimed_item.claimed_at = datetime.now().isoformat()
                    self._in_progress[claimed_item.item_id] = claimed_item
                    
                    logger.debug(f"Agent {agent_id} claimed work: {claimed_item.item_type}:{claimed_item.target}")
                    return claimed_item
            
            return None
    
    def complete_work_item(self, item_id: str, result: Dict[str, Any]) -> None:
        """Mark a work item as completed."""
        with self._lock:
            if item_id in self._in_progress:
                completed_item = self._in_progress.pop(item_id)
                completed_item.completed_at = datetime.now().isoformat()
                completed_item.result = result
                self._completed[item_id] = completed_item
                self._stats['total_items_completed'] += 1
                
                logger.debug(f"Work item completed: {completed_item.item_type}:{completed_item.target}")
    
    def _is_item_ready(self, item: WorkItem) -> bool:
        """Check if a work item's dependencies are satisfied."""
        for dep_id in item.dependencies:
            if dep_id not in self._completed:
                return False
        return True
    
    def get_progress_stats(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        with self._lock:
            total_items = self._stats['total_items_added']
            completed_items = self._stats['total_items_completed']
            in_progress_items = len(self._in_progress)
            queued_items = len(self._queue)
            
            return {
                'total_items': total_items,
                'completed': completed_items,
                'in_progress': in_progress_items,
                'queued': queued_items,
                'completion_percentage': (completed_items / total_items * 100) if total_items > 0 else 0,
                'agents_active': self._stats['agents_active']
            }
    
    def is_work_available(self) -> bool:
        """Check if there's any work available for agents."""
        with self._lock:
            return len(self._queue) > 0 or len(self._in_progress) > 0
    
    def register_agent(self, agent_id: str) -> None:
        """Register an active agent."""
        with self._lock:
            self._stats['agents_active'] += 1
            logger.info(f"Agent {agent_id} registered. Active agents: {self._stats['agents_active']}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        with self._lock:
            self._stats['agents_active'] = max(0, self._stats['agents_active'] - 1)
            logger.info(f"Agent {agent_id} unregistered. Active agents: {self._stats['agents_active']}")


class CoordinatedWebAgent:
    """Individual agent that works as part of the coordinated exploration system."""
    
    def __init__(self, agent_id: str, shared_state: StateStore, shared_queue: SharedWorkQueue,
                 start_url: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.shared_state = shared_state
        self.shared_queue = shared_queue
        self.start_url = start_url
        self.config = config
        
        # Individual explorer instance
        self.explorer = WebExplorer(
            start_url=start_url,
            headless=config.get('headless', True),
            max_actions=config.get('max_actions_per_agent', 200),
            max_actions_per_page=config.get('max_actions_per_page', 25),
            viewport_size=config.get('viewport_size', {'width': 1280, 'height': 720}),
            exploration_mode=config.get('exploration_mode', 'intelligent')
        )
        
        # Agent state
        self.actions_performed = 0
        self.pages_explored = 0
        self.start_time = None
        self.is_active = False
        
    async def run_agent(self) -> Dict[str, Any]:
        """Main agent execution loop."""
        self.start_time = time.time()
        self.is_active = True
        
        try:
            # Register with the shared queue
            self.shared_queue.register_agent(self.agent_id)
            
            # Initialize browser for this agent
            await self.explorer._setup_browser()
            
            logger.info(f"🤖 Agent {self.agent_id} started")
            
            # Main work loop
            agent_results = await self._agent_work_loop()
            
            logger.info(f"🏁 Agent {self.agent_id} completed. "
                       f"Actions: {self.actions_performed}, Pages: {self.pages_explored}")
            
            return agent_results
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed: {e}")
            return {'error': str(e), 'actions_performed': self.actions_performed}
        
        finally:
            self.is_active = False
            self.shared_queue.unregister_agent(self.agent_id)
            await self.explorer._cleanup_browser()
    
    async def _agent_work_loop(self) -> Dict[str, Any]:
        """Agent's main work processing loop."""
        agent_results = {
            'agent_id': self.agent_id,
            'pages_explored': [],
            'actions_performed': [],
            'states_discovered': [],
            'bugs_found': [],
            'warnings': []
        }
        
        work_timeout_count = 0
        max_timeout_count = 3  # Stop after 3 consecutive timeouts
        
        while work_timeout_count < max_timeout_count:
            # Try to claim next work item
            work_item = self.shared_queue.claim_next_work(self.agent_id)
            
            if work_item is None:
                # No work available, wait a bit and check again
                await asyncio.sleep(2.0)
                work_timeout_count += 1
                
                # Check if other agents are still working
                stats = self.shared_queue.get_progress_stats()
                if stats['in_progress'] == 0 and stats['queued'] == 0:
                    logger.info(f"Agent {self.agent_id}: No work available and no other agents working")
                    break
                
                continue
            
            # Reset timeout counter since we got work
            work_timeout_count = 0
            
            # Process the work item
            try:
                work_result = await self._process_work_item(work_item)
                self.shared_queue.complete_work_item(work_item.item_id, work_result)
                
                # Update agent results
                self._update_agent_results(agent_results, work_result)
                
                # Discover new work from this result
                await self._discover_new_work(work_result)
                
            except Exception as e:
                logger.error(f"Agent {self.agent_id} failed to process work item {work_item.item_id}: {e}")
                self.shared_queue.complete_work_item(work_item.item_id, {'error': str(e)})
        
        return agent_results
    
    async def _process_work_item(self, work_item: WorkItem) -> Dict[str, Any]:
        """Process a specific work item."""
        logger.info(f"🔄 Agent {self.agent_id} processing: {work_item.item_type}:{work_item.target}")
        
        if work_item.item_type == 'url':
            return await self._explore_url(work_item.target)
        elif work_item.item_type == 'state_transition':
            return await self._explore_state_transition(work_item.target)
        else:
            raise ValueError(f"Unknown work item type: {work_item.item_type}")
    
    async def _explore_url(self, url: str) -> Dict[str, Any]:
        """Explore a specific URL."""
        try:
            # Navigate to the URL
            await self.explorer._navigate_to_url(url) 
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Extract page information
            html_content = await self.explorer.page.content()
            from utils import extract_page_info, extract_interactive_elements
            page_info = extract_page_info(html_content, url)
            interactive_elements = extract_interactive_elements(html_content, url)
            
            # Record page exploration in shared state
            self.shared_state.record_page_exploration(url, page_info, interactive_elements)
            
            # Extract current UI state for state graph
            current_ui_state = self.explorer.state_extractor.extract_ui_state(
                self.explorer.page, url, page_info)
            state_fingerprint = self.explorer.state_graph.add_state(current_ui_state)
            
            # Perform limited exploration on this page (to avoid overwhelming the queue)
            max_actions_on_page = min(5, len(interactive_elements))  # Limit actions per agent per page
            prioritized_elements = self.explorer.performance_optimizer.prioritize_elements(
                interactive_elements[:max_actions_on_page])
            
            page_actions = []
            for element in prioritized_elements:
                action = self.explorer._create_systematic_action(element)
                if action:
                    action_result = await self.explorer._execute_action(action)
                    page_actions.append(action_result)
                    self.actions_performed += 1
                    
                    # Quick break if we hit an error
                    if not action_result.get('success', False):
                        break
            
            self.pages_explored += 1
            
            # Discover links for future exploration
            discovered_links = [elem['href'] for elem in interactive_elements if elem['type'] == 'link']
            
            return {
                'type': 'url_exploration',
                'url': url,
                'page_info': page_info,
                'interactive_elements': interactive_elements,
                'discovered_links': discovered_links,
                'actions_performed': page_actions,
                'state_fingerprint': state_fingerprint,
                'agent_id': self.agent_id
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed to explore URL {url}: {e}")
            return {'type': 'url_exploration', 'url': url, 'error': str(e), 'agent_id': self.agent_id}
    
    async def _explore_state_transition(self, state_fingerprint: str) -> Dict[str, Any]:
        """Explore unexplored transitions from a specific state."""
        # This would implement state-based exploration
        # For now, return a placeholder
        return {
            'type': 'state_transition_exploration',
            'state_fingerprint': state_fingerprint,
            'agent_id': self.agent_id,
            'note': 'State transition exploration not fully implemented yet'
        }
    
    async def _discover_new_work(self, work_result: Dict[str, Any]) -> None:
        """Discover and queue new work items from exploration results."""
        if work_result.get('type') == 'url_exploration' and 'discovered_links' in work_result:
            # Add discovered links as new work items
            for link in work_result['discovered_links'][:3]:  # Limit to prevent explosion
                if not self.shared_state.has_visited_url(link):
                    work_item = WorkItem(
                        item_id=f"url_{uuid.uuid4().hex[:8]}",
                        item_type='url',
                        target=link,
                        priority=5,  # Medium priority for discovered links
                        estimated_effort=10,
                        dependencies=[],
                        created_at=datetime.now().isoformat()
                    )
                    self.shared_queue.add_work_item(work_item)
    
    def _update_agent_results(self, agent_results: Dict[str, Any], work_result: Dict[str, Any]) -> None:
        """Update agent results with work result data."""
        if work_result.get('type') == 'url_exploration':
            agent_results['pages_explored'].append(work_result)
            agent_results['actions_performed'].extend(work_result.get('actions_performed', []))
            
            # Extract bugs and warnings
            for action in work_result.get('actions_performed', []):
                if action.get('evaluation', {}).get('status') == 'BUG':
                    agent_results['bugs_found'].append(action)
                elif action.get('evaluation', {}).get('status') == 'WARNING':
                    agent_results['warnings'].append(action)


class CoordinatedWebExplorer:
    """Main coordinator for multi-agent web exploration."""
    
    def __init__(self, start_url: str, num_agents: int = 4, config: Dict[str, Any] = None):
        self.start_url = start_url
        self.num_agents = num_agents
        self.config = config or {}
        
        # Shared components
        self.shared_state = StateStore()
        self.shared_queue = SharedWorkQueue()
        
        # Agent instances
        self.agents: List[CoordinatedWebAgent] = []
        
        # Results
        self.exploration_start_time = None
        self.exploration_results = {}
        
        logger.info(f"🚀 Coordinated explorer initialized with {num_agents} agents")
    
    async def start_coordinated_exploration(self) -> Dict[str, Any]:
        """Start the coordinated multi-agent exploration."""
        self.exploration_start_time = time.time()
        
        try:
            # Initialize shared state
            self.shared_state.set_target_site(self.start_url)
            
            # Create initial work item
            initial_work = WorkItem(
                item_id="initial_url",
                item_type='url',
                target=self.start_url,
                priority=10,  # Highest priority
                estimated_effort=15,
                dependencies=[],
                created_at=datetime.now().isoformat()
            )
            self.shared_queue.add_work_item(initial_work)
            
            # Create and start agents (this now returns results)
            exploration_results = await self._create_and_start_agents()
            
            # Generate final report
            final_results = await self._generate_final_results(exploration_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Coordinated exploration failed: {e}")
            raise
    
    async def _create_and_start_agents(self) -> None:
        """Create and start all agent instances."""
        # Create agents
        for i in range(self.num_agents):
            agent_id = f"agent_{i+1:02d}"
            agent = CoordinatedWebAgent(
                agent_id=agent_id,
                shared_state=self.shared_state,
                shared_queue=self.shared_queue,
                start_url=self.start_url,
                config=self.config
            )
            self.agents.append(agent)
        
        logger.info(f"Created {len(self.agents)} agents")
        
        # Start all agents concurrently
        agent_tasks = [agent.run_agent() for agent in self.agents]
        
                 # Wait for all agents to complete
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Process agent results
        self.exploration_results = {
            'agents': [],
            'summary': {},
            'errors': []
        }
        
        for i, result in enumerate(agent_results):
            if isinstance(result, Exception):
                self.exploration_results['errors'].append({
                    'agent_id': f"agent_{i+1:02d}",
                    'error': str(result)
                })
            else:
                self.exploration_results['agents'].append(result)
        
        # Return the results for the monitoring process
        return self.exploration_results
    
    async def _generate_final_results(self, exploration_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final exploration results."""
        # Generate final report
        final_stats = self.shared_queue.get_progress_stats()
        site_summary = self.shared_state.get_site_exploration_summary()
        
        total_duration = time.time() - self.exploration_start_time
        
        final_results = {
            'exploration_summary': {
                'total_duration': total_duration,
                'num_agents': self.num_agents,
                'work_items_completed': final_stats['completed'],
                'pages_discovered': site_summary['total_pages_discovered'],
                'elements_explored': site_summary['total_elements_explored'],
                'exploration_percentage': site_summary['exploration_percentage']
            },
            'agent_results': exploration_results['agents'],
            'work_queue_stats': final_stats,
            'site_summary': site_summary,
            'errors': exploration_results['errors']
        }
        
        logger.info(f"🏆 Coordinated exploration completed! "
                   f"Duration: {total_duration:.1f}s, "
                   f"Pages: {site_summary['total_pages_discovered']}, "
                   f"Exploration: {site_summary['exploration_percentage']:.1f}%")
        
        return final_results


# Convenience function for easy usage
async def run_coordinated_exploration(start_url: str, num_agents: int = 4, 
                                    headless: bool = True, max_actions: int = 1000) -> Dict[str, Any]:
    """
    Run coordinated multi-agent exploration with default settings.
    
    Args:
        start_url: URL to start exploration from
        num_agents: Number of concurrent agents (default: 4)
        headless: Whether to run browsers in headless mode
        max_actions: Maximum total actions across all agents
        
    Returns:
        Dictionary containing exploration results
    """
    config = {
        'headless': headless,
        'max_actions_per_agent': max_actions // num_agents,
        'max_actions_per_page': 25,
        'exploration_mode': 'intelligent'
    }
    
    coordinator = CoordinatedWebExplorer(start_url, num_agents, config)
    return await coordinator.start_coordinated_exploration()