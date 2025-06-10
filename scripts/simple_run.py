#!/usr/bin/env python3
"""
Simple test demonstration of the QA AI system with session management.
This script shows how the session manager works independently.
"""

import asyncio
import logging
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_session_system():
    """Demonstrate the session management system."""
    print("🔍 QA AI - Session Management Demo")
    print("=" * 50)
    
    # Create session manager
    test_url = "https://example.com"
    session_manager = SessionManager(test_url)
    
    print(f"📁 Session created: {session_manager.session_id}")
    print(f"📂 Session directory: {session_manager.session_dir}")
    
    # Simulate exploration results
    mock_results = {
        'start_time': 1234567890,
        'end_time': 1234567950,
        'duration': 60.0,
        'exploration_status': 'completed',
        'base_url': test_url,
        'domain': 'example_com',
        'exploration_summary': {
            'total_pages_visited': 5,
            'total_actions_performed': 15,
            'bugs_found': 2,
            'warnings': 3,
            'console_messages': 8,
            'state_statistics': {
                'total_states_discovered': 7,
                'total_state_transitions': 12,
                'unique_state_fingerprints': 7
            }
        },
        'bugs_found': [
            {
                'type': 'http_error',
                'status_code': 500,
                'url': 'https://example.com/api/data',
                'timestamp': 1234567900,
                'screenshot': None,
                'error_details': 'HTTP_500'
            },
            {
                'type': 'console_error',
                'console_type': 'error',
                'message': 'TypeError: Cannot read property of undefined',
                'url': 'https://example.com/dashboard',
                'timestamp': 1234567920,
                'screenshot': None
            }
        ],
        'warnings': [
            {
                'type': 'action_timeout',
                'action': {'type': 'click', 'selector': 'button.submit'},
                'url': 'https://example.com/form',
                'timestamp': 1234567930,
                'screenshot': None
            }
        ],
        'state_fingerprints': ['a1b2c3d4', 'e5f6g7h8', 'i9j0k1l2'],
        'visited_urls': ['https://example.com', 'https://example.com/dashboard', 'https://example.com/form']
    }
    
    # Generate mock XML sitemap
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ApplicationStateFingerprint domain="example_com" total_states="7" total_transitions="12">
    <States>
        <State fingerprint="a1b2c3d4" type="page">
            <URL>https://example.com</URL>
            <PageHash>abc123def456</PageHash>
            <InteractiveElements count="5">
                <Buttons count="2"/>
                <Links count="3"/>
            </InteractiveElements>
        </State>
        <State fingerprint="e5f6g7h8" type="page">
            <URL>https://example.com/dashboard</URL>
            <PageHash>def456ghi789</PageHash>
            <InteractiveElements count="8">
                <Buttons count="4"/>
                <Links count="3"/>
                <Inputs count="1"/>
            </InteractiveElements>
        </State>
    </States>
    <Transitions count="12">
        <Transition from="a1b2c3d4" to="e5f6g7h8" action="click" element="nav-dashboard"/>
    </Transitions>
</ApplicationStateFingerprint>"""

    # Save the mock sitemap
    sitemap_path = session_manager.save_sitemap(mock_xml, "example_com")
    print(f"🗺️ Sitemap saved: {sitemap_path}")
    
    # Save the session report
    report_path = session_manager.save_session_report(mock_results)
    print(f"📋 Report saved: {report_path}")
    
    print("\n📊 SESSION SUMMARY:")
    print(f"  • Pages visited: {mock_results['exploration_summary']['total_pages_visited']}")
    print(f"  • Actions performed: {mock_results['exploration_summary']['total_actions_performed']}")
    print(f"  • Bugs found: {mock_results['exploration_summary']['bugs_found']}")
    print(f"  • Warnings: {mock_results['exploration_summary']['warnings']}")
    print(f"  • States discovered: {mock_results['exploration_summary']['state_statistics']['total_states_discovered']}")
    print(f"  • Error screenshots: {len(session_manager.screenshots_taken)}")
    
    print(f"\n📁 SESSION FILES:")
    print(f"  📂 Directory: {session_manager.session_dir}")
    print(f"  📋 JSON Report: reports/session_report.json")
    print(f"  📄 Text Summary: reports/session_summary.txt")
    print(f"  🗺️ XML Sitemap: reports/state_fingerprint_example_com.xml")
    if session_manager.screenshots_taken:
        print(f"  📸 Screenshots: screenshots/ ({len(session_manager.screenshots_taken)} files)")
    else:
        print(f"  ✅ No error screenshots (clean session)")
    
    session_info = session_manager.get_session_info()
    print(f"\n🔍 Session ID: {session_info['session_id']}")
    
    return session_manager.session_dir

def main():
    """Main demo function."""
    print("🚀 Starting QA AI Session Management Demo\n")
    
    try:
        session_dir = asyncio.run(demo_session_system())
        
        print("\n" + "="*50)
        print("✅ DEMO COMPLETED SUCCESSFULLY")
        print("="*50)
        print(f"\n💡 To explore the session files:")
        print(f"   open {session_dir}")
        print(f"   cat {session_dir}/reports/session_summary.txt")
        print(f"   open {session_dir}/reports/session_report.json")
        
        print(f"\n🎯 This demonstrates how each QA AI run will:")
        print(f"   • Create a unique timestamped session directory")
        print(f"   • Capture error screenshots when issues occur")
        print(f"   • Generate comprehensive XML state fingerprints")
        print(f"   • Provide both human-readable and JSON reports")
        print(f"   • Organize all files for easy access and analysis")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 