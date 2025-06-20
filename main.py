#!/usr/bin/env python3
"""
QA AI - Complete Testing Pipeline

Unified entry point that runs exploration and automatically generates test cases.
This provides a seamless workflow from discovery to automation.
"""

import asyncio
import argparse
import time
import json
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scripts.run_exploration import run_exploration
from generators import TestCaseGenerator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qalia_complete_session.log')
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the unified QA AI banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  🚀 QA AI - Complete Pipeline                ║
║                                                              ║
║  🔍 1. Autonomous Web Exploration                            ║
║  🧪 2. Automatic Test Case Generation                        ║
║  📝 3. Multi-Framework Test Export                           ║
║  🎯 Discovery → Automation in One Command                    ║
╚══════════════════════════════════════════════════════════════╝
    """)


async def run_complete_pipeline(
    base_url: str,
    exploration_options: Dict[str, Any] = None,
    generation_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run the complete QA AI pipeline: exploration + test generation.
    
    Args:
        base_url: URL to explore and generate tests for
        exploration_options: Options for the exploration phase
        generation_options: Options for test generation phase
        
    Returns:
        Complete pipeline results including session info and test generation summary
    """
    exploration_options = exploration_options or {}
    generation_options = generation_options or {}
    
    print("🔍 PHASE 1: WEB EXPLORATION")
    print("=" * 50)
    
    # Run exploration
    logger.info(f"Starting exploration of {base_url}")
    exploration_results = await run_exploration(base_url, exploration_options)
    
    if exploration_results.get('status') != 'completed':
        raise Exception(f"Exploration failed: {exploration_results.get('error', 'Unknown error')}")
    
    # Extract session directory directly from exploration results
    session_dir = exploration_results.get('session_dir')
    
    print(f"✅ Exploration completed successfully!")
    print(f"📁 Session directory: {session_dir}")
    
    print("\n🧪 PHASE 2: TEST CASE GENERATION")
    print("=" * 50)
    
    # Generate test cases from exploration session
    logger.info("Starting test case generation from exploration results")
    
    # Load session data for test generation
    exploration_data = exploration_results.get('exploration_results', exploration_results)
    
    # Create test generator
    generator = TestCaseGenerator(base_url, exploration_data)
    test_suites = generator.generate_test_cases()
    
    if not test_suites:
        logger.warning("No test cases generated - exploration may not have captured enough actions")
        print("⚠️ No test cases generated. Try running with more exploration depth or longer timeout.")
        return {
            'status': 'partial_success',
            'exploration_results': exploration_results,
            'test_generation_results': None,
            'message': 'Exploration succeeded but no test cases generated'
        }
    
    # Export tests to all frameworks
    output_dir = Path("generated_tests")
    if generation_options.get('output_dir'):
        output_dir = Path(generation_options['output_dir'])
    
    frameworks = generation_options.get('frameworks', ['playwright', 'cypress', 'jest'])
    
    # Generate test files
    generated_files = {}
    if 'playwright' in frameworks:
        generated_files['playwright'] = generator.export_playwright_tests(output_dir / 'playwright')
    if 'cypress' in frameworks:
        generated_files['cypress'] = generator.export_cypress_tests(output_dir / 'cypress')
    if 'jest' in frameworks:
        generated_files['jest'] = generator.export_jest_tests(output_dir / 'jest')
    
    # Generate summary report
    summary = generator.generate_summary_report()
    
    # Save summary to session directory if available
    if session_dir:
        summary_path = Path(session_dir) / "reports" / "test_generation_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Test generation summary saved to: {summary_path}")
    
    # Also save to generated_tests directory
    output_summary_path = output_dir / "generation_summary.json"
    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"✅ Test generation completed successfully!")
    print(f"📁 Tests saved to: {output_dir}")
    logger.info(f"🏁 POST-EXPLORATION: Complete pipeline finished - generated {summary['generation_summary']['total_test_cases']} test cases across {len(frameworks)} frameworks")
    
    # Execute generated tests to validate they work
    test_execution_results = None
    if generation_options.get('run_tests', True):  # New option to enable/disable test execution
        logger.info("🚀 POST-GENERATION: Starting test execution validation...")
        test_execution_results = await run_generated_tests(output_dir, ['playwright'])  # Start with Playwright only for speed
        
        # Save test execution results
        if session_dir:
            execution_results_path = Path(session_dir) / "reports" / "test_execution_results.json"
            execution_results_path.parent.mkdir(parents=True, exist_ok=True)
            with open(execution_results_path, 'w', encoding='utf-8') as f:
                json.dump(test_execution_results, f, indent=2, default=str)
            logger.info(f"Test execution results saved to: {execution_results_path}")
    
    return {
        'status': 'success',
        'exploration_results': exploration_results,
        'test_generation_results': {
            'test_suites': test_suites,
            'generated_files': generated_files,
            'summary': summary,
            'output_directory': str(output_dir)
        },
        'test_execution_results': test_execution_results,
        'session_directory': session_dir
    }


def print_pipeline_summary(results: Dict[str, Any]):
    """Print comprehensive pipeline summary."""
    print("\n" + "="*70)
    print("🎉 QA AI PIPELINE COMPLETE")
    print("="*70)
    
    exploration_results = results.get('exploration_results', {})
    test_results = results.get('test_generation_results', {})
    execution_results = results.get('test_execution_results', {})
    
    # Exploration Summary
    print("🔍 EXPLORATION PHASE:")
    session_info = exploration_results.get('session_info', {})
    exploration_summary = exploration_results.get('exploration_summary', {})
    
    print(f"  • Duration: {exploration_results.get('duration', 0):.1f} seconds")
    print(f"  • URLs visited: {exploration_summary.get('pages_visited', 0)}")
    print(f"  • Actions performed: {exploration_summary.get('total_actions_performed', 0)}")
    print(f"  • Errors found: {exploration_summary.get('errors_found', 0)}")
    print(f"  • Session: {results.get('session_directory', 'Unknown')}")
    
    # Test Generation Summary
    if test_results:
        print("\n🧪 TEST GENERATION PHASE:")
        summary = test_results.get('summary', {})
        gen_summary = summary.get('generation_summary', {})
        
        print(f"  • Test cases generated: {gen_summary.get('total_test_cases', 0)}")
        print(f"  • Test suites created: {gen_summary.get('total_test_suites', 0)}")
        print(f"  • User journeys analyzed: {gen_summary.get('total_journeys_analyzed', 0)}")
        
        # Framework breakdown
        generated_files = test_results.get('generated_files', {})
        print(f"  • Frameworks generated:")
        for framework, files in generated_files.items():
            print(f"    - {framework.title()}: {len(files)} files")
        
        print(f"  • Output directory: {test_results.get('output_directory', 'Unknown')}")
    
    # Test Execution Summary
    if execution_results:
        print("\n🏃 TEST EXECUTION PHASE:")
        exec_summary = execution_results.get('execution_summary', {})
        framework_results = execution_results.get('framework_results', {})
        
        print(f"  • Frameworks tested: {exec_summary.get('total_frameworks_tested', 0)}")
        print(f"  • Successful frameworks: {exec_summary.get('successful_frameworks', 0)}")
        print(f"  • Test files executed: {exec_summary.get('total_test_files_executed', 0)}")
        
        # Framework execution details
        for framework, result in framework_results.items():
            status = "✅" if result.get('success', False) else "❌"
            passed = result.get('passed_tests', 0)
            failed = result.get('failed_tests', 0)
            exec_time = result.get('execution_time', 0)
            print(f"    {status} {framework.title()}: {passed} passed, {failed} failed ({exec_time:.1f}s)")
    
    print("\n🚀 NEXT STEPS:")
    if test_results:
        output_dir = test_results.get('output_directory', 'generated_tests')
        if execution_results and execution_results.get('execution_summary', {}).get('successful_frameworks', 0) > 0:
            print(f"  ✅ Tests are working! You can now:")
            print(f"  1. Review working tests: ls -la {output_dir}/")
            print(f"  2. Integrate into CI/CD pipeline")
            print(f"  3. Run locally: cd {output_dir}/playwright && npx playwright test")
        else:
            print(f"  1. Review generated tests: ls -la {output_dir}/")
            print(f"  2. Install dependencies:")
            print(f"     cd {output_dir}/playwright && npm install")
            print(f"  3. Run tests:")
            print(f"     npx playwright test")
            print(f"  4. Debug any failing tests")
    else:
        print("  1. Review exploration results in session directory")
        print("  2. Try running again with increased exploration depth")
        print("  3. Check if the website has sufficient interactive elements")
    
    print("="*70)


async def run_generated_tests(output_dir: Path, frameworks: list = None) -> Dict[str, Any]:
    """
    Execute the generated tests and return results.
    
    Args:
        output_dir: Directory containing generated test files
        frameworks: List of frameworks to run tests for
        
    Returns:
        Dictionary containing test execution results
    """
    if frameworks is None:
        frameworks = ['playwright']  # Default to Playwright for fastest execution
    
    test_results = {
        'execution_summary': {
            'total_frameworks_tested': 0,
            'successful_frameworks': 0,
            'failed_frameworks': 0,
            'total_test_files_executed': 0,
            'execution_timestamp': time.time()
        },
        'framework_results': {}
    }
    
    logger.info(f"🧪 POST-GENERATION: Starting test execution for {len(frameworks)} frameworks")
    
    for framework in frameworks:
        framework_dir = output_dir / framework
        if not framework_dir.exists():
            logger.warning(f"Framework directory not found: {framework_dir}")
            continue
            
        logger.info(f"🎯 Executing {framework} tests in {framework_dir}")
        framework_result = await _run_framework_tests(framework, framework_dir)
        
        test_results['framework_results'][framework] = framework_result
        test_results['execution_summary']['total_frameworks_tested'] += 1
        test_results['execution_summary']['total_test_files_executed'] += framework_result.get('test_files_count', 0)
        
        if framework_result.get('success', False):
            test_results['execution_summary']['successful_frameworks'] += 1
        else:
            test_results['execution_summary']['failed_frameworks'] += 1
    
    logger.info(f"✅ POST-GENERATION: Test execution complete - {test_results['execution_summary']['successful_frameworks']}/{test_results['execution_summary']['total_frameworks_tested']} frameworks passed")
    
    return test_results


async def _run_framework_tests(framework: str, framework_dir: Path) -> Dict[str, Any]:
    """Run tests for a specific framework."""
    result = {
        'framework': framework,
        'success': False,
        'test_files_count': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'execution_time': 0,
        'output': '',
        'error': ''
    }
    
    try:
        # Count test files
        if framework == 'playwright':
            test_files = list(framework_dir.glob('*.spec.ts'))
        elif framework == 'cypress':
            test_files = list(framework_dir.glob('*.cy.js'))
        elif framework == 'jest':
            test_files = list(framework_dir.glob('*.test.js'))
        else:
            test_files = []
            
        result['test_files_count'] = len(test_files)
        
        if not test_files:
            result['error'] = 'No test files found'
            return result
        
        # Install dependencies
        logger.info(f"📦 Installing {framework} dependencies...")
        install_start = time.time()
        
        if framework == 'playwright':
            # Install npm dependencies
            install_result = subprocess.run(
                ['npm', 'install'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=180  # 3 minutes timeout
            )
            if install_result.returncode != 0:
                result['error'] = f"npm install failed: {install_result.stderr}"
                return result
                
            # Install Playwright browsers (with timeout)
            browser_install = subprocess.run(
                ['npx', 'playwright', 'install', '--with-deps'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minutes timeout
            )
            
        elif framework == 'cypress':
            install_result = subprocess.run(
                ['npm', 'install', 'cypress'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=180
            )
            if install_result.returncode != 0:
                result['error'] = f"npm install cypress failed: {install_result.stderr}"
                return result
                
        elif framework == 'jest':
            install_result = subprocess.run(
                ['npm', 'install', 'jest', 'puppeteer'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=180
            )
            if install_result.returncode != 0:
                result['error'] = f"npm install jest failed: {install_result.stderr}"
                return result
        
        # Run tests
        logger.info(f"🏃 Running {framework} tests...")
        test_start = time.time()
        
        test_result = None  # Initialize to avoid undefined variable
        
        if framework == 'playwright':
            test_result = subprocess.run(
                ['npx', 'playwright', 'test', '--reporter=json'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minutes timeout for test execution
            )
        elif framework == 'cypress':
            test_result = subprocess.run(
                ['npx', 'cypress', 'run', '--reporter', 'json'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=300
            )
        elif framework == 'jest':
            test_result = subprocess.run(
                ['npx', 'jest', '--json'], 
                cwd=framework_dir, 
                capture_output=True, 
                text=True, 
                timeout=300
            )
        
        if test_result is None:
            result['error'] = f"Unsupported framework: {framework}"
            return result
            
        result['execution_time'] = time.time() - test_start
        result['output'] = test_result.stdout
        
        # Parse test results (basic parsing - could be enhanced)
        if test_result.returncode == 0:
            result['success'] = True
            # Try to parse JSON output for more details
            try:
                if framework == 'playwright':
                    test_data = json.loads(test_result.stdout)
                    if 'stats' in test_data:
                        result['passed_tests'] = test_data['stats'].get('passed', 0)
                        result['failed_tests'] = test_data['stats'].get('failed', 0)
                elif framework == 'jest':
                    test_data = json.loads(test_result.stdout)
                    result['passed_tests'] = test_data.get('numPassedTests', 0)
                    result['failed_tests'] = test_data.get('numFailedTests', 0)
            except json.JSONDecodeError:
                # Fallback to basic success/failure
                result['passed_tests'] = len(test_files)  # Assume all passed if returncode is 0
                
        else:
            result['error'] = test_result.stderr or 'Tests failed'
            # Try to extract failure count from output
            result['failed_tests'] = len(test_files)
        
        logger.info(f"📊 {framework} results: {result['passed_tests']} passed, {result['failed_tests']} failed")
        
    except subprocess.TimeoutExpired:
        result['error'] = f"{framework} test execution timed out"
        logger.error(f"⏰ {framework} tests timed out")
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"❌ {framework} test execution failed: {e}")
    
    return result


def main():
    """Main entry point for the complete QA AI pipeline."""
    parser = argparse.ArgumentParser(
        description='QA AI - Complete Testing Pipeline (Exploration → Test Generation)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - full pipeline
  python main.py https://example.com
  
  # Advanced exploration options
  python main.py https://app.defi.space --headless --max-depth 4 --timeout 600
  
  # Custom test generation
  python main.py https://mysite.com --output-dir my_tests --frameworks playwright cypress
  
  # Exploration only (skip test generation)
  python main.py https://example.com --exploration-only
  
Complete Pipeline Output:
  exploration_sessions/[timestamp]/     # Exploration session data
  ├── reports/
  │   ├── session_report.json          # Raw exploration data
  │   ├── session_summary.txt          # Human readable summary
  │   └── test_generation_summary.json # Test generation results
  └── screenshots/                     # Error screenshots
  
  generated_tests/                     # Generated test files
  ├── playwright/
  │   ├── *.spec.ts                   # Playwright tests
  │   └── playwright.config.ts        # Configuration
  ├── cypress/
  │   ├── *.cy.js                     # Cypress tests
  │   └── cypress.config.js           # Configuration
  └── jest/
      ├── *.test.js                   # Jest tests
      └── package.json                # Dependencies
        """
    )
    
    # URL argument
    parser.add_argument('url', help='Base URL to explore and generate tests for')
    
    # Exploration options
    parser.add_argument('--headless', action='store_true',
                       help='Run browser in headless mode (default: visible)')
    parser.add_argument('--max-depth', type=int, default=3,
                       help='Maximum exploration depth (default: 3)')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Exploration timeout in seconds (default: 300)')
    parser.add_argument('--action-timeout', type=int, default=5000,
                       help='Individual action timeout in ms (default: 5000)')
    
    # Test generation options
    parser.add_argument('--output-dir', type=str, default='generated_tests',
                       help='Output directory for generated tests (default: generated_tests)')
    parser.add_argument('--frameworks', nargs='+', 
                       choices=['playwright', 'cypress', 'jest'],
                       default=['playwright', 'cypress', 'jest'],
                       help='Test frameworks to generate (default: all)')
    parser.add_argument('--run-tests', action='store_true',
                       help='Execute generated tests to validate they work (default: enabled)')
    parser.add_argument('--skip-test-execution', action='store_true',
                       help='Skip test execution phase (faster but no validation)')
    
    # Pipeline control
    parser.add_argument('--exploration-only', action='store_true',
                       help='Run only exploration phase, skip test generation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print banner
    print_banner()
    
    # Prepare options
    exploration_options = {
        'headless': args.headless,
        'max_depth': args.max_depth,
        'timeout': args.timeout,
        'action_timeout': args.action_timeout
    }
    
    generation_options = {
        'output_dir': args.output_dir,
        'frameworks': args.frameworks,
        'run_tests': args.run_tests and not args.skip_test_execution  # Enable test execution unless explicitly skipped
    }
    
    # Display configuration
    print(f"🔗 Target URL: {args.url}")
    print(f"🖥️  Browser Mode: {'Headless' if args.headless else 'Visible'}")
    print(f"🔍 Max Depth: {args.max_depth}")
    print(f"⏱️  Timeout: {args.timeout}s")
    print(f"🧪 Test Frameworks: {', '.join(args.frameworks)}")
    print(f"📁 Output Directory: {args.output_dir}")
    print(f"🚀 Pipeline Mode: {'Exploration Only' if args.exploration_only else 'Full Pipeline'}")
    print()
    
    try:
        start_time = time.time()
        
        if args.exploration_only:
            # Run only exploration
            print("🔍 Running exploration phase only...")
            results = asyncio.run(run_exploration(args.url, exploration_options))
            print("✅ Exploration completed. Use generate_tests_from_session.py to create tests.")
        else:
            # Run complete pipeline
            print("🚀 Running complete pipeline...")
            results = asyncio.run(run_complete_pipeline(
                args.url, 
                exploration_options, 
                generation_options
            ))
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Print comprehensive summary
        if not args.exploration_only:
            print_pipeline_summary(results)
        
        print(f"\n⏱️ Total execution time: {total_time:.1f} seconds")
        
        if results.get('status') == 'success':
            print("🎉 Pipeline completed successfully!")
            return 0
        elif results.get('status') == 'partial_success':
            print("⚠️ Pipeline partially completed (exploration succeeded, test generation failed)")
            return 1
        else:
            print("❌ Pipeline failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted by user")
        logger.info("Pipeline interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main()) 