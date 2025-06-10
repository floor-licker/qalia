#!/usr/bin/env python3
"""
Command-line interface for coordinated multi-agent web exploration.
"""

import asyncio
import argparse
import logging
import json
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

from coordinated_explorer import CoordinatedWebExplorer, run_coordinated_exploration

# Load environment variables
load_dotenv()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler('coordinated_exploration.log')
    file_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)


def validate_environment() -> None:
    """Validate required environment variables."""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease create a .env file with:")
        for var in missing_vars:
            print(f"  {var}=your_value_here")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Coordinated Multi-Agent Web Exploration System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with 4 agents
  python run_coordinated.py https://example.com
  
  # Custom number of agents
  python run_coordinated.py https://example.com --agents 6
  
  # High-speed exploration
  python run_coordinated.py https://example.com --agents 8 --max-actions 2000
  
  # Visible mode for debugging
  python run_coordinated.py https://example.com --agents 2 --no-headless --verbose
        """
    )
    
    parser.add_argument(
        'url',
        help='Starting URL to explore'
    )
    
    parser.add_argument(
        '--agents', '-a',
        type=int,
        default=4,
        help='Number of concurrent agents (default: 4, recommended: 4-8)'
    )
    
    parser.add_argument(
        '--max-actions',
        type=int,
        default=1000,
        help='Maximum total actions across all agents (default: 1000)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browsers in visible mode (useful for debugging)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='coordinated_results.json',
        help='Output file for results (default: coordinated_results.json)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=1800,  # 30 minutes
        help='Maximum runtime in seconds (default: 1800)'
    )
    
    return parser.parse_args()


def print_banner() -> None:
    """Print application banner."""
    banner = """
    🚀 Coordinated Multi-Agent Web Explorer
    =====================================
    Distributed AI-powered web exploration using multiple concurrent agents
    """
    print(banner)


def print_configuration(args: argparse.Namespace) -> None:
    """Print current configuration."""
    print("📋 Configuration:")
    print(f"  Target URL: {args.url}")
    print(f"  Number of agents: {args.agents}")
    print(f"  Headless mode: {not args.no_headless}")
    print(f"  Max total actions: {args.max_actions}")
    print(f"  Actions per agent: ~{args.max_actions // args.agents}")
    print(f"  Output file: {args.output}")
    print(f"  Timeout: {args.timeout}s")
    print()


def print_agent_recommendations(num_agents: int) -> None:
    """Print recommendations for number of agents."""
    print("🤖 Agent Recommendations:")
    
    if num_agents <= 2:
        print("  ⚠️  Low parallelism - consider 4+ agents for better performance")
    elif num_agents <= 4:
        print("  ✅ Good balance - recommended for most sites")
    elif num_agents <= 8:
        print("  🚀 High parallelism - good for large sites")
    else:
        print("  ⚠️  Very high parallelism - may overwhelm target site")
    
    print(f"  • Each agent will perform ~{1000 // num_agents} actions")
    print(f"  • Total browser instances: {num_agents}")
    print()


def save_results(results: Dict[str, Any], output_file: str) -> None:
    """Save exploration results to JSON file."""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"✅ Results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")


def print_exploration_summary(results: Dict[str, Any]) -> None:
    """Print exploration summary."""
    summary = results.get('exploration_summary', {})
    
    print("\n🏆 Exploration Complete!")
    print("=" * 50)
    print(f"Duration: {summary.get('total_duration', 0):.1f} seconds")
    print(f"Agents used: {summary.get('num_agents', 0)}")
    print(f"Work items completed: {summary.get('work_items_completed', 0)}")
    print(f"Pages discovered: {summary.get('pages_discovered', 0)}")
    print(f"Elements explored: {summary.get('elements_explored', 0)}")
    print(f"Exploration coverage: {summary.get('exploration_percentage', 0):.1f}%")
    
    # Agent performance breakdown
    agent_results = results.get('agent_results', [])
    if agent_results:
        print("\n📊 Agent Performance:")
        for agent_result in agent_results:
            agent_id = agent_result.get('agent_id', 'unknown')
            pages = len(agent_result.get('pages_explored', []))
            actions = len(agent_result.get('actions_performed', []))
            bugs = len(agent_result.get('bugs_found', []))
            warnings = len(agent_result.get('warnings', []))
            
            print(f"  {agent_id}: {pages} pages, {actions} actions, {bugs} bugs, {warnings} warnings")
    
    # Error summary
    errors = results.get('errors', [])
    if errors:
        print(f"\n⚠️  {len(errors)} agent errors occurred:")
        for error in errors:
            print(f"  {error.get('agent_id', 'unknown')}: {error.get('error', 'unknown error')}")


async def run_exploration_with_timeout(args: argparse.Namespace) -> Dict[str, Any]:
    """Run exploration with timeout."""
    try:
        # Run coordinated exploration
        results = await asyncio.wait_for(
            run_coordinated_exploration(
                start_url=args.url,
                num_agents=args.agents,
                headless=not args.no_headless,
                max_actions=args.max_actions
            ),
            timeout=args.timeout
        )
        return results
    
    except asyncio.TimeoutError:
        print(f"⏰ Exploration timed out after {args.timeout} seconds")
        return {
            'error': 'timeout',
            'timeout_seconds': args.timeout,
            'exploration_summary': {'total_duration': args.timeout}
        }


async def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Setup
    setup_logging(args.verbose)
    validate_environment()
    
    # Print information
    print_banner()
    print_configuration(args)
    print_agent_recommendations(args.agents)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting coordinated exploration with {args.agents} agents")
    
    try:
        # Run exploration
        print("🚀 Starting coordinated exploration...")
        results = await run_exploration_with_timeout(args)
        
        # Save and display results
        save_results(results, args.output)
        print_exploration_summary(results)
        
    except KeyboardInterrupt:
        print("\n⏹️  Exploration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Exploration failed: {e}")
        print(f"❌ Exploration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 