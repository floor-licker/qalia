#!/usr/bin/env python3
"""
Basic Usage Example

Demonstrates how to use the modular Qalia system for simple website exploration.
"""

import asyncio
from explorers import BasicExplorer
from config import ExplorationConfig


async def basic_exploration_example():
    """Example of basic systematic exploration."""
    
    # Create configuration for systematic exploration
    config = ExplorationConfig.for_systematic_exploration()
    
    # Initialize explorer
    explorer = BasicExplorer("https://example.com", config)
    
    # Run exploration
    print("🚀 Starting basic exploration...")
    results = await explorer.explore()
    
    # Print summary
    print(f"✅ Exploration completed!")
    print(f"📊 Pages visited: {results['exploration_summary']['total_pages_visited']}")
    print(f"🎯 Actions performed: {results['exploration_summary']['total_actions_performed']}")
    print(f"🐛 Bugs found: {results['exploration_summary']['bugs_found']}")
    
    return results


async def quick_scan_example():
    """Example of quick website scanning."""
    
    # Create configuration for quick scanning
    config = ExplorationConfig.for_quick_scan()
    
    # Initialize explorer
    explorer = BasicExplorer("https://example.com", config)
    
    # Run quick scan
    print("⚡ Starting quick scan...")
    results = await explorer.explore()
    
    print(f"✅ Quick scan completed in {results['duration']:.1f}s")
    return results


if __name__ == "__main__":
    # Run basic exploration
    asyncio.run(basic_exploration_example())
    
    # Run quick scan
    # asyncio.run(quick_scan_example()) 