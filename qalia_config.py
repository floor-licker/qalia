"""
Qalia Configuration Parser and Deployment Manager

This module handles parsing qalia.yml configuration files and managing
application deployment for testing.
"""

import yaml
import os
import subprocess
import time
import requests
import tempfile
import shutil
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class QaliaConfig:
    """Handles qalia.yml configuration parsing and validation."""
    
    def __init__(self, config_path: str = "qalia.yml"):
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load and parse the qalia.yml configuration file."""
        try:
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            logger.info(f"Loaded configuration from {self.config_path}")
        except FileNotFoundError:
            logger.warning(f"No {self.config_path} found, using defaults")
            self.config = self.get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {self.config_path}: {e}")
            raise
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration when no qalia.yml is found."""
        return {
            "deployment": {
                "type": "static",
                "url": None
            },
            "testing": {
                "entry_points": [{"url": "/", "name": "Homepage"}],
                "exploration": {
                    "max_depth": 3,
                    "timeout": 300,
                    "headless": True,
                    "viewport": {"width": 1920, "height": 1080}
                },
                "generation": {
                    "frameworks": ["playwright", "cypress", "jest"],
                    "output_dir": "qalia-tests"
                }
            },
            "authentication": {"enabled": False},
            "notifications": {
                "github": {"enabled": True, "create_check_run": True, "comment_on_pr": True}
            }
        }
    
    def get_deployment_config(self) -> Dict[str, Any]:
        """Get deployment configuration."""
        return self.config.get("deployment", {})
    
    def get_testing_config(self) -> Dict[str, Any]:
        """Get testing configuration."""
        return self.config.get("testing", {})
    
    def get_authentication_config(self) -> Dict[str, Any]:
        """Get authentication configuration."""
        return self.config.get("authentication", {"enabled": False})
    
    def get_scenarios(self) -> List[Dict[str, Any]]:
        """Get custom test scenarios."""
        return self.config.get("scenarios", [])
    
    def get_exclusions(self) -> Dict[str, List[str]]:
        """Get URLs and selectors to exclude from testing."""
        return self.config.get("exclusions", {"urls": [], "selectors": []})

class DeploymentManager:
    """Manages application deployment for testing."""
    
    def __init__(self, config: QaliaConfig, repo_path: str):
        self.config = config
        self.repo_path = repo_path
        self.deployment_config = config.get_deployment_config()
        self.process = None
        self.temp_dir = None
    
    async def deploy_application(self) -> str:
        """Deploy the application and return the URL where it's accessible."""
        deployment_type = self.deployment_config.get("type", "static")
        
        # If URL is provided, use it directly (existing deployment)
        if "url" in self.deployment_config:
            url = self.deployment_config["url"]
            logger.info(f"Using existing deployment at {url}")
            return url
        
        # Otherwise, deploy locally based on type
        if deployment_type == "static":
            return await self._deploy_static()
        elif deployment_type == "npm":
            return await self._deploy_npm()
        elif deployment_type == "python":
            return await self._deploy_python()
        elif deployment_type == "docker":
            return await self._deploy_docker()
        elif deployment_type == "custom":
            return await self._deploy_custom()
        else:
            raise ValueError(f"Unsupported deployment type: {deployment_type}")
    
    async def _deploy_static(self) -> str:
        """Deploy a static website."""
        # For static sites, we can serve them directly
        port = self.deployment_config.get("port", 8080)
        
        # Run build commands if specified
        await self._run_build_commands()
        
        # Start a simple HTTP server
        build_dir = self.deployment_config.get("build_dir", "dist")
        if not os.path.exists(build_dir):
            build_dir = "."
        
        cmd = f"python -m http.server {port} --directory {build_dir}"
        self.process = subprocess.Popen(cmd, shell=True, cwd=self.repo_path)
        
        # Wait for server to be ready
        url = f"http://localhost:{port}"
        await self._wait_for_ready(url)
        return url
    
    async def _deploy_npm(self) -> str:
        """Deploy a Node.js application."""
        # Run build commands
        await self._run_build_commands()
        
        # Start the application
        start_config = self.deployment_config.get("start", {})
        command = start_config.get("command", "npm start")
        port = start_config.get("port", 3000)
        
        # Set environment variables
        env = os.environ.copy()
        env_vars = self.config.config.get("environment", {}).get("variables", {})
        env.update(env_vars)
        
        self.process = subprocess.Popen(
            command, 
            shell=True, 
            cwd=self.repo_path,
            env=env
        )
        
        # Wait for application to be ready
        url = f"http://localhost:{port}"
        await self._wait_for_ready(url, start_config.get("wait_for_ready", 30))
        return url
    
    async def _deploy_python(self) -> str:
        """Deploy a Python application."""
        # Install dependencies
        if os.path.exists(os.path.join(self.repo_path, "requirements.txt")):
            subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=self.repo_path)
        
        # Run build commands
        await self._run_build_commands()
        
        # Start the application
        start_config = self.deployment_config.get("start", {})
        command = start_config.get("command", "python app.py")
        port = start_config.get("port", 5000)
        
        self.process = subprocess.Popen(command, shell=True, cwd=self.repo_path)
        
        url = f"http://localhost:{port}"
        await self._wait_for_ready(url, start_config.get("wait_for_ready", 30))
        return url
    
    async def _deploy_docker(self) -> str:
        """Deploy using Docker."""
        docker_config = self.deployment_config.get("docker", {})
        image_name = docker_config.get("image", "qalia-test-app")
        port = docker_config.get("port", 3000)
        
        # Build Docker image
        build_cmd = f"docker build -t {image_name} ."
        subprocess.run(build_cmd, shell=True, cwd=self.repo_path, check=True)
        
        # Run container
        run_cmd = f"docker run -d -p {port}:{port} {image_name}"
        result = subprocess.run(run_cmd, shell=True, capture_output=True, text=True)
        container_id = result.stdout.strip()
        
        # Store container ID for cleanup
        self.container_id = container_id
        
        url = f"http://localhost:{port}"
        await self._wait_for_ready(url)
        return url
    
    async def _deploy_custom(self) -> str:
        """Deploy using custom commands."""
        custom_config = self.deployment_config.get("custom", {})
        
        # Run setup commands
        setup_commands = custom_config.get("setup", [])
        for cmd in setup_commands:
            subprocess.run(cmd, shell=True, cwd=self.repo_path, check=True)
        
        # Start the application
        start_command = custom_config.get("start_command")
        if start_command:
            self.process = subprocess.Popen(start_command, shell=True, cwd=self.repo_path)
        
        # Return the URL
        url = custom_config.get("url", "http://localhost:3000")
        await self._wait_for_ready(url)
        return url
    
    async def _run_build_commands(self):
        """Run build commands specified in configuration."""
        build_commands = self.deployment_config.get("build", [])
        for cmd in build_commands:
            logger.info(f"Running build command: {cmd}")
            result = subprocess.run(cmd, shell=True, cwd=self.repo_path)
            if result.returncode != 0:
                raise RuntimeError(f"Build command failed: {cmd}")
    
    async def _wait_for_ready(self, url: str, timeout: int = 30):
        """Wait for the application to be ready."""
        health_check_url = self.deployment_config.get("start", {}).get("health_check", url)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(health_check_url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Application ready at {url}")
                    return
            except requests.RequestException:
                pass
            
            time.sleep(2)
        
        raise TimeoutError(f"Application not ready after {timeout} seconds")
    
    def cleanup(self):
        """Clean up deployed resources."""
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        if hasattr(self, 'container_id'):
            subprocess.run(f"docker stop {self.container_id}", shell=True)
            subprocess.run(f"docker rm {self.container_id}", shell=True)
        
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

async def get_application_url(repo_path: str, config_file: str = "qalia.yml") -> str:
    """
    Main function to get the application URL for testing.
    
    This function:
    1. Loads the qalia.yml configuration
    2. Deploys the application if needed
    3. Returns the URL where the app is accessible
    """
    config_path = os.path.join(repo_path, config_file)
    config = QaliaConfig(config_path)
    
    deployment_manager = DeploymentManager(config, repo_path)
    
    try:
        url = await deployment_manager.deploy_application()
        logger.info(f"Application deployed and accessible at: {url}")
        return url
    except Exception as e:
        deployment_manager.cleanup()
        raise e 