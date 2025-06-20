#!/usr/bin/env python3
"""
GitHub Actions Workflow Generator for Qalia Test Integration
Creates workflow files that run the generated tests as separate GitHub checks
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any

class WorkflowGenerator:
    """Generates GitHub Actions workflows for running generated tests."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.workflows_dir = self.repo_path / ".github" / "workflows"
        
    def generate_test_workflows(self, frameworks: List[str], test_results_dir: str = "qalia-tests") -> List[Path]:
        """
        Generate GitHub Actions workflows for each test framework.
        
        Args:
            frameworks: List of frameworks to create workflows for
            test_results_dir: Directory where test files are located
            
        Returns:
            List of created workflow file paths
        """
        created_workflows = []
        
        # Ensure workflows directory exists
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        for framework in frameworks:
            workflow_path = self._create_framework_workflow(framework, test_results_dir)
            if workflow_path:
                created_workflows.append(workflow_path)
                
        return created_workflows
    
    def _create_framework_workflow(self, framework: str, test_dir: str) -> Path:
        """Create a GitHub Actions workflow for a specific framework."""
        
        if framework == "playwright":
            return self._create_playwright_workflow(test_dir)
        elif framework == "cypress":
            return self._create_cypress_workflow(test_dir)
        elif framework == "jest":
            return self._create_jest_workflow(test_dir)
        else:
            print(f"⚠️ Unsupported framework: {framework}")
            return None
    
    def _create_playwright_workflow(self, test_dir: str) -> Path:
        """Create Playwright test workflow."""
        workflow = {
            "name": "🎭 Qalia Playwright Tests",
            "on": {
                "repository_dispatch": {
                    "types": ["qalia-test-playwright"]
                },
                "pull_request": {
                    "branches": ["main", "master", "develop"]
                },
                "push": {
                    "branches": ["main", "master"]
                },
                "workflow_dispatch": None
            },
            "jobs": {
                "playwright-tests": {
                    "name": "Run Playwright Tests",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout code",
                            "uses": "actions/checkout@v4",
                            "with": {
                                "ref": "${{ github.event.client_payload.commit_sha || github.sha }}"
                            }
                        },
                        {
                            "name": "Setup Node.js",
                            "uses": "actions/setup-node@v4",
                            "with": {
                                "node-version": "18",
                                "cache": "npm",
                                "cache-dependency-path": f"{test_dir}/playwright/package-lock.json"
                            }
                        },
                        {
                            "name": "Check if tests exist",
                            "id": "check-tests",
                            "run": f"""
                                if [ -d "{test_dir}/playwright" ] && [ -f "{test_dir}/playwright/package.json" ]; then
                                    echo "exists=true" >> $GITHUB_OUTPUT
                                    echo "✅ Playwright tests found"
                                else
                                    echo "exists=false" >> $GITHUB_OUTPUT
                                    echo "⚠️ Playwright tests not found - skipping"
                                fi
                            """
                        },
                        {
                            "name": "Install dependencies",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/playwright && npm ci"
                        },
                        {
                            "name": "Install Playwright browsers",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/playwright && npx playwright install --with-deps"
                        },
                        {
                            "name": "Run Playwright tests",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/playwright && npx playwright test",
                            "env": {
                                "CI": "true"
                            }
                        },
                        {
                            "name": "Upload Playwright Report",
                            "uses": "actions/upload-artifact@v4",
                            "if": "always() && steps.check-tests.outputs.exists == 'true'",
                            "with": {
                                "name": "playwright-report",
                                "path": f"{test_dir}/playwright/playwright-report/",
                                "retention-days": 30
                            }
                        }
                    ]
                }
            }
        }
        
        workflow_path = self.workflows_dir / "qalia-playwright-tests.yml"
        self._write_workflow(workflow_path, workflow)
        return workflow_path
    
    def _create_cypress_workflow(self, test_dir: str) -> Path:
        """Create Cypress test workflow."""
        workflow = {
            "name": "🌲 Qalia Cypress Tests", 
            "on": {
                "repository_dispatch": {
                    "types": ["qalia-test-cypress"]
                },
                "pull_request": {
                    "branches": ["main", "master", "develop"]
                },
                "push": {
                    "branches": ["main", "master"]
                },
                "workflow_dispatch": None
            },
            "jobs": {
                "cypress-tests": {
                    "name": "Run Cypress Tests",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout code",
                            "uses": "actions/checkout@v4",
                            "with": {
                                "ref": "${{ github.event.client_payload.commit_sha || github.sha }}"
                            }
                        },
                        {
                            "name": "Setup Node.js",
                            "uses": "actions/setup-node@v4",
                            "with": {
                                "node-version": "18",
                                "cache": "npm",
                                "cache-dependency-path": f"{test_dir}/cypress/package-lock.json"
                            }
                        },
                        {
                            "name": "Check if tests exist",
                            "id": "check-tests",
                            "run": f"""
                                if [ -d "{test_dir}/cypress" ] && [ -f "{test_dir}/cypress/package.json" ]; then
                                    echo "exists=true" >> $GITHUB_OUTPUT
                                    echo "✅ Cypress tests found"
                                else
                                    echo "exists=false" >> $GITHUB_OUTPUT
                                    echo "⚠️ Cypress tests not found - skipping"
                                fi
                            """
                        },
                        {
                            "name": "Install dependencies",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/cypress && npm ci"
                        },
                        {
                            "name": "Run Cypress tests",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/cypress && npx cypress run",
                            "env": {
                                "CI": "true"
                            }
                        },
                        {
                            "name": "Upload Cypress Screenshots",
                            "uses": "actions/upload-artifact@v4",
                            "if": "failure() && steps.check-tests.outputs.exists == 'true'",
                            "with": {
                                "name": "cypress-screenshots",
                                "path": f"{test_dir}/cypress/cypress/screenshots"
                            }
                        },
                        {
                            "name": "Upload Cypress Videos",
                            "uses": "actions/upload-artifact@v4",
                            "if": "always() && steps.check-tests.outputs.exists == 'true'",
                            "with": {
                                "name": "cypress-videos", 
                                "path": f"{test_dir}/cypress/cypress/videos"
                            }
                        }
                    ]
                }
            }
        }
        
        workflow_path = self.workflows_dir / "qalia-cypress-tests.yml"
        self._write_workflow(workflow_path, workflow)
        return workflow_path
    
    def _create_jest_workflow(self, test_dir: str) -> Path:
        """Create Jest test workflow."""
        workflow = {
            "name": "🃏 Qalia Jest Tests",
            "on": {
                "repository_dispatch": {
                    "types": ["qalia-test-jest"]
                },
                "pull_request": {
                    "branches": ["main", "master", "develop"]
                },
                "push": {
                    "branches": ["main", "master"]
                },
                "workflow_dispatch": None
            },
            "jobs": {
                "jest-tests": {
                    "name": "Run Jest Tests",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout code", 
                            "uses": "actions/checkout@v4",
                            "with": {
                                "ref": "${{ github.event.client_payload.commit_sha || github.sha }}"
                            }
                        },
                        {
                            "name": "Setup Node.js",
                            "uses": "actions/setup-node@v4",
                            "with": {
                                "node-version": "18",
                                "cache": "npm",
                                "cache-dependency-path": f"{test_dir}/jest/package-lock.json"
                            }
                        },
                        {
                            "name": "Check if tests exist",
                            "id": "check-tests",
                            "run": f"""
                                if [ -d "{test_dir}/jest" ] && [ -f "{test_dir}/jest/package.json" ]; then
                                    echo "exists=true" >> $GITHUB_OUTPUT
                                    echo "✅ Jest tests found"
                                else
                                    echo "exists=false" >> $GITHUB_OUTPUT
                                    echo "⚠️ Jest tests not found - skipping"
                                fi
                            """
                        },
                        {
                            "name": "Install dependencies",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/jest && npm ci"
                        },
                        {
                            "name": "Run Jest tests",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/jest && npm test",
                            "env": {
                                "CI": "true"
                            }
                        },
                        {
                            "name": "Upload Jest Coverage",
                            "uses": "actions/upload-artifact@v4",
                            "if": "always() && steps.check-tests.outputs.exists == 'true'",
                            "with": {
                                "name": "jest-coverage",
                                "path": f"{test_dir}/jest/coverage/"
                            }
                        }
                    ]
                }
            }
        }
        
        workflow_path = self.workflows_dir / "qalia-jest-tests.yml"
        self._write_workflow(workflow_path, workflow)
        return workflow_path
    
    def _write_workflow(self, path: Path, workflow: Dict[str, Any]) -> None:
        """Write workflow to YAML file."""
        with open(path, 'w') as f:
            yaml.dump(workflow, f, default_flow_style=False, sort_keys=False, indent=2)
        print(f"✅ Created workflow: {path}")
    
    def create_test_integration_workflow(self, test_dir: str = "qalia-tests") -> Path:
        """
        Create a comprehensive workflow that runs all generated tests.
        This shows up as a single check that runs all frameworks.
        """
        workflow = {
            "name": "🤖 Qalia Generated Tests",
            "on": {
                "repository_dispatch": {
                    "types": ["qalia-test-matrix"]
                },
                "pull_request": {
                    "branches": ["main", "master", "develop"]
                },
                "push": {
                    "branches": ["main", "master"]
                },
                "workflow_dispatch": None
            },
            "jobs": {
                "test-matrix": {
                    "name": "Test ${{ matrix.framework }}",
                    "runs-on": "ubuntu-latest",
                    "strategy": {
                        "fail-fast": False,
                        "matrix": {
                            "framework": ["playwright", "cypress", "jest"]
                        }
                    },
                    "steps": [
                        {
                            "name": "Checkout code",
                            "uses": "actions/checkout@v4",
                            "with": {
                                "ref": "${{ github.event.client_payload.commit_sha || github.sha }}"
                            }
                        },
                        {
                            "name": "Setup Node.js",
                            "uses": "actions/setup-node@v4",
                            "with": {
                                "node-version": "18"
                            }
                        },
                        {
                            "name": "Check if framework tests exist",
                            "id": "check-tests",
                            "run": f"""
                                if [ -d "{test_dir}/${{{{ matrix.framework }}}}" ] && [ -f "{test_dir}/${{{{ matrix.framework }}}}/package.json" ]; then
                                    echo "exists=true" >> $GITHUB_OUTPUT
                                    echo "✅ ${{{{ matrix.framework }}}} tests found"
                                else
                                    echo "exists=false" >> $GITHUB_OUTPUT
                                    echo "⚠️ ${{{{ matrix.framework }}}} tests not found"
                                fi
                            """
                        },
                        {
                            "name": "Install dependencies",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"cd {test_dir}/${{{{ matrix.framework }}}} && npm ci"
                        },
                        {
                            "name": "Install Playwright browsers",
                            "if": "steps.check-tests.outputs.exists == 'true' && matrix.framework == 'playwright'",
                            "run": f"cd {test_dir}/playwright && npx playwright install --with-deps"
                        },
                        {
                            "name": "Run tests",
                            "if": "steps.check-tests.outputs.exists == 'true'",
                            "run": f"""
                                cd {test_dir}/${{{{ matrix.framework }}}}
                                case "${{{{ matrix.framework }}}}" in
                                  "playwright")
                                    npx playwright test
                                    ;;
                                  "cypress")
                                    npx cypress run
                                    ;;
                                  "jest")
                                    npm test
                                    ;;
                                esac
                            """,
                            "env": {
                                "CI": "true"
                            }
                        },
                        {
                            "name": "Upload test artifacts",
                            "uses": "actions/upload-artifact@v4",
                            "if": "always() && steps.check-tests.outputs.exists == 'true'",
                            "with": {
                                "name": "${{ matrix.framework }}-results",
                                "path": f"{test_dir}/${{{{ matrix.framework }}}}/test-results/"
                            }
                        }
                    ]
                }
            }
        }
        
        workflow_path = self.workflows_dir / "qalia-generated-tests.yml"
        self._write_workflow(workflow_path, workflow)
        return workflow_path
    
    def commit_and_push_workflows(self, commit_message: str = "🤖 Add Qalia generated test workflows") -> None:
        """
        Commit and push the generated workflows to the repository.
        This requires git to be available and the repo to be initialized.
        """
        import subprocess
        
        try:
            # Add workflow files
            subprocess.run(["git", "add", ".github/workflows/qalia-*.yml"], 
                         cwd=self.repo_path, check=True)
            
            # Commit
            subprocess.run(["git", "commit", "-m", commit_message], 
                         cwd=self.repo_path, check=True)
            
            # Push
            subprocess.run(["git", "push"], cwd=self.repo_path, check=True)
            
            print("✅ Workflows committed and pushed successfully!")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to commit/push workflows: {e}")
            print("You may need to manually commit and push the workflow files.")


def main():
    """Example usage of the WorkflowGenerator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate GitHub Actions workflows for Qalia tests")
    parser.add_argument("repo_path", help="Path to the repository")
    parser.add_argument("--frameworks", nargs="+", 
                       choices=["playwright", "cypress", "jest"],
                       default=["playwright", "cypress", "jest"],
                       help="Frameworks to create workflows for")
    parser.add_argument("--test-dir", default="qalia-tests",
                       help="Directory containing test files")
    parser.add_argument("--commit", action="store_true",
                       help="Automatically commit and push the workflows")
    
    args = parser.parse_args()
    
    generator = WorkflowGenerator(args.repo_path)
    
    # Generate individual framework workflows
    workflows = generator.generate_test_workflows(args.frameworks, args.test_dir)
    
    # Generate comprehensive test matrix workflow
    matrix_workflow = generator.create_test_integration_workflow(args.test_dir)
    workflows.append(matrix_workflow)
    
    print(f"\n✅ Generated {len(workflows)} workflow files:")
    for workflow in workflows:
        print(f"   📄 {workflow}")
    
    if args.commit:
        generator.commit_and_push_workflows()
    else:
        print("\n🚀 Next steps:")
        print("   1. Review the generated workflow files")
        print("   2. Commit and push them to your repository:")
        print("      git add .github/workflows/qalia-*.yml")
        print("      git commit -m '🤖 Add Qalia generated test workflows'")
        print("      git push")


if __name__ == "__main__":
    main() 