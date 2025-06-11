#!/usr/bin/env python3
"""
QA AI - Autonomous Web Testing with Automatic Test Generation

Enhanced exploration runner that automatically generates test cases after 
exploration completes. Provides end-to-end workflow from discovery to automation.
"""

import asyncio
import logging
import argparse
import time
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators import TestCaseGenerator
import json

# Import run_exploration function directly
sys.path.insert(0, str(Path(__file__).parent))
from run_exploration import run_exploration, print_session_summary

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qa_ai_complete_session.log')
    ]
)

logger = logging.getLogger(__name__)

def print_banner():
    """Print the enhanced QA AI banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║            🔍 QA AI - Complete Testing Workflow               ║
║                                                              ║
║  🎯 1. Autonomous Website Exploration                        ║  
║  🧪 2. Automatic Test Case Generation                        ║
║  📝 3. Multi-Framework Test Export                           ║
║  🚀 4. Ready-to-Run Test Suites                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

async def generate_tests_from_results(results: dict, output_dir: Path, frameworks: list = None) -> dict:
    """
    Generate test cases from exploration results.
    
    Args:
        results: Exploration results dictionary
        output_dir: Directory to save generated tests
        frameworks: List of frameworks to generate (default: all)
        
    Returns:
        Test generation summary
    """
    if frameworks is None:
        frameworks = ['playwright', 'cypress', 'jest']
    
    # Extract base URL and exploration data
    base_url = results.get('base_url', 'https://example.com')
    exploration_data = results.get('detailed_results', {})
    
    logger.info("🧪 Starting automatic test case generation...")
    logger.info(f"🎯 Target: {base_url}")
    
    # Create test generator
    generator = TestCaseGenerator(base_url, {
        'exploration_summary': results.get('exploration_summary', {}),
        'detailed_results': exploration_data
    })
    
    # Generate test cases
    test_suites = generator.generate_test_cases()
    
    if not test_suites:
        logger.warning("⚠️ No test cases generated - insufficient data")
        return {'error': 'No test cases generated'}
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export to specified frameworks
    results_by_framework = {}
    
    for framework in frameworks:
        try:
            framework_dir = output_dir / framework
            framework_dir.mkdir(parents=True, exist_ok=True)
            
            if framework == 'playwright':
                file_paths = generator.export_playwright_tests(framework_dir)
            elif framework == 'cypress':
                file_paths = generator.export_cypress_tests(framework_dir)
            elif framework == 'jest':
                file_paths = generator.export_jest_tests(framework_dir)
            else:
                logger.warning(f"Framework {framework} not supported, skipping")
                continue
            
            results_by_framework[framework] = file_paths
            logger.info(f"✅ {framework}: {len(file_paths)} files generated")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate {framework} tests: {e}")
            results_by_framework[framework] = []
    
    # Generate summary
    summary = generator.generate_summary_report()
    summary['framework_results'] = results_by_framework
    
    # Save summary
    summary_path = output_dir / "test_generation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"📄 Test generation summary saved: {summary_path}")
    
    return summary

def print_test_generation_summary(summary: dict, output_dir: Path):
    """Print comprehensive test generation summary."""
    if 'error' in summary:
        print(f"\n❌ TEST GENERATION FAILED: {summary['error']}")
        return
    
    gen_summary = summary.get('generation_summary', {})
    test_breakdown = summary.get('test_breakdown', {})
    framework_results = summary.get('framework_results', {})
    
    print("\n" + "🧪" + "="*68)
    print("🧪 AUTOMATED TEST GENERATION COMPLETE")
    print("🧪" + "="*68)
    
    print(f"📊 GENERATION STATISTICS:")
    print(f"  • Total test cases: {gen_summary.get('total_test_cases', 0)}")
    print(f"  • Test suites created: {gen_summary.get('total_test_suites', 0)}")
    print(f"  • User journeys analyzed: {gen_summary.get('total_journeys_analyzed', 0)}")
    
    print(f"\n🎯 TEST PRIORITY BREAKDOWN:")
    priority_breakdown = test_breakdown.get('by_priority', {})
    for priority, count in priority_breakdown.items():
        print(f"  • {priority.title()}: {count} tests")
    
    print(f"\n📝 FRAMEWORK OUTPUT:")
    total_files = 0
    for framework, file_paths in framework_results.items():
        file_count = len(file_paths)
        total_files += file_count
        status = "✅" if file_count > 0 else "❌"
        print(f"  {status} {framework.title()}: {file_count} files")
        if file_count > 0:
            framework_dir = output_dir / framework
            print(f"     📁 {framework_dir}")
    
    print(f"\n🚀 READY-TO-RUN COMMANDS:")
    for framework in framework_results.keys():
        if len(framework_results[framework]) > 0:
            framework_dir = output_dir / framework
            if framework == 'playwright':
                print(f"  📝 Playwright: cd {framework_dir} && npm install && npx playwright test")
            elif framework == 'cypress':
                print(f"  📝 Cypress: cd {framework_dir} && npm install && npx cypress run")
            elif framework == 'jest':
                print(f"  📝 Jest: cd {framework_dir} && npm install && npm test")
    
    print(f"\n📁 ALL FILES SAVED TO:")
    print(f"   {output_dir}")
    print("🧪" + "="*68)

async def run_complete_workflow(base_url: str, options: dict = None) -> dict:
    """
    Run complete workflow: exploration + test generation.
    
    Args:
        base_url: URL to explore and test
        options: Exploration and generation options
        
    Returns:
        Combined results from exploration and test generation
    """
    # Default options
    if options is None:
        options = {}
    
    # Step 1: Run exploration
    logger.info("🚀 Phase 1: Website Exploration")
    logger.info("=" * 50)
    
    exploration_results = await run_exploration(base_url, options)
    
    # Print exploration summary
    print_session_summary(exploration_results)
    
    # Check if exploration was successful
    if exploration_results.get('status') != 'completed':
        logger.error("❌ Exploration failed, skipping test generation")
        return {
            'exploration': exploration_results,
            'test_generation': {'error': 'Exploration failed'}
        }
    
    # Step 2: Generate tests
    logger.info("\n🧪 Phase 2: Automatic Test Generation")
    logger.info("=" * 50)
    
    # Create output directory based on session
    session_dir = exploration_results.get('session_dir')
    if session_dir:
        output_dir = Path(session_dir) / "generated_tests"
    else:
        output_dir = Path("generated_tests") / f"tests_{int(time.time())}"
    
    # Generate tests
    frameworks = options.get('test_frameworks', ['playwright', 'cypress', 'jest'])
    test_results = await generate_tests_from_results(
        exploration_results, 
        output_dir, 
        frameworks
    )
    
    # Print test generation summary
    print_test_generation_summary(test_results, output_dir)
    
    # Combined results
    complete_results = {
        'workflow': 'complete',
        'base_url': base_url,
        'total_duration': exploration_results.get('duration', 0),
        'exploration': exploration_results,
        'test_generation': test_results,
        'output_directory': str(output_dir)
    }
    
    return complete_results

def main():
    """Main entry point for complete workflow."""
    parser = argparse.ArgumentParser(
        description='QA AI - Complete Testing Workflow (Exploration + Test Generation)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete workflow with all defaults
  python run_exploration_with_tests.py https://defi.space

  # Custom exploration with specific test frameworks
  python run_exploration_with_tests.py https://app.example.com --frameworks playwright cypress

  # Headless exploration with Jest tests only
  python run_exploration_with_tests.py https://myapp.com --headless --frameworks jest

  # Extended exploration depth with all test frameworks
  python run_exploration_with_tests.py https://complex-app.com --max-depth 5 --frameworks playwright cypress jest

Output Structure:
  exploration_sessions/
  └── domain_20250611_100320/
      ├── screenshots/           # Error screenshots from exploration
      ├── reports/               # Exploration reports and analysis
      └── generated_tests/       # Auto-generated test files
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
    
    parser.add_argument('url', help='Base URL to explore and generate tests for')
    
    # Exploration options
    parser.add_argument('--headless', action='store_true', 
                       help='Run browser in headless mode')
    parser.add_argument('--max-depth', type=int, default=3,
                       help='Maximum exploration depth (default: 3)')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Exploration timeout in seconds (default: 300)')
    parser.add_argument('--action-timeout', type=int, default=5000,
                       help='Individual action timeout in ms (default: 5000)')
    
    # Test generation options
    parser.add_argument('--frameworks', nargs='+', 
                       choices=['playwright', 'cypress', 'jest'],
                       default=['playwright', 'cypress', 'jest'],
                       help='Test frameworks to generate (default: all)')
    parser.add_argument('--skip-test-generation', action='store_true',
                       help='Skip automatic test generation')
    
    # General options
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
        'action_timeout': args.action_timeout,
        'test_frameworks': args.frameworks,
        'skip_test_generation': args.skip_test_generation
    }
    
    print(f"🔗 Target URL: {args.url}")
    print(f"🖥️  Browser Mode: {'Headless' if args.headless else 'Visible'}")
    print(f"🔍 Max Depth: {args.max_depth}")
    print(f"⏱️  Timeout: {args.timeout}s")
    print(f"🧪 Test Frameworks: {', '.join(args.frameworks)}")
    print(f"📸 Screenshots: Enabled")
    print()
    
    try:
        # Run complete workflow
        start_time = time.time()
        results = asyncio.run(run_complete_workflow(args.url, options))
        end_time = time.time()
        
        total_duration = end_time - start_time
        
        # Final summary
        print("\n" + "🎉" + "="*68)
        print("🎉 COMPLETE QA WORKFLOW FINISHED")
        print("🎉" + "="*68)
        
        exploration_summary = results['exploration'].get('exploration_summary', {})
        test_summary = results['test_generation'].get('generation_summary', {})
        
        print(f"⏱️  TOTAL DURATION: {total_duration:.1f} seconds")
        print(f"🔍 EXPLORATION: {exploration_summary.get('total_actions_performed', 0)} actions, "
              f"{exploration_summary.get('pages_visited', 0)} pages")
        print(f"🧪 TEST GENERATION: {test_summary.get('total_test_cases', 0)} test cases, "
              f"{test_summary.get('total_test_suites', 0)} suites")
        
        if 'output_directory' in results:
            print(f"📁 ALL OUTPUT: {results['output_directory']}")
        
        print("\n🚀 READY TO RUN AUTOMATED TESTS!")
        print("🎉" + "="*68)
        
    except KeyboardInterrupt:
        print("\n🛑 Workflow interrupted by user")
        logger.info("Complete workflow interrupted by user")
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        logger.error(f"Complete workflow failed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 