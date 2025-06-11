#!/usr/bin/env python3
"""
Generate Test Cases from Exploration Sessions

Command-line script to convert exploration session data into runnable test files.
Supports multiple testing frameworks and provides comprehensive test coverage.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators import TestCaseGenerator, TestFramework, generate_tests_from_session
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the test generation banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║               🧪 QA AI - Test Case Generator                 ║
║                                                              ║
║  🤖 Automated Test Generation from Exploration Sessions      ║  
║  📝 Multiple Framework Support (Playwright, Cypress, Jest)   ║
║  🎯 Intelligent Test Case Organization                       ║
║  🔄 User Journey-Based Test Creation                         ║
╚══════════════════════════════════════════════════════════════╝
    """)


def find_latest_session(domain: str = None) -> Path:
    """Find the latest exploration session directory."""
    sessions_dir = Path("exploration_sessions")
    if not sessions_dir.exists():
        raise FileNotFoundError("No exploration_sessions directory found")
    
    session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
    if domain:
        session_dirs = [d for d in session_dirs if domain in d.name]
    
    if not session_dirs:
        raise FileNotFoundError(f"No session directories found{' for domain ' + domain if domain else ''}")
    
    # Sort by creation time, get latest
    latest = max(session_dirs, key=lambda d: d.stat().st_mtime)
    return latest


def list_available_sessions() -> None:
    """List all available exploration sessions."""
    sessions_dir = Path("exploration_sessions")
    if not sessions_dir.exists():
        print("❌ No exploration_sessions directory found")
        return
    
    session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
    if not session_dirs:
        print("❌ No exploration sessions found")
        return
    
    print("\n📁 Available Exploration Sessions:")
    print("=" * 60)
    
    for session_dir in sorted(session_dirs, key=lambda d: d.stat().st_mtime, reverse=True):
        # Try to read session info
        report_path = session_dir / "reports" / "session_report.json"
        if report_path.exists():
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    session_info = session_data.get('session_info', {})
                    exploration = session_data.get('exploration_results', {})
                    summary = exploration.get('exploration_summary', {})
                    
                    print(f"📂 {session_dir.name}")
                    print(f"   🔗 URL: {session_info.get('base_url', 'Unknown')}")
                    print(f"   📊 Actions: {summary.get('total_actions_performed', 0)}")
                    print(f"   ⏱️  Duration: {session_info.get('duration', 0):.1f}s")
                    print(f"   📁 Path: {session_dir}")
                    print()
            except Exception as e:
                print(f"📂 {session_dir.name} (Unable to read session data: {e})")
                print()
        else:
            print(f"📂 {session_dir.name} (No session report found)")
            print()


def validate_session_data(session_data: Dict[str, Any]) -> bool:
    """Validate that session data contains necessary information for test generation."""
    required_keys = ['session_info', 'exploration_results']
    
    for key in required_keys:
        if key not in session_data:
            logger.error(f"Missing required key in session data: {key}")
            return False
    
    exploration_results = session_data.get('exploration_results', {})
    detailed_results = exploration_results.get('detailed_results', {})
    executed_actions = detailed_results.get('executed_actions', [])
    
    if not executed_actions:
        logger.warning("No executed actions found in session data")
        return False
    
    logger.info(f"✅ Session data validation passed: {len(executed_actions)} actions found")
    return True


def print_generation_summary(summary: Dict[str, Any]) -> None:
    """Print a comprehensive test generation summary."""
    gen_summary = summary.get('generation_summary', {})
    test_breakdown = summary.get('test_breakdown', {})
    test_suites = summary.get('test_suites', [])
    
    print("\n" + "="*70)
    print("🧪 TEST GENERATION COMPLETE")
    print("="*70)
    
    print(f"📊 GENERATION STATISTICS:")
    print(f"  • Total test cases: {gen_summary.get('total_test_cases', 0)}")
    print(f"  • Test suites created: {gen_summary.get('total_test_suites', 0)}")
    print(f"  • User journeys analyzed: {gen_summary.get('total_journeys_analyzed', 0)}")
    print(f"  • Source actions processed: {summary.get('metadata', {}).get('total_source_actions', 0)}")
    
    print(f"\n🎯 TEST PRIORITY BREAKDOWN:")
    priority_breakdown = test_breakdown.get('by_priority', {})
    for priority, count in priority_breakdown.items():
        print(f"  • {priority.title()}: {count} tests")
    
    print(f"\n📁 TEST CATEGORY BREAKDOWN:")
    category_breakdown = test_breakdown.get('by_category', {})
    for category, count in category_breakdown.items():
        print(f"  • {category.replace('_', ' ').title()}: {count} tests")
    
    print(f"\n📋 TEST SUITES CREATED:")
    total_duration = 0
    for suite in test_suites:
        duration = suite.get('estimated_duration', 0)
        total_duration += duration
        print(f"  • {suite.get('name', 'Unknown')}: {suite.get('test_count', 0)} tests (~{duration}s)")
    
    print(f"\n⏱️ ESTIMATED EXECUTION TIME:")
    print(f"  • Total: {total_duration}s ({total_duration/60:.1f} minutes)")
    print(f"  • Average per test: {total_duration/max(gen_summary.get('total_test_cases', 1), 1):.1f}s")
    
    print("\n🚀 NEXT STEPS:")
    print("  1. Review generated test files")
    print("  2. Install framework dependencies (npm install)")
    print("  3. Run tests: npm test or playwright test")
    print("  4. Customize test data and assertions as needed")
    print("="*70)


async def generate_tests_main():
    """Main test generation function."""
    parser = argparse.ArgumentParser(
        description='Generate test cases from QA-AI exploration sessions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from latest session
  python generate_tests_from_session.py --latest

  # Generate from specific session
  python generate_tests_from_session.py --session-dir exploration_sessions/defi_space_20250611_100320

  # Generate only Playwright tests
  python generate_tests_from_session.py --latest --framework playwright

  # List available sessions
  python generate_tests_from_session.py --list

Output Structure:
  generated_tests/
  ├── playwright/
  │   ├── wallet_integration_tests.spec.ts
  │   ├── navigation_tests.spec.ts
  │   └── playwright.config.ts
  ├── cypress/
  │   ├── wallet_integration_tests.cy.js
  │   └── cypress.config.js
  └── jest/
      ├── wallet_integration_tests.test.js
      └── package.json
        """
    )
    
    # Session selection options
    session_group = parser.add_mutually_exclusive_group(required=True)
    session_group.add_argument('--session-dir', type=str,
                              help='Specific session directory to process')
    session_group.add_argument('--latest', action='store_true',
                              help='Use the latest exploration session')
    session_group.add_argument('--domain', type=str,
                              help='Use latest session for specific domain')
    session_group.add_argument('--list', action='store_true',
                              help='List available sessions and exit')
    
    # Generation options
    parser.add_argument('--output-dir', type=str, default='generated_tests',
                       help='Output directory for generated tests (default: generated_tests)')
    parser.add_argument('--framework', choices=['playwright', 'cypress', 'jest', 'all'],
                       default='all', help='Test framework to generate (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Analyze session and show what would be generated without creating files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print_banner()
    
    # Handle list command
    if args.list:
        list_available_sessions()
        return 0
    
    try:
        # Determine session directory
        if args.session_dir:
            session_dir = Path(args.session_dir)
            if not session_dir.exists():
                logger.error(f"Session directory not found: {session_dir}")
                return 1
        elif args.latest:
            session_dir = find_latest_session()
            logger.info(f"📂 Using latest session: {session_dir}")
        elif args.domain:
            session_dir = find_latest_session(args.domain)
            logger.info(f"📂 Using latest session for {args.domain}: {session_dir}")
        else:
            logger.error("No session specified")
            return 1
        
        # Load session data
        session_report_path = session_dir / "reports" / "session_report.json"
        if not session_report_path.exists():
            logger.error(f"Session report not found: {session_report_path}")
            logger.info("💡 Try running the exploration first to generate session data")
            return 1
        
        logger.info(f"📄 Loading session data from: {session_report_path}")
        with open(session_report_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Validate session data
        if not validate_session_data(session_data):
            logger.error("❌ Session data validation failed")
            return 1
        
        # Extract session information
        session_info = session_data.get('session_info', {})
        base_url = session_info.get('base_url', 'https://example.com')
        session_id = session_info.get('session_id', 'unknown')
        
        logger.info(f"🎯 Generating tests for: {base_url}")
        logger.info(f"📋 Session ID: {session_id}")
        
        # Create test generator
        exploration_results = session_data.get('exploration_results', {})
        generator = TestCaseGenerator(base_url, exploration_results)
        
        # Generate test cases
        logger.info("🔍 Analyzing user journeys and generating test cases...")
        test_suites = generator.generate_test_cases()
        
        if not test_suites:
            logger.warning("⚠️ No test cases generated - insufficient data or no user interactions found")
            return 1
        
        # Dry run mode
        if args.dry_run:
            summary = generator.generate_summary_report()
            print("\n🔍 DRY RUN MODE - Analysis Results:")
            print_generation_summary(summary)
            print("\n💡 Run without --dry-run to generate actual test files")
            return 0
        
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Output directory: {output_dir}")
        
        # Generate test files
        if args.framework == 'all':
            logger.info("🚀 Generating tests for all frameworks...")
            results = generator.export_all_frameworks(output_dir)
            
            # Print results for each framework
            for framework_name, file_paths in results.items():
                if file_paths:
                    logger.info(f"✅ {framework_name}: {len(file_paths)} files generated")
                    for file_path in file_paths:
                        logger.debug(f"   📄 {file_path}")
                else:
                    logger.warning(f"⚠️ {framework_name}: No files generated")
        else:
            # Generate for specific framework
            framework = TestFramework(args.framework)
            framework_dir = output_dir / framework.value
            framework_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🚀 Generating {framework.value} tests...")
            if framework == TestFramework.PLAYWRIGHT:
                file_paths = generator.export_playwright_tests(framework_dir)
            elif framework == TestFramework.CYPRESS:
                file_paths = generator.export_cypress_tests(framework_dir)
            elif framework == TestFramework.JEST:
                file_paths = generator.export_jest_tests(framework_dir)
            else:
                logger.error(f"Framework {framework.value} not yet implemented")
                return 1
            
            logger.info(f"✅ Generated {len(file_paths)} files")
            for file_path in file_paths:
                logger.debug(f"   📄 {file_path}")
        
        # Generate and save summary
        summary = generator.generate_summary_report()
        summary_path = output_dir / "generation_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Print summary
        print_generation_summary(summary)
        
        logger.info(f"📄 Generation summary saved: {summary_path}")
        logger.info("🎉 Test generation completed successfully!")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test generation failed: {e}")
        logger.debug("Full error details:", exc_info=True)
        return 1


def main():
    """Main entry point."""
    try:
        return asyncio.run(generate_tests_main())
    except KeyboardInterrupt:
        print("\n🛑 Test generation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 