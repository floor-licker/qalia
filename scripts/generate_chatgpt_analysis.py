#!/usr/bin/env python3
"""
Generate ChatGPT Analysis XML from existing session data.

This script reads session JSON reports and generates detailed XML reports
suitable for ChatGPT analysis to detect bugs and unexpected behavior.
"""

import json
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session.manager import SessionManager


def find_latest_session(domain: str = None) -> Path:
    """Find the latest session directory."""
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


def generate_analysis_xml(session_dir: Path, output_path: Path = None) -> str:
    """Generate ChatGPT analysis XML from session data."""
    
    # Read session report
    report_path = session_dir / "reports" / "session_report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Session report not found: {report_path}")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    # Extract base URL and create SessionManager
    base_url = session_data.get('session_info', {}).get('base_url', 'unknown')
    session_manager = SessionManager(base_url)
    session_manager.session_id = session_data.get('session_info', {}).get('session_id', 'unknown')
    
    # Generate analysis XML
    exploration_results = session_data.get('exploration_results', {})
    analysis_xml = session_manager.generate_detailed_action_analysis_xml(exploration_results)
    
    # Save to file
    if output_path:
        output_file = output_path
    else:
        output_file = session_dir / "reports" / "action_analysis_for_chatgpt.xml"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(analysis_xml)
    
    print(f"✅ ChatGPT analysis XML generated: {output_file}")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(description="Generate ChatGPT analysis XML for bug detection")
    parser.add_argument("--session-dir", type=str, help="Specific session directory to analyze")
    parser.add_argument("--domain", type=str, help="Domain filter for finding latest session")
    parser.add_argument("--output", type=str, help="Output file path (default: session/reports/action_analysis_for_chatgpt.xml)")
    parser.add_argument("--print-xml", action="store_true", help="Print XML to console")
    
    args = parser.parse_args()
    
    try:
        # Determine session directory
        if args.session_dir:
            session_dir = Path(args.session_dir)
            if not session_dir.exists():
                raise FileNotFoundError(f"Session directory not found: {session_dir}")
        else:
            session_dir = find_latest_session(args.domain)
            print(f"📂 Using latest session: {session_dir}")
        
        # Generate XML
        output_path = Path(args.output) if args.output else None
        xml_file = generate_analysis_xml(session_dir, output_path)
        
        # Print XML if requested
        if args.print_xml:
            with open(xml_file, 'r', encoding='utf-8') as f:
                print("\n" + "="*80)
                print("CHATGPT ANALYSIS XML")
                print("="*80)
                print(f.read())
        
        print(f"\n🤖 Ready for ChatGPT analysis!")
        print(f"📄 Send this XML file to ChatGPT: {xml_file}")
        print("\n💡 Suggested ChatGPT prompt:")
        print("---")
        print("Please analyze this XML report from automated web testing.")
        print("Look for potential bugs, unexpected behavior, or performance issues.")
        print("For each anomaly you find, explain:")
        print("1. What the issue is")
        print("2. Why it might be problematic") 
        print("3. Recommended investigation steps")
        print("Focus on action->result pairs that seem unusual or concerning.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 