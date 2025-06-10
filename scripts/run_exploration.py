#!/usr/bin/env python3
"""
QA AI - Autonomous Web Testing with Session Management

Enhanced to capture error screenshots and organize results in session directories.
"""

import asyncio
import logging
import argparse
import time
from pathlib import Path

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qa_ai_session.log')
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
    from explorer import WebExplorer
    
    # Create explorer with session management
    explorer_options = {
        'headless': options.get('headless', True),
        'max_depth': options.get('max_depth', 3),
        'exploration_timeout': options.get('timeout', 300),
        'action_timeout': options.get('action_timeout', 5000)
    }
    
    explorer = WebExplorer(base_url=base_url, **explorer_options)
    
    logger.info(f"🚀 Starting exploration of {base_url}")
    logger.info(f"📁 Session: {explorer.session_manager.session_id}")
    
    # Run the exploration
    results = await explorer.explore()
    
    return results

def print_session_summary(results: dict):
    """Print a comprehensive session summary."""
    session_info = results.get('session_info', {})
    exploration_summary = results.get('exploration_summary', {})
    
    print("\n" + "="*70)
    print("🎯 EXPLORATION SESSION COMPLETE")
    print("="*70)
    
    # Session information
    print(f"📁 Session Directory: {session_info.get('session_dir', 'Unknown')}")
    print(f"🔗 Base URL: {results.get('base_url', 'Unknown')}")
    print(f"⏱️  Duration: {results.get('duration', 0):.1f} seconds")
    print(f"🏁 Status: {results.get('exploration_status', 'Unknown')}")
    
    print("\n📊 EXPLORATION STATISTICS:")
    print(f"  • URLs visited: {exploration_summary.get('total_pages_visited', 0)}")
    print(f"  • Actions performed: {exploration_summary.get('total_actions_performed', 0)}")
    print(f"  • Console messages: {exploration_summary.get('console_messages', 0)}")
    
    # State mapping results
    state_stats = exploration_summary.get('state_statistics', {})
    if state_stats:
        print(f"  • States discovered: {state_stats.get('total_states_discovered', 0)}")
        print(f"  • State transitions: {state_stats.get('total_state_transitions', 0)}")
        print(f"  • Unique fingerprints: {state_stats.get('unique_state_fingerprints', 0)}")
    
    # Error statistics  
    bugs_found = exploration_summary.get('bugs_found', 0)
    warnings = exploration_summary.get('warnings', 0)
    
    print(f"\n🐛 QUALITY ASSESSMENT:")
    if bugs_found == 0 and warnings == 0:
        print(f"  ✅ No issues found - clean session!")
    else:
        print(f"  🚨 Bugs found: {bugs_found}")
        print(f"  ⚠️  Warnings: {warnings}")
    
    # Screenshot information
    screenshots_taken = session_info.get('screenshots_taken', 0)
    print(f"\n📸 ERROR DOCUMENTATION:")
    if screenshots_taken == 0:
        print(f"  ✅ No error screenshots taken - clean session!")
    else:
        print(f"  📷 Screenshots captured: {screenshots_taken}")
        print(f"  📁 Screenshots location: {session_info.get('session_dir')}/screenshots/")
    
    print("\n📁 SESSION FILES:")
    session_dir = session_info.get('session_dir', '')
    if session_dir:
        print(f"  📋 Session report: {session_dir}/reports/session_report.json")
        print(f"  📄 Human summary: {session_dir}/reports/session_summary.txt")
        print(f"  🗺️ State fingerprint: {session_dir}/reports/state_fingerprint_*.xml")
        if screenshots_taken > 0:
            print(f"  📸 Error screenshots: {session_dir}/screenshots/")
    
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