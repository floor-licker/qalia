#!/usr/bin/env python3
"""
Test the Minimal Web Explorer on defi.space
"""

import asyncio
import logging
import time
from minimal_explorer import MinimalWebExplorer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_defi_space():
    """Test comprehensive exploration of defi.space."""
    print("=" * 70)
    print("🔍 QA AI - Comprehensive Testing of defi.space")
    print("=" * 70)
    
    url = "https://defi.space"
    
    # Create explorer instance
    explorer = MinimalWebExplorer(
        base_url=url,
        max_actions_per_page=50,  # Test many elements to see comprehensive discovery
        headless=False  # Set to True for headless testing
    )
    
    try:
        print(f"🚀 Starting exploration of {url}")
        print(f"📁 Session directory: {explorer.session_manager.session_id}")
        print()
        
        # Run exploration
        start_time = time.time()
        results = await explorer.explore()
        end_time = time.time()
        
        if 'error' in results:
            print(f"❌ Exploration failed: {results['error']}")
            return
        
        # Print comprehensive results
        print("\n" + "=" * 70)
        print("📊 EXPLORATION RESULTS")
        print("=" * 70)
        
        summary = results['exploration_summary']
        print(f"⏱️  Duration: {results['duration']:.1f} seconds")
        print(f"🎯 Total Interactive Elements Found: {summary['total_elements']}")
        buttons = [e for e in results['discovered_elements'] if e['type'] == 'button']
        print(f"🔘 Buttons Discovered: {len(buttons)}")
        print(f"🔗 Links Found: {len([e for e in results['discovered_elements'] if e['type'] == 'link'])}")
        print(f"📝 Inputs Found: {len([e for e in results['discovered_elements'] if e['type'] == 'input'])}")
        print(f"⚡ Actions Performed: {summary['actions_performed']}")
        print(f"🐛 Bugs Found: {len(results['bugs_found'])}")
        print(f"⚠️  Warnings: {len(results['warnings'])}")
        
        print("\n📋 DETAILED ELEMENT BREAKDOWN:")
        print("-" * 40)
        
        # Show button details
        # buttons already defined above
        if buttons:
            print(f"\n🔘 BUTTONS ({len(buttons)}):")
            for i, btn in enumerate(buttons[:10]):  # Show first 10
                text = btn['text'][:50] if btn['text'] else 'No text'
                print(f"  {i+1:2d}. {text}")
            if len(buttons) > 10:
                print(f"     ... and {len(buttons) - 10} more buttons")
        
        # Show links
        links = [e for e in results['discovered_elements'] if e['type'] == 'link']
        if links:
            print(f"\n🔗 LINKS ({len(links)}):")
            for i, link in enumerate(links[:5]):  # Show first 5
                text = link['text'][:40] if link['text'] else link['href'][:40]
                print(f"  {i+1:2d}. {text}")
            if len(links) > 5:
                print(f"     ... and {len(links) - 5} more links")
        
        # Show inputs
        inputs = [e for e in results['discovered_elements'] if e['type'] == 'input']
        if inputs:
            print(f"\n📝 INPUTS ({len(inputs)}):")
            for i, inp in enumerate(inputs):
                name = inp['name'] if inp['name'] else f"input_{i}"
                input_type = inp.get('input_type', 'text')
                print(f"  {i+1:2d}. {name} (type: {input_type})")
        
        # Show any bugs or errors found
        if results['bugs_found']:
            print(f"\n🐛 BUGS FOUND ({len(results['bugs_found'])}):")
            for i, bug in enumerate(results['bugs_found']):
                print(f"  {i+1}. {bug['type']}: {bug.get('message', bug.get('url', 'Unknown'))}")
        
        # Session info
        session_info = results['session_info']
        print(f"\n📁 SESSION INFORMATION:")
        print(f"   Directory: {session_info['session_dir']}")
        print(f"   Session ID: {session_info['session_id']}")
        print(f"   Screenshots taken: {session_info['screenshots_taken']}")
        
        print("\n✅ Exploration completed successfully!")
        print(f"📂 Results saved to: {session_info['session_dir']}")
        
        # Assessment
        print("\n" + "=" * 70)
        print("🎯 ASSESSMENT")
        print("=" * 70)
        
        total_elements = summary['total_elements']
        buttons_found = len([e for e in results['discovered_elements'] if e['type'] == 'button'])
        
        if buttons_found >= 20:
            print(f"✅ EXCELLENT: Found {buttons_found} buttons (target: 20+)")
            print("   The explorer successfully discovered comprehensive UI elements!")
        elif buttons_found >= 10:
            print(f"✅ GOOD: Found {buttons_found} buttons (target: 20+)")
            print("   The explorer found a good number of UI elements.")
        else:
            print(f"⚠️  LIMITED: Found only {buttons_found} buttons (target: 20+)")
            print("   The explorer may need tuning for better element discovery.")
        
        print(f"\n🔍 Total UI coverage: {total_elements} interactive elements discovered")
        print("   This indicates the depth of UI exploration achieved.")
        
        return results
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")
        return None

if __name__ == "__main__":
    results = asyncio.run(test_defi_space())
    
    if results:
        print("\n🎉 Test completed - check the session directory for detailed results!")
    else:
        print("\n💥 Test failed - check logs for details") 