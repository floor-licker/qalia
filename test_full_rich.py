import asyncio
from explorers.basic_explorer import CleanWebExplorer, ExplorationConfig

async def test_full_rich_detection():
    config = ExplorationConfig(
        max_actions_per_page=3,
        headless=True,
        capture_screenshots=True
    )
    
    explorer = CleanWebExplorer('https://httpbin.org/', config)
    
    try:
        print('🚀 Starting full rich state detection test...')
        results = await explorer.explore()
        
        actions = results.get('detailed_results', {}).get('executed_actions', [])
        print(f'📊 Executed {len(actions)} actions with rich state detection')
        
        for i, action in enumerate(actions[:2]):  # Show first 2 actions
            print(f'\nAction {i+1}:')
            print(f'  Element: {action.get("element_type", "unknown")} - {action.get("text", "no text")[:30]}')
            print(f'  Success: {action.get("success", False)}')
            
            # Rich state assessment
            assessment = action.get('success_assessment', {})
            if assessment:
                print(f'  Rich Assessment: {assessment.get("success", "N/A")} (confidence: {assessment.get("confidence", 0):.1%})')
                print(f'  Reasoning: {assessment.get("reasoning", "N/A")}')
            
            # State changes
            changes = action.get('state_changes', [])
            print(f'  State Changes: {len(changes)}')
            for j, change in enumerate(changes[:2]):  # Show first 2 changes
                print(f'    {j+1}. {change.get("change_type", "unknown")}: {change.get("description", "N/A")}')
        
        print('\n✅ Full rich state detection test completed!')
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await explorer._cleanup()

if __name__ == "__main__":
    asyncio.run(test_full_rich_detection()) 