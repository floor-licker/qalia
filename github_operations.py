#!/usr/bin/env python3
"""
GitHub Operations Manager

Handles all GitHub-related functionality including:
- Authentication and client management
- Repository operations (cloning, committing)
- Check runs and PR comments
- Workflow triggering
"""

import os
import shutil
import tempfile
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import hmac
import hashlib
import jwt
import requests
from github import Github

from workflow_generator import WorkflowGenerator

logger = logging.getLogger(__name__)


class GitHubManager:
    """Manages all GitHub operations for the Qalia application."""
    
    def __init__(self, app_id: str, private_key: str, webhook_secret: Optional[str] = None):
        """
        Initialize GitHub manager.
        
        Args:
            app_id: GitHub App ID
            private_key: GitHub App private key (PEM format)
            webhook_secret: Optional webhook secret for signature verification
        """
        self.app_id = app_id
        self.private_key = private_key
        self.webhook_secret = webhook_secret
    
    def verify_webhook_signature(self, request_body: bytes, signature: str) -> bool:
        """Verify the webhook signature from GitHub."""
        if not self.webhook_secret:
            return True  # Skip verification if no secret is set
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            request_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    def get_client(self, installation_id: int) -> Tuple[Github, str]:
        """
        Get an authenticated GitHub client for the installation.
        
        Args:
            installation_id: GitHub App installation ID
            
        Returns:
            Tuple of (GitHub client, access token)
        """
        if not self.app_id:
            raise ValueError("GitHub App ID not configured")
        
        # Generate JWT
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + 600,  # 10 minutes
            "iss": self.app_id
        }
        
        jwt_token = jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256"
        )
        
        # Get installation access token using direct API call
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Qalia-GitHub-App"
        }
        
        response = requests.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers=headers
        )
        
        if response.status_code != 201:
            raise RuntimeError(
                f"Failed to get installation token: {response.status_code} {response.text}"
            )
        
        token_data = response.json()
        access_token = token_data["token"]
        
        # Return client with installation token and the token itself
        return Github(access_token), access_token
    
    async def clone_repository(self, repo_url: str, branch: str = "main", access_token: Optional[str] = None) -> Optional[str]:
        """
        Clone a repository to a temporary directory.
        
        Args:
            repo_url: Repository URL to clone
            branch: Branch to clone
            access_token: Optional access token for authentication
            
        Returns:
            Path to cloned repository or None if failed
        """
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Prepare the URL with authentication if token is provided
            if access_token:
                # Parse the URL and inject the token
                if repo_url.startswith("https://github.com/"):
                    auth_url = repo_url.replace("https://", f"https://x-access-token:{access_token}@")
                else:
                    auth_url = repo_url
            else:
                auth_url = repo_url
            
            # Clone the repository
            result = subprocess.run(
                ["git", "clone", "-b", branch, auth_url, temp_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to clone repository: {result.stderr}")
                return None
            
            logger.info(f"Repository cloned successfully to: {temp_dir}")
            return temp_dir
        
        except Exception as e:
            logger.error(f"Exception during repository cloning: {e}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
    
    async def commit_tests_and_workflows(
        self,
        repo_path: str, 
        test_results_dir: str, 
        frameworks: list,
        access_token: str,
        branch: str = "main"
    ) -> bool:
        """
        Commit generated tests and workflows to the repository.
        
        Args:
            repo_path: Local path to the cloned repository
            test_results_dir: Path to generated test files (relative to repo)
            frameworks: List of frameworks that have tests
            access_token: GitHub access token for authentication
            branch: Branch to commit to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            repo_path = Path(repo_path)
            
            # Copy generated tests to repository
            source_tests = Path(test_results_dir)
            target_tests = repo_path / "qalia-tests"
            
            if source_tests.exists():
                if target_tests.exists():
                    shutil.rmtree(target_tests)
                shutil.copytree(source_tests, target_tests)
                logger.info(f"Copied generated tests to {target_tests}")
            
            # Generate GitHub Actions workflows
            generator = WorkflowGenerator(str(repo_path))
            workflows = generator.generate_test_workflows(frameworks, "qalia-tests")
            matrix_workflow = generator.create_test_integration_workflow("qalia-tests")
            workflows.append(matrix_workflow)
            
            logger.info(f"Generated {len(workflows)} workflow files")
            
            # Configure git user (required for commits)
            subprocess.run(["git", "config", "user.name", "Qalia AI"], 
                          cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.email", "qalia@ai-generated.com"], 
                          cwd=repo_path, check=True)
            
            # Check if there are any changes to commit
            status_result = subprocess.run(["git", "status", "--porcelain"], 
                                         cwd=repo_path, capture_output=True, text=True)
            
            if not status_result.stdout.strip():
                logger.info("No changes to commit - tests and workflows are up to date")
                return True
            
            # PREVENT NODE_MODULES COMMITS: Create .gitignore in qalia-tests directory
            qalia_tests_dir = os.path.join(repo_path, "qalia-tests")
            if os.path.exists(qalia_tests_dir):
                # Remove any existing node_modules from git tracking
                try:
                    subprocess.run(["git", "rm", "-r", "--cached", "qalia-tests/*/node_modules"], 
                                  cwd=repo_path, capture_output=True)
                    logger.info("Removed node_modules directories from git tracking")
                except subprocess.CalledProcessError:
                    # node_modules might not exist in git yet, which is fine
                    pass
                
                gitignore_path = os.path.join(qalia_tests_dir, ".gitignore")
                gitignore_content = """# Node.js dependencies - should not be committed
node_modules/
*/node_modules/
package-lock.json
*/package-lock.json

# Test results and artifacts
test-results/
*/test-results/
playwright-report/
*/playwright-report/
coverage/
*/coverage/

# Temporary files
*.log
.DS_Store
.env
"""
                with open(gitignore_path, 'w', encoding='utf-8') as f:
                    f.write(gitignore_content)
                logger.info("Created .gitignore in qalia-tests directory to prevent node_modules commits")
            
            # Add all changes
            subprocess.run(["git", "add", "qalia-tests/", ".github/workflows/qalia-*.yml"], 
                          cwd=repo_path, check=True)
            
            # Create commit message
            commit_message = f"""🤖 Add Qalia generated tests and workflows

- Generated test files for {', '.join(frameworks)} frameworks
- Added GitHub Actions workflows for automated testing
- Tests can be run individually or as a complete suite

Generated by Qalia.ai on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            # Commit changes
            subprocess.run(["git", "commit", "-m", commit_message], 
                          cwd=repo_path, check=True)
            
            # Push to remote
            subprocess.run(["git", "push", "origin", branch], 
                          cwd=repo_path, check=True)
            
            logger.info("Successfully committed and pushed generated tests and workflows")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to commit tests and workflows: {e}")
            return False
    
    async def create_check_run(self, repo_name: str, commit_sha: str, analysis_results: Dict[str, Any]) -> None:
        """
        Create a GitHub check run with QA AI results.
        
        Args:
            repo_name: Repository name (owner/repo)
            commit_sha: Commit SHA to create check run for
            analysis_results: Analysis results from QA AI
        """
        # Extract installation_id from analysis_results or use a stored one
        # For now, we'll need to get the client differently
        # This will need to be refactored when we extract the analysis service
        pass  # Implementation will be moved here from app.py
    
    async def comment_on_pr(self, repo_name: str, pr_number: int, analysis_results: Dict[str, Any]) -> None:
        """
        Comment on a pull request with QA AI results.
        
        Args:
            repo_name: Repository name (owner/repo)
            pr_number: Pull request number
            analysis_results: Analysis results from QA AI
        """
        # Implementation will be moved here from app.py
        pass
    
    async def trigger_test_workflows(
        self,
        repo_name: str, 
        branch: str, 
        frameworks: list,
        commit_sha: str,
        installation_id: int
    ) -> bool:
        """
        Trigger the generated test workflows immediately using repository dispatch.
        
        Args:
            repo_name: Repository name (owner/repo)
            branch: Branch to run tests on
            frameworks: List of frameworks to test
            commit_sha: The commit SHA to test against
            installation_id: GitHub App installation ID
            
        Returns:
            True if workflows were triggered successfully
        """
        try:
            g, _ = self.get_client(installation_id)
            repo = g.get_repo(repo_name)
            
            # Trigger each framework workflow
            for framework in frameworks:
                try:
                    # Use repository dispatch to trigger workflow
                    repo.create_repository_dispatch(
                        event_type=f"qalia-test-{framework}",
                        client_payload={
                            "framework": framework,
                            "commit_sha": commit_sha,
                            "branch": branch,
                            "triggered_by": "qalia_analysis"
                        }
                    )
                    logger.info(f"✅ Triggered {framework} test workflow")
                    
                except Exception as e:
                    logger.error(f"Failed to trigger {framework} workflow: {e}")
            
            # Also trigger the matrix workflow
            try:
                repo.create_repository_dispatch(
                    event_type="qalia-test-matrix",
                    client_payload={
                        "frameworks": frameworks,
                        "commit_sha": commit_sha,
                        "branch": branch,
                        "triggered_by": "qalia_analysis"
                    }
                )
                logger.info("✅ Triggered matrix test workflow")
                
            except Exception as e:
                logger.error(f"Failed to trigger matrix workflow: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger test workflows: {e}")
            return False
    
    def is_qalia_commit(self, payload: Dict[str, Any]) -> bool:
        """
        Check if a commit was made by Qalia to prevent infinite loops.
        
        Args:
            payload: GitHub webhook payload
            
        Returns:
            True if this is a Qalia-generated commit that should be skipped
        """
        try:
            # Check different payload structures for commit information
            commit_info = None
            
            # For pull request events
            if "pull_request" in payload:
                head_commit = payload.get("pull_request", {}).get("head", {}).get("commit", {})
                if head_commit:
                    commit_info = head_commit
                else:
                    # Alternative structure
                    commits = payload.get("pull_request", {}).get("commits", [])
                    if commits:
                        commit_info = commits[-1]  # Get the latest commit
            
            # For push events
            elif "head_commit" in payload:
                commit_info = payload["head_commit"]
            
            # For commits array in push events
            elif "commits" in payload and payload["commits"]:
                commit_info = payload["commits"][-1]  # Get the latest commit
            
            if not commit_info:
                logger.warning("Could not extract commit info for loop detection")
                return False
            
            # Check commit message for Qalia signatures
            commit_message = commit_info.get("message", "")
            qalia_signatures = [
                "🤖 Add Qalia generated tests and workflows",
                "Generated by Qalia.ai",
                "🤖 Qalia:",
                "[qalia-bot]",
                "qalia-ai[bot]"
            ]
            
            for signature in qalia_signatures:
                if signature in commit_message:
                    logger.info(f"Detected Qalia commit signature: {signature}")
                    return True
            
            # Check commit author
            author_name = commit_info.get("author", {}).get("name", "")
            author_email = commit_info.get("author", {}).get("email", "")
            
            qalia_authors = [
                "Qalia AI",
                "qalia@ai-generated.com",
                "qalia-ai[bot]"
            ]
            
            if author_name in qalia_authors or author_email in qalia_authors:
                logger.info(f"Detected Qalia commit author: {author_name} <{author_email}>")
                return True
            
            # Check committer as well
            committer_name = commit_info.get("committer", {}).get("name", "")
            committer_email = commit_info.get("committer", {}).get("email", "")
            
            if committer_name in qalia_authors or committer_email in qalia_authors:
                logger.info(f"Detected Qalia committer: {committer_name} <{committer_email}>")
                return True
            
            # Check if commit only modifies Qalia-related files
            added_files = commit_info.get("added", [])
            modified_files = commit_info.get("modified", [])
            removed_files = commit_info.get("removed", [])
            
            all_changed_files = added_files + modified_files + removed_files
            
            if all_changed_files:
                qalia_file_patterns = [
                    "qalia-tests/",
                    ".github/workflows/qalia-",
                    "qalia.yml"
                ]
                
                # Check if ALL changed files are Qalia-related
                qalia_only = True
                for file_path in all_changed_files:
                    is_qalia_file = any(pattern in file_path for pattern in qalia_file_patterns)
                    if not is_qalia_file:
                        qalia_only = False
                        break
                
                if qalia_only and len(all_changed_files) > 0:
                    logger.info(f"Detected commit with only Qalia-related files: {all_changed_files}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in infinite loop detection: {e}")
            # If we can't determine, err on the side of caution and allow the commit
            return False


def get_private_key() -> str:
    """Read the private key from the PEM file or environment variable."""
    # Try environment variable first
    env_key = os.getenv("GITHUB_PRIVATE_KEY")
    if env_key:
        return env_key
    
    # Fall back to file
    try:
        with open("private-key.pem", "r") as key_file:
            return key_file.read()
    except FileNotFoundError:
        # Try alternative locations
        try:
            with open("app/private-key.pem", "r") as key_file:
                return key_file.read()
        except FileNotFoundError:
            raise RuntimeError(
                "Private key not found. Please ensure private-key.pem exists or set GITHUB_PRIVATE_KEY environment variable."
            ) 