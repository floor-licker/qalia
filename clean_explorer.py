#!/usr/bin/env python3
"""
Clean Modular Website Explorer

A clean, maintainable implementation using modular utilities.
Demonstrates the power of extracting common patterns into reusable components.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from utils import (
    BrowserManager, BrowserConfig,
    ElementExtractor, 
    ActionExecutor, ActionConfig,
    StateManager,
    ErrorHandler,
    ModalHandler,
    SessionReporter,
    NavigationUtils
)
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ExplorationConfig:
    """Configuration for exploration session."""
    max_actions_per_page: int = 50
    action_timeout: int = 5000
    headless: bool = True
    exploration_timeout: int = 300
    capture_screenshots: bool = True


class CleanWebExplorer:
    """
    Clean, modular website explorer using extracted utility components.
    
    This demonstrates how extracting common patterns into utilities
    makes the main explorer much more maintainable and focused.
    """
    
    def __init__(self, base_url: str, config: Optional[ExplorationConfig] = None):
        self.base_url = base_url
        self.config = config or ExplorationConfig()
        
        # Initialize core components
        self.browser_manager = BrowserManager(BrowserConfig(
            headless=self.config.headless,
            timeout=self.config.action_timeout
        ))
        
        self.element_extractor = ElementExtractor(base_url)
        self.action_executor = None  # Will be initialized after browser setup
        self.state_manager = StateManager(base_url)
        self.error_handler = ErrorHandler()
        self.modal_handler = None  # Will be initialized after browser setup
        self.navigation_utils = NavigationUtils(base_url)
        self.session_manager = SessionManager(base_url)
        
        # Initialize reporter
        domain = self.navigation_utils.get_domain(base_url)
        self.reporter = SessionReporter(base_url, domain)
        
        # Exploration state
        self.visited_urls = set()
        self.discovered_elements = []
        self.executed_actions = []
        
        logger.info(f"🚀 Clean explorer initialized for: {base_url}")
    
    async def explore(self) -> Dict[str, Any]:
        """
        Main exploration method - clean and focused.
        """
        start_time = time.time()
        
        try:
            # Setup phase
            await self._setup()
            
            # Navigate to base URL
            success = await self.browser_manager.navigate(self.base_url)
            if not success:
                raise Exception("Failed to navigate to base URL")
            
            # Capture initial state
            initial_state = await self.state_manager.capture_page_state(
                self.browser_manager.page
            )
            logger.info(f"📍 Initial state captured: {initial_state}")
            
            # Perform systematic exploration
            await self._systematic_exploration()
            
            # Generate results
            end_time = time.time()
            duration = end_time - start_time
            
            results = await self._compile_results(start_time, end_time, duration)
            
            # Save session data
            await self._save_session(results)
            
            logger.info(f"✅ Exploration completed in {duration:.1f}s")
            return results
            
        except Exception as e:
            logger.error(f"💥 Exploration failed: {e}")
            
            # Generate partial results
            end_time = time.time()
            duration = end_time - start_time
            results = await self._compile_results(start_time, end_time, duration)
            results['status'] = 'failed'
            results['error'] = str(e)
            
            return results
            
        finally:
            await self._cleanup()
    
    async def _setup(self) -> None:
        """Setup all components."""
        logger.info("🔧 Setting up exploration components...")
        
        # Setup browser
        await self.browser_manager.setup()
        
        # Initialize page-dependent components
        page = self.browser_manager.page
        self.action_executor = ActionExecutor(page, ActionConfig(
            default_timeout=self.config.action_timeout
        ))
        self.modal_handler = ModalHandler(page)
        
        # Connect error handler to browser events
        self.browser_manager.add_console_handler(
            self.error_handler.handle_console_error
        )
        self.browser_manager.add_response_handler(
            self.error_handler.handle_http_error
        )
        
        # Connect action executor error handler
        self.action_executor.set_error_handler(
            self._handle_action_error
        )
        
        logger.info("✅ All components setup completed")
    
    async def _systematic_exploration(self) -> None:
        """Perform systematic exploration of the website."""
        logger.info("🔍 Starting systematic exploration...")
        
        # Extract interactive elements
        elements = await self.element_extractor.extract_from_page(
            self.browser_manager.page
        )
        self.discovered_elements.extend(elements)
        
        if not elements:
            logger.warning("⚠️ No interactive elements found!")
            return
        
        # Test elements systematically
        actions_performed = 0
        successful_actions = 0
        
        for element in elements:
            if actions_performed >= self.config.max_actions_per_page:
                logger.info(f"🛑 Reached max actions limit: {self.config.max_actions_per_page}")
                break
            
            try:
                # Check for modals before action
                modals = await self.modal_handler.detect_modals()
                if modals:
                    logger.info("🎭 Modal detected, attempting dismissal")
                    await self.modal_handler.dismiss_modal()
                
                # Execute action
                result = await self.action_executor.execute_action(element)
                self.executed_actions.append(result)
                
                actions_performed += 1
                if result.success:
                    successful_actions += 1
                
                # Capture state after action
                current_state = await self.state_manager.capture_page_state(
                    self.browser_manager.page
                )
                
                # Check if we've navigated to a new page
                current_url = self.browser_manager.get_current_url()
                if current_url != self.base_url and current_url not in self.visited_urls:
                    self.visited_urls.add(current_url)
                    logger.info(f"🆕 New page discovered: {current_url}")
                    
                    # Brief exploration of new page
                    await self._explore_new_page(current_url)
                    
                    # Navigate back to base
                    await self.browser_manager.navigate(self.base_url)
                
                # Progress reporting
                if actions_performed % 10 == 0:
                    logger.info(f"📊 Progress: {actions_performed}/{len(elements)} actions ({successful_actions} successful)")
                
            except Exception as e:
                logger.error(f"❌ Error during element exploration: {e}")
                continue
        
        success_rate = successful_actions / actions_performed if actions_performed > 0 else 0
        logger.info(f"🎯 Exploration completed: {actions_performed} actions, {success_rate:.1%} success rate")
    
    async def _explore_new_page(self, url: str) -> None:
        """Briefly explore a new page that was discovered."""
        logger.info(f"🔎 Briefly exploring new page: {url}")
        
        try:
            # Capture state
            await self.state_manager.capture_page_state(
                self.browser_manager.page
            )
            
            # Extract elements (for state tracking)
            new_elements = await self.element_extractor.extract_from_page(
                self.browser_manager.page
            )
            self.discovered_elements.extend(new_elements)
            
            logger.info(f"📋 Found {len(new_elements)} elements on new page")
            
        except Exception as e:
            logger.debug(f"Error exploring new page: {e}")
    
    async def _handle_action_error(self, action: Dict[str, Any], element: Dict[str, Any], error: str) -> None:
        """Handle action execution errors."""
        await self.error_handler.handle_action_error(
            action, element, error, self.browser_manager.page
        )
    
    async def _compile_results(self, start_time: float, end_time: float, duration: float) -> Dict[str, Any]:
        """Compile comprehensive exploration results."""
        # Get component summaries
        state_summary = self.state_manager.get_state_summary()
        error_summary = self.error_handler.get_error_summary()
        action_stats = self.action_executor.get_action_stats() if self.action_executor else {}
        
        # Calculate metrics
        total_elements = len(self.discovered_elements)
        total_actions = len(self.executed_actions)
        successful_actions = sum(1 for a in self.executed_actions if a.success)
        success_rate = successful_actions / total_actions if total_actions > 0 else 0
        
        results = {
            'status': 'completed',
            'base_url': self.base_url,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'exploration_summary': {
                'total_elements_discovered': total_elements,
                'total_actions_performed': total_actions,
                'successful_actions': successful_actions,
                'success_rate': success_rate,
                'pages_visited': len(self.visited_urls) + 1,  # +1 for base page
                'errors_found': error_summary['total_errors'],
                'states_discovered': state_summary['total_states_discovered']
            },
            'detailed_results': {
                'discovered_elements': self.discovered_elements,
                'executed_actions': [
                    {
                        'success': a.success,
                        'action': a.action,
                        'duration': a.duration,
                        'error': a.error,
                        'retry_count': a.retry_count
                    } for a in self.executed_actions
                ],
                'state_analysis': state_summary,
                'error_analysis': error_summary,
                'action_statistics': action_stats,
                'visited_urls': list(self.visited_urls)
            }
        }
        
        return results
    
    async def _save_session(self, results: Dict[str, Any]) -> None:
        """Save session results and generate reports."""
        try:
            # Generate XML sitemap for ChatGPT
            xml_sitemap = self.reporter.generate_xml_sitemap(results['detailed_results'])
            
            # Generate JSON report
            json_report = self.reporter.generate_json_report(results['detailed_results'])
            
            # Save using session manager
            domain = self.navigation_utils.get_domain(self.base_url).replace('.', '_')
            self.session_manager.save_sitemap(xml_sitemap, domain)
            self.session_manager.save_session_report(results)
            
            # Generate ChatGPT analysis prompt
            analysis_prompt = self.reporter.generate_chatgpt_analysis_prompt(
                xml_sitemap, results['detailed_results']
            )
            
            logger.info(f"💾 Session saved: {self.session_manager.session_dir}")
            logger.info("📄 Reports generated: XML sitemap, JSON report, ChatGPT prompt")
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    async def _cleanup(self) -> None:
        """Clean up all components."""
        logger.info("🧹 Cleaning up...")
        await self.browser_manager.cleanup()


# Example usage
async def main():
    """Example usage of the clean explorer."""
    base_url = "https://example.com"  # Replace with actual URL
    
    config = ExplorationConfig(
        max_actions_per_page=30,
        headless=True,
        capture_screenshots=True
    )
    
    explorer = CleanWebExplorer(base_url, config)
    results = await explorer.explore()
    
    print("\n" + "="*60)
    print("EXPLORATION RESULTS SUMMARY")
    print("="*60)
    
    summary = results['exploration_summary']
    print(f"🎯 Elements Discovered: {summary['total_elements_discovered']}")
    print(f"⚡ Actions Performed: {summary['total_actions_performed']}")
    print(f"✅ Success Rate: {summary['success_rate']:.1%}")
    print(f"🌐 Pages Visited: {summary['pages_visited']}")
    print(f"🚨 Errors Found: {summary['errors_found']}")
    print(f"🎭 States Discovered: {summary['states_discovered']}")
    print(f"⏱️ Duration: {results['duration']:.1f}s")


if __name__ == "__main__":
    asyncio.run(main()) 