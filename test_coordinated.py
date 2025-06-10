#!/usr/bin/env python3
"""
Simple test to verify coordinated exploration imports work correctly.
"""

import asyncio
import logging

# Test basic imports
def test_imports():
    """Test that we can import the coordinated exploration components."""
    try:
        print("Testing imports...")
        
        # Test individual components
        from coordinated_explorer import WorkItem, SharedWorkQueue
        print("✅ WorkItem and SharedWorkQueue imported successfully")
        
        from state_store import StateStore
        print("✅ StateStore imported successfully")
        
        from state_fingerprint import StateGraph, UIState
        print("✅ StateGraph and UIState imported successfully")
        
        # Test main classes
        from coordinated_explorer import CoordinatedWebAgent, CoordinatedWebExplorer
        print("✅ Main coordinated exploration classes imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_work_queue():
    """Test the SharedWorkQueue functionality."""
    try:
        print("\nTesting SharedWorkQueue...")
        
        from coordinated_explorer import WorkItem, SharedWorkQueue
        from datetime import datetime
        
        # Create work queue
        queue = SharedWorkQueue()
        
        # Create test work item
        work_item = WorkItem(
            item_id="test_001",
            item_type="url",
            target="https://example.com",
            priority=10,
            estimated_effort=5,
            dependencies=[],
            created_at=datetime.now().isoformat()
        )
        
        # Test queue operations
        queue.add_work_item(work_item)
        print("✅ Work item added successfully")
        
        # Test claiming work
        claimed = queue.claim_next_work("test_agent")
        assert claimed is not None, "Should have claimed work item"
        assert claimed.item_id == "test_001", "Should claim correct item"
        print("✅ Work item claimed successfully")
        
        # Test completion
        queue.complete_work_item("test_001", {"status": "completed"})
        print("✅ Work item completed successfully")
        
        # Test stats
        stats = queue.get_progress_stats()
        assert stats['total_items'] == 1, "Should have 1 total item"
        assert stats['completed'] == 1, "Should have 1 completed item"
        print("✅ Work queue stats working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ WorkQueue test failed: {e}")
        return False

async def test_basic_coordinator():
    """Test basic coordinator initialization."""
    try:
        print("\nTesting CoordinatedWebExplorer initialization...")
        
        # This should work even if explorer.py has issues
        from coordinated_explorer import CoordinatedWebExplorer
        
        coordinator = CoordinatedWebExplorer(
            start_url="https://example.com", 
            num_agents=2,
            config={'headless': True}
        )
        
        print("✅ CoordinatedWebExplorer initialized successfully")
        print(f"  - Start URL: {coordinator.start_url}")
        print(f"  - Number of agents: {coordinator.num_agents}")
        print(f"  - Shared state initialized: {coordinator.shared_state is not None}")
        print(f"  - Shared queue initialized: {coordinator.shared_queue is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Coordinator test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Coordinated Multi-Agent Web Exploration System")
    print("=" * 60)
    
    # Run tests
    tests = [
        test_imports,
        test_work_queue,
        lambda: asyncio.run(test_basic_coordinator())
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Coordinated exploration system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 