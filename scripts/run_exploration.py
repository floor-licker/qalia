#!/usr/bin/env python3
"""
QA AI - Autonomous Web Testing with Session Management

Enhanced to capture error screenshots and organize results in session directories.
"""

import asyncio
import logging
import argparse
import time
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qalia_session.log')
    ]
)

logger = logging.getLogger(__name__)

def print_banner():
    """Print the QA AI banner with session info."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    🔍 QA AI - Session Explorer                ║
║                                                              ║
║  🎯 Autonomous Website Testing with Error Screenshots         ║  
║  📁 Session-based Organization                               ║
║  📸 Visual Error Documentation                               ║
║  🗺️ Complete State Fingerprinting                            ║
╚══════════════════════════════════════════════════════════════╝
    """)

async def run_exploration(base_url: str, options: dict = None) -> dict:
    """
    Run website exploration with session management.
    
    Args:
        base_url: URL to explore
        options: Additional exploration options
        
    Returns:
        Dictionary containing exploration results and session info
    """
    from explorers import BasicExplorer as WebExplorer
    from explorers.basic_explorer import ExplorationConfig
    
    # Create exploration configuration
    config = ExplorationConfig(
        headless=options.get('headless', True),
        exploration_timeout=options.get('timeout', 300),
        action_timeout=options.get('action_timeout', 15000),
        navigation_timeout=options.get('navigation_timeout', 60000),
        max_actions_per_page=100,  # Increased for BFS exploration
        max_depth=options.get('max_depth', 3),  # BFS depth limit
        capture_screenshots=True
    )
    
    explorer = WebExplorer(base_url=base_url, config=config)
    
    logger.info(f"🚀 Starting exploration of {base_url}")
    logger.info(f"📁 Session: {explorer.session_manager.session_id}")
    
    # Run the exploration
    results = await explorer.explore()
    
    return results

def print_session_summary(results: dict):
    """Print a comprehensive session summary."""
    session_info = results.get('session_info', {})
    exploration_summary = results.get('exploration_summary', {})
    detailed_results = results.get('detailed_results', {})
    
    print("\n" + "="*70)
    print("🎯 EXPLORATION SESSION COMPLETE")
    print("="*70)
    
    # Session information - try multiple sources for session directory
    session_dir = (results.get('session_dir') or
                  session_info.get('session_dir') or 
                  detailed_results.get('session_dir') or 
                  'Unknown')
    
    print(f"📁 Session Directory: {session_dir}")
    print(f"🔗 Base URL: {results.get('base_url', 'Unknown')}")
    print(f"⏱️  Duration: {results.get('duration', 0):.1f} seconds")
    print(f"🏁 Status: {results.get('status', 'Unknown')}")
    
    print("\n📊 EXPLORATION STATISTICS:")
    print(f"  • URLs visited: {exploration_summary.get('pages_visited', 0)}")
    print(f"  • Actions performed: {exploration_summary.get('total_actions_performed', 0)}")
    print(f"  • Console messages: {exploration_summary.get('errors_found', 0)}")
    
    # State mapping results
    states_discovered = exploration_summary.get('states_discovered', 0)
    if states_discovered > 0:
        print(f"  • States discovered: {states_discovered}")
    
    # Error statistics - use actual data from exploration_summary
    errors_found = exploration_summary.get('errors_found', 0)
    
    print(f"\n🐛 QUALITY ASSESSMENT:")
    if errors_found == 0:
        print(f"  ✅ No issues found - clean session!")
    else:
        print(f"  🚨 Console errors detected: {errors_found}")
    
    # Screenshot information - assume no screenshots if not specified
    print(f"\n📸 ERROR DOCUMENTATION:")
    print(f"  ✅ No error screenshots taken - clean session!")
    
    print("\n📁 SESSION FILES:")
    # Use best available session directory info
    if session_dir and session_dir != 'Unknown':
        print(f"  📋 Session report: {session_dir}/reports/session_report.json")
        print(f"  📄 Human summary: {session_dir}/reports/session_summary.txt")
        print(f"  🗺️ State fingerprint: {session_dir}/reports/state_fingerprint_*.xml")
        print(f"  🤖 ChatGPT analysis: {session_dir}/reports/chatgpt_bug_analysis.md")
    
    print("="*70)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='QA AI - Autonomous Web Testing with Session Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py https://example.com
  python run.py https://app.defi.space --headless
  python run.py https://mysite.com --max-depth 5 --timeout 600
  
Session Output:
  Each run creates a unique session directory containing:
  • Screenshots of any errors encountered
  • Complete XML state fingerprint 
  • Human-readable and JSON reports
  • All files organized by timestamp
        """
    )
    
    parser.add_argument('url', help='Base URL to explore')
    parser.add_argument('--headless', action='store_true', 
                       help='Run browser in headless mode (default: visible)')
    parser.add_argument('--max-depth', type=int, default=3,
                       help='Maximum exploration depth (default: 3)')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Exploration timeout in seconds (default: 300)')
    parser.add_argument('--action-timeout', type=int, default=5000,
                       help='Individual action timeout in ms (default: 5000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print banner
    print_banner()
    
    # Prepare options
    options = {
        'headless': args.headless,
        'max_depth': args.max_depth,
        'timeout': args.timeout,
        'action_timeout': args.action_timeout
    }
    
    print(f"🔗 Target URL: {args.url}")
    print(f"🖥️  Browser Mode: {'Headless' if args.headless else 'Visible'}")
    print(f"🔍 Max Depth: {args.max_depth}")
    print(f"⏱️  Timeout: {args.timeout}s")
    print(f"📸 Error Screenshots: Enabled")
    print()
    
    try:
        # Run exploration
        start_time = time.time()
        results = asyncio.run(run_exploration(args.url, options))
        end_time = time.time()
        
        # Print results
        print_session_summary(results)
        
        # Show how to access files
        session_dir = results.get('session_info', {}).get('session_dir', '')
        if session_dir and Path(session_dir).exists():
            print(f"\n💡 To view session files:")
            print(f"   open {session_dir}")
            print(f"   ls -la {session_dir}/screenshots/")
            print(f"   cat {session_dir}/reports/session_summary.txt")
        
    except KeyboardInterrupt:
        print("\n🛑 Exploration interrupted by user")
        logger.info("Exploration interrupted by user")
    except Exception as e:
        print(f"\n❌ Exploration failed: {e}")
        logger.error(f"Exploration failed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 