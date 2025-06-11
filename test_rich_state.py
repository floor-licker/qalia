#!/usr/bin/env python3
"""
Test script to verify rich state detection integration
"""
import asyncio
from explorers.basic_explorer import CleanWebExplorer, ExplorationConfig

async def test_rich_state_detection():
    config = ExplorationConfig(
        max_actions_per_page=5,  # Just a few actions for testing
        headless=True,
        capture_screenshots=True,
        action_timeout=10000
    )
    
    explorer = CleanWebExplorer('https://app.uniswap.org', config)
    
    try:
        results = await explorer.explore()
        
        # Check if rich state detection data is present
        actions = results.get('detailed_results', {}).get('executed_actions', [])
        
        print(f'📊 Test Results:')
        print(f'   Total actions: {len(actions)}')
        
        if actions:
            first_action = actions[0]
            print(f'   Rich state fields present:')
            print(f'     • state_changes: {"state_changes" in first_action}')
            print(f'     • success_assessment: {"success_assessment" in first_action}')
            print(f'     • baseline_state: {"baseline_state" in first_action}')
            print(f'     • final_state: {"final_state" in first_action}')
            
            if first_action.get('state_changes'):
                print(f'     • Number of state changes: {len(first_action["state_changes"])}')
                for i, change in enumerate(first_action['state_changes'][:3]):
                    print(f'       - Change {i+1}: {change.get("description", "N/A")}')
            
            if first_action.get('success_assessment'):
                assessment = first_action['success_assessment']
                print(f'     • Rich success: {assessment.get("success", "N/A")}')
                print(f'     • Confidence: {assessment.get("confidence", "N/A")}')
                print(f'     • Reasoning: {assessment.get("reasoning", "N/A")}')
        
        rich_summary = results.get('detailed_results', {}).get('rich_state_detection', {})
        print(f'   Rich state detector initialized: {rich_summary.get("initialized", False)}')
        if rich_summary.get('initialized'):
            print(f'   Total changes detected: {rich_summary.get("total_changes_detected", 0)}')
        
        print('✅ Rich state detection integration test completed!')
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await explorer._cleanup()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_rich_state_detection()) 