#!/usr/bin/env python3
"""
Test script for infinite loop prevention mechanisms.

This script tests various webhook payloads to ensure Qalia commits are properly detected
and infinite loops are prevented.
"""

import json
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from github_operations import GitHubManager

def test_qalia_commit_detection():
    """Test the is_qalia_commit function with various payload scenarios."""
    
    print("🔍 Testing Qalia commit detection...")
    
    # Initialize GitHub manager (dummy credentials for testing)
    github_manager = GitHubManager("dummy_app_id", "dummy_key")
    
    # Test Case 1: Push event with Qalia commit
    push_payload = {
        "head_commit": {
            "message": "🤖 Add Qalia generated tests and workflows\n\n- Generated test files for playwright, cypress, jest frameworks",
            "author": {
                "name": "Qalia AI",
                "email": "qalia@ai-generated.com"
            },
            "added": ["qalia-tests/playwright/test.spec.ts"],
            "modified": [".github/workflows/qalia-playwright-tests.yml"],
            "removed": []
        },
        "repository": {"name": "demo-web-app"}
    }
    
    result1 = github_manager.is_qalia_commit(push_payload)
    print(f"✅ Push with Qalia commit: {result1} (should be True)")
    
    # Test Case 2: PR event with Qalia commit
    pr_payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 123,
            "title": "🤖 Add Qalia generated tests and workflows",
            "head": {
                "commit": {
                    "message": "🤖 Add Qalia generated tests and workflows\n\n- Generated test files for playwright, cypress, jest frameworks",
                    "author": {
                        "name": "Qalia AI",
                        "email": "qalia@ai-generated.com"
                    }
                }
            },
            "commits": 1
        },
        "repository": {"name": "demo-web-app"}
    }
    
    result2 = github_manager.is_qalia_commit(pr_payload)
    print(f"✅ PR with Qalia commit: {result2} (should be True)")
    
    # Test Case 3: Normal user commit (should not be detected)
    normal_payload = {
        "head_commit": {
            "message": "Fix bug in user authentication",
            "author": {
                "name": "John Developer",
                "email": "john@example.com"
            },
            "added": ["src/auth.js"],
            "modified": ["package.json"],
            "removed": []
        },
        "repository": {"name": "demo-web-app"}
    }
    
    result3 = github_manager.is_qalia_commit(normal_payload)
    print(f"✅ Normal user commit: {result3} (should be False)")
    
    # Test Case 4: PR with no commit info (edge case)
    incomplete_pr_payload = {
        "action": "opened",
        "pull_request": {
            "number": 456,
            "title": "Add new feature",
            "head": {},
            "commits": 0
        },
        "repository": {"name": "demo-web-app"}
    }
    
    result4 = github_manager.is_qalia_commit(incomplete_pr_payload)
    print(f"✅ PR with incomplete data: {result4} (should be False)")
    
    # Test Case 5: Qalia-only file changes
    qalia_files_payload = {
        "head_commit": {
            "message": "Update test configurations",
            "author": {
                "name": "Regular User",
                "email": "user@example.com"
            },
            "added": [],
            "modified": [
                "qalia-tests/cypress/cypress.config.js",
                ".github/workflows/qalia-cypress-tests.yml"
            ],
            "removed": []
        },
        "repository": {"name": "demo-web-app"}
    }
    
    result5 = github_manager.is_qalia_commit(qalia_files_payload)
    print(f"✅ Qalia-only file changes: {result5} (should be True)")
    
    # Summary
    all_tests_passed = result1 and result2 and not result3 and not result4 and result5
    
    if all_tests_passed:
        print("\n🎉 All tests passed! Infinite loop prevention is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Check the logic in is_qalia_commit()")
        return False

def test_payload_structures():
    """Test different GitHub webhook payload structures."""
    
    print("\n📊 Testing different payload structures...")
    
    github_manager = GitHubManager("dummy_app_id", "dummy_key")
    
    # GitHub PR webhook structures can vary
    variations = [
        {
            "name": "Standard PR structure",
            "payload": {
                "action": "synchronize",
                "pull_request": {
                    "head": {
                        "commit": {
                            "message": "🤖 Add Qalia generated tests and workflows"
                        }
                    }
                }
            }
        },
        {
            "name": "PR with commits array",
            "payload": {
                "action": "synchronize",
                "pull_request": {"head": {}},
                "commits": [
                    {
                        "message": "🤖 Add Qalia generated tests and workflows"
                    }
                ]
            }
        },
        {
            "name": "PR title fallback",
            "payload": {
                "action": "synchronize",
                "pull_request": {
                    "title": "🤖 Add Qalia generated tests and workflows",
                    "head": {},
                    "commits": 1
                }
            }
        }
    ]
    
    for test in variations:
        result = github_manager.is_qalia_commit(test["payload"])
        print(f"✅ {test['name']}: {result} (should be True)")

if __name__ == "__main__":
    print("🧪 Starting infinite loop prevention tests...\n")
    
    success = test_qalia_commit_detection()
    test_payload_structures()
    
    if success:
        print("\n✨ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1) 