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
import socket

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
                "startup": "python -m http.server {port}",
                "port": 8080
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
        
        # Check if startup command is provided - prefer local deployment
        startup_command = self.deployment_config.get("startup")
        if startup_command:
            # Local deployment using startup command
            logger.info("Found startup command - deploying locally")
        elif "url" in self.deployment_config:
            # Fallback to existing deployment URL
            url = self.deployment_config["url"]
            logger.info(f"Using existing deployment at {url}")
            return url
        else:
            raise ValueError("No startup command or URL specified. Please add 'startup' field to deployment configuration.")
        
        # Get port (default to 8080)
        port = self.deployment_config.get("port", 8080)
        
        # Try to find an available port if the default is taken
        port = self._find_available_port(port)
        
        # Run build commands if specified
        await self._run_build_commands()
        
        # Replace {port} placeholder in startup command if present
        startup_command = startup_command.replace("{port}", str(port))
        
        logger.info(f"Starting application with command: {startup_command}")
        
        # Start the application
        self.process = subprocess.Popen(startup_command, shell=True, cwd=self.repo_path)
        
        # Wait for server to be ready
        url = f"http://localhost:{port}"
        await self._wait_for_ready(url)
        return url
    
    def _find_available_port(self, preferred_port: int) -> int:
        """Find an available port starting from preferred_port."""
        for port in range(preferred_port, preferred_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    logger.info(f"Found available port: {port}")
                    return port
            except OSError:
                continue
        
        # If no port found in range, raise error
        raise RuntimeError(f"No available ports found in range {preferred_port}-{preferred_port + 100}")
    
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