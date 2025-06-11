#!/usr/bin/env python3
"""
Demo script to show what the GitHub Actions summary will look like
"""

def generate_demo_summary():
    summary = """# 🤖 QA AI Test Generation Report

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Target Application** | `http://localhost:8080` |
| **Test Cases Generated** | **4** |
| **Test Suites Created** | **2** |
| **Analysis Duration** | 97s |
| **Max Exploration Depth** | 30 |
| **Frameworks** | `playwright,cypress,jest` |

## 🎯 Generated Test Files

- 📝 `authentication_tests.test.js`
- 📝 `_tests.test.js`

## 📈 Detailed Analysis

### Test Case Breakdown

**By Priority:**
- 🔴 Critical: 1 test(s)
- 🟡 High: 1 test(s)
- 🟢 Medium: 2 test(s)

### Test Suites

**authentication_tests** - Test suite for authentication functionality
- Tests: 1
- Estimated Duration: 42s

**_tests** - Test suite for  functionality
- Tests: 3
- Estimated Duration: 90s

## 📁 Artifacts

Generated test files and reports are available as workflow artifacts:
1. Click on the **Summary** tab above
2. Scroll down to **Artifacts** section
3. Download the **qalia-test-results** archive

### Artifact Contents
- **Test Files**: Ready-to-run test cases for your CI/CD pipeline
- **Reports**: Detailed analysis and exploration session data
- **Configuration**: QA AI configuration used for generation
"""
    
    return summary

if __name__ == "__main__":
    print("Demo GitHub Actions Summary:")
    print("=" * 50)
    print(generate_demo_summary()) 