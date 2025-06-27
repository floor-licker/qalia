#!/usr/bin/env python3
"""
State Coverage Validation Script

Validates that generated tests provide comprehensive coverage of all discovered states
from exploration sessions. Provides detailed analysis and reporting of coverage gaps.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators import TestCaseGenerator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the state coverage validation banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║             🎯 QA AI - State Coverage Validator              ║
║                                                              ║
║  🗺️  Comprehensive State Coverage Analysis                   ║  
║  📊 Gap Analysis & Coverage Reporting                        ║
║  🔍 Missing State Path Discovery                             ║
║  ✅ Complete Coverage Validation                             ║
╚══════════════════════════════════════════════════════════════╝
    """)


def analyze_state_coverage(session_dir: Path) -> Dict[str, Any]:
    """
    Analyze state coverage for a given exploration session.
    
    Args:
        session_dir: Path to exploration session directory
        
    Returns:
        Comprehensive state coverage analysis
    """
    logger.info(f"🔍 Analyzing state coverage for session: {session_dir.name}")
    
    # Load session data
    session_report_path = session_dir / "reports" / "session_report.json"
    if not session_report_path.exists():
        raise FileNotFoundError(f"Session report not found: {session_report_path}")
    
    with open(session_report_path, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    # Extract base URL and exploration data
    base_url = session_data.get('session_info', {}).get('base_url', 'https://example.com')
    exploration_data = session_data.get('exploration_results', {})
    
    # Generate test cases with state coverage
    logger.info("🧪 Generating tests with state coverage analysis...")
    generator = TestCaseGenerator(base_url, exploration_data)
    test_suites = generator.generate_test_cases()
    
    # Get detailed coverage report
    coverage_report = generator._validate_state_coverage()
    
    # Analyze uncovered states in detail
    uncovered_analysis = analyze_uncovered_states(generator)
    
    return {
        'session_info': {
            'session_id': session_data.get('session_info', {}).get('session_id'),
            'base_url': base_url,
            'session_dir': str(session_dir)
        },
        'coverage_summary': coverage_report,
        'uncovered_analysis': uncovered_analysis,
        'test_generation_summary': generator.generate_summary_report(),
        'recommendations': generate_coverage_recommendations(generator, coverage_report)
    }


def analyze_uncovered_states(generator: TestCaseGenerator) -> Dict[str, Any]:
    """
    Analyze uncovered states in detail to understand why they can't be reached.
    
    Args:
        generator: TestCaseGenerator instance with coverage analysis
        
    Returns:
        Detailed analysis of uncovered states
    """
    uncovered_states = generator._get_uncovered_states()
    analysis = {
        'total_uncovered': len(uncovered_states),
        'by_state_type': {},
        'unreachable_states': [],
        'orphaned_states': [],
        'modal_states': [],
        'detailed_states': []
    }
    
    for state_fp in uncovered_states:
        state_data = generator.discovered_states[state_fp]
        state_type = state_data.get('type', 'unknown')
        
        # Count by type
        analysis['by_state_type'][state_type] = analysis['by_state_type'].get(state_type, 0) + 1
        
        # Check if state is reachable
        path = generator._find_path_to_state(state_fp)
        
        state_info = {
            'fingerprint': state_fp,
            'type': state_type,
            'url': state_data.get('url', 'unknown'),
            'element_count': len(state_data.get('interactive_elements', [])),
            'has_path': path is not None,
            'path_length': len(path) if path else 0
        }
        
        if not path:
            if state_type == 'modal':
                analysis['modal_states'].append(state_info)
            elif not any(t['to_state'] == state_fp for t in generator.state_transitions):
                analysis['orphaned_states'].append(state_info)
            else:
                analysis['unreachable_states'].append(state_info)
        
        analysis['detailed_states'].append(state_info)
    
    return analysis


def generate_coverage_recommendations(generator: TestCaseGenerator, coverage_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate recommendations for improving state coverage.
    
    Args:
        generator: TestCaseGenerator instance
        coverage_report: Coverage analysis report
        
    Returns:
        List of actionable recommendations
    """
    recommendations = []
    
    if coverage_report['coverage_percentage'] < 100:
        uncovered_count = coverage_report['uncovered_states']
        
        recommendations.append({
            'type': 'coverage_gap',
            'priority': 'high' if uncovered_count > 5 else 'medium',
            'title': f'Improve State Coverage ({coverage_report["coverage_percentage"]:.1f}%)',
            'description': f'{uncovered_count} states remain uncovered by generated tests',
            'action': 'Add manual test cases or enhance exploration to reach uncovered states'
        })
        
        # Analyze specific recommendations based on uncovered state types
        uncovered_states = generator._get_uncovered_states()
        modal_states = [s for s in uncovered_states 
                       if generator.discovered_states[s].get('type') == 'modal']
        
        if modal_states:
            recommendations.append({
                'type': 'modal_coverage',
                'priority': 'medium',
                'title': f'Modal State Coverage ({len(modal_states)} modal states uncovered)',
                'description': 'Modal states may require specific trigger sequences',
                'action': 'Review modal trigger patterns and add explicit modal navigation tests'
            })
        
        form_states = [s for s in uncovered_states 
                      if generator.discovered_states[s].get('type') == 'form']
        
        if form_states:
            recommendations.append({
                'type': 'form_coverage',
                'priority': 'medium',
                'title': f'Form State Coverage ({len(form_states)} form states uncovered)',
                'description': 'Form states may require specific input combinations',
                'action': 'Add form filling test scenarios with various input combinations'
            })
    
    else:
        recommendations.append({
            'type': 'complete_coverage',
            'priority': 'low',
            'title': 'Complete State Coverage Achieved',
            'description': 'All discovered states are covered by generated tests',
            'action': 'Maintain current test coverage and monitor for new states'
        })
    
    # Performance recommendations
    total_tests = len(generator.all_test_cases)
    if total_tests > 50:
        recommendations.append({
            'type': 'test_optimization',
            'priority': 'medium',
            'title': f'Test Suite Optimization ({total_tests} total tests)',
            'description': 'Large test suite may impact execution time',
            'action': 'Consider grouping similar tests or running in parallel'
        })
    
    return recommendations


def print_coverage_report(analysis: Dict[str, Any]) -> None:
    """Print a comprehensive coverage report."""
    print("\n" + "="*70)
    print("🎯 STATE COVERAGE ANALYSIS REPORT")
    print("="*70)
    
    session_info = analysis['session_info']
    coverage = analysis['coverage_summary']
    uncovered = analysis['uncovered_analysis']
    
    print(f"📋 Session: {session_info['session_id']}")
    print(f"🔗 Base URL: {session_info['base_url']}")
    print(f"📁 Session Dir: {session_info['session_dir']}")
    
    print(f"\n📊 COVERAGE STATISTICS:")
    print(f"  • Total States Discovered: {coverage['total_states']}")
    print(f"  • States Covered by Tests: {coverage['covered_states']}")
    print(f"  • Coverage Percentage: {coverage['coverage_percentage']:.1f}%")
    print(f"  • Uncovered States: {coverage['uncovered_states']}")
    
    if coverage['uncovered_states'] > 0:
        print(f"\n🔍 UNCOVERED STATE ANALYSIS:")
        print(f"  • Total Uncovered: {uncovered['total_uncovered']}")
        
        by_type = uncovered['by_state_type']
        for state_type, count in by_type.items():
            print(f"  • {state_type.title()} States: {count}")
        
        if uncovered['orphaned_states']:
            print(f"  • Orphaned States: {len(uncovered['orphaned_states'])} (no incoming transitions)")
        
        if uncovered['modal_states']:
            print(f"  • Modal States: {len(uncovered['modal_states'])} (may need specific triggers)")
        
        if uncovered['unreachable_states']:
            print(f"  • Unreachable States: {len(uncovered['unreachable_states'])} (no path found)")
    
    print(f"\n📝 RECOMMENDATIONS:")
    recommendations = analysis['recommendations']
    for i, rec in enumerate(recommendations, 1):
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "⚪")
        print(f"  {i}. {priority_emoji} {rec['title']}")
        print(f"     {rec['description']}")
        print(f"     Action: {rec['action']}")
        print()
    
    if coverage['coverage_percentage'] == 100:
        print("🎉 COMPLETE STATE COVERAGE ACHIEVED!")
        print("All discovered states are reachable by generated tests.")
    else:
        print(f"⚠️  COVERAGE GAP: {coverage['uncovered_states']} states need attention")
    
    print("="*70)


def main():
    """Main entry point for state coverage validation."""
    parser = argparse.ArgumentParser(
        description='Validate state coverage for QA AI generated tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate latest session
  python validate_state_coverage.py --latest

  # Validate specific session
  python validate_state_coverage.py --session-dir exploration_sessions/defi_space_20250611_100320

  # Validate with detailed output
  python validate_state_coverage.py --latest --detailed

Output:
  • Coverage percentage for all discovered states
  • Analysis of uncovered states by type
  • Recommendations for improving coverage
  • Detailed breakdown of unreachable states
        """
    )
    
    parser.add_argument('--session-dir', type=Path,
                       help='Specific session directory to analyze')
    parser.add_argument('--latest', action='store_true',
                       help='Analyze latest exploration session')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed analysis of each uncovered state')
    parser.add_argument('--export', type=Path,
                       help='Export analysis to JSON file')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Determine session directory
    if args.session_dir:
        session_dir = args.session_dir
    elif args.latest:
        sessions_dir = Path("exploration_sessions")
        if not sessions_dir.exists():
            print("❌ No exploration_sessions directory found")
            return 1
        
        session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        if not session_dirs:
            print("❌ No exploration sessions found")
            return 1
        
        # Get latest session
        session_dir = max(session_dirs, key=lambda d: d.stat().st_mtime)
        print(f"📂 Using latest session: {session_dir.name}")
    else:
        print("❌ Please specify --session-dir or --latest")
        return 1
    
    if not session_dir.exists():
        print(f"❌ Session directory not found: {session_dir}")
        return 1
    
    try:
        # Analyze state coverage
        analysis = analyze_state_coverage(session_dir)
        
        # Print comprehensive report
        print_coverage_report(analysis)
        
        # Show detailed uncovered states if requested
        if args.detailed and analysis['uncovered_analysis']['total_uncovered'] > 0:
            print("\n🔍 DETAILED UNCOVERED STATE ANALYSIS:")
            print("-" * 50)
            
            for state_info in analysis['uncovered_analysis']['detailed_states']:
                print(f"State: {state_info['fingerprint'][:12]}...")
                print(f"  Type: {state_info['type']}")
                print(f"  URL: {state_info['url']}")
                print(f"  Elements: {state_info['element_count']}")
                print(f"  Reachable: {'Yes' if state_info['has_path'] else 'No'}")
                if state_info['has_path']:
                    print(f"  Path Length: {state_info['path_length']} steps")
                print()
        
        # Export analysis if requested
        if args.export:
            with open(args.export, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"📄 Analysis exported to: {args.export}")
        
        # Return appropriate exit code
        coverage_percentage = analysis['coverage_summary']['coverage_percentage']
        if coverage_percentage == 100:
            print("✅ State coverage validation passed!")
            return 0
        else:
            print(f"⚠️  State coverage validation completed with gaps ({coverage_percentage:.1f}%)")
            return 0  # Still success, just with warnings
        
    except Exception as e:
        print(f"❌ State coverage validation failed: {e}")
        logger.error(f"Validation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 