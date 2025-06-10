import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages exploration sessions including directory creation and file organization.
    """
    
    def __init__(self, base_url: str):
        """
        Initialize session manager.
        
        Args:
            base_url: The starting URL being explored
        """
        self.base_url = base_url
        self.domain = self._extract_domain(base_url)
        self.session_id = self._generate_session_id()
        self.session_dir = self._create_session_directory()
        
        # Track screenshots taken
        self.screenshots_taken = []
        
        logger.info(f"📁 Session directory created: {self.session_dir}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for directory naming."""
        if '//' in url:
            domain = url.split('//')[1].split('/')[0]
        else:
            domain = url.split('/')[0]
        
        # Clean domain for filename safety
        return domain.replace(':', '_').replace('.', '_')
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.domain}_{timestamp}"
    
    def _create_session_directory(self) -> Path:
        """Create session directory structure."""
        base_dir = Path("exploration_sessions")
        session_dir = base_dir / self.session_id
        
        # Create directories
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "screenshots").mkdir(exist_ok=True)
        (session_dir / "reports").mkdir(exist_ok=True)
        
        return session_dir
    
    async def capture_error_screenshot(self, page, error_type: str, error_details: str = "", 
                                     url: str = "") -> Optional[str]:
        """
        Capture screenshot when an error occurs.
        
        Args:
            page: Playwright page object
            error_type: Type of error (e.g., "500_error", "console_error", "timeout")
            error_details: Additional error details for filename
            url: Current URL where error occurred
            
        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            # Generate descriptive filename
            timestamp = datetime.now().strftime("%H%M%S")
            safe_details = self._sanitize_filename(error_details)
            url_part = self._sanitize_filename(url.split('/')[-1]) if url else "unknown"
            
            filename = f"{timestamp}_{error_type}_{url_part}"
            if safe_details:
                filename += f"_{safe_details}"
            filename += ".png"
            
            screenshot_path = self.session_dir / "screenshots" / filename
            
            # Take full page screenshot
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Track screenshot
            screenshot_info = {
                'filename': filename,
                'path': str(screenshot_path),
                'error_type': error_type,
                'error_details': error_details,
                'url': url,
                'timestamp': datetime.now().isoformat()
            }
            self.screenshots_taken.append(screenshot_info)
            
            logger.info(f"📸 Error screenshot captured: {filename}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to capture error screenshot: {e}")
            return None
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for safe filename usage."""
        if not text:
            return ""
        
        # Remove/replace unsafe characters
        safe_chars = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_'))
        return safe_chars.replace(' ', '_')[:50]  # Limit length
    
    def save_sitemap(self, xml_content: str, domain: str) -> str:
        """
        Save the state fingerprint XML to the session directory.
        
        Args:
            xml_content: XML content to save
            domain: Domain name for filename
            
        Returns:
            Path to saved file
        """
        filename = f"state_fingerprint_{domain}.xml"
        filepath = self.session_dir / "reports" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logger.info(f"🗺️ Sitemap saved: {filename}")
        return str(filepath)
    
    def save_session_report(self, exploration_results: Dict[str, Any]) -> str:
        """
        Save comprehensive session report.
        
        Args:
            exploration_results: Results from exploration
            
        Returns:
            Path to saved report
        """
        import json
        
        # Enhanced report with screenshot information
        report = {
            'session_info': {
                'session_id': self.session_id,
                'domain': self.domain,
                'base_url': self.base_url,
                'start_time': exploration_results.get('start_time'),
                'end_time': exploration_results.get('end_time', time.time()),
                'duration': exploration_results.get('duration', 0)
            },
            'exploration_results': exploration_results,
            'screenshots': {
                'total_screenshots': len(self.screenshots_taken),
                'error_screenshots': self.screenshots_taken,
                'screenshot_summary': self._generate_screenshot_summary()
            },
            'files_generated': {
                'session_directory': str(self.session_dir),
                'screenshots_dir': str(self.session_dir / "screenshots"),
                'reports_dir': str(self.session_dir / "reports")
            }
        }
        
        # Save JSON report
        report_path = self.session_dir / "reports" / "session_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save human-readable summary
        summary_path = self.session_dir / "reports" / "session_summary.txt"
        self._save_human_readable_summary(report, summary_path)
        
        logger.info(f"📋 Session report saved: {report_path}")
        return str(report_path)
    
    def _generate_screenshot_summary(self) -> Dict[str, Any]:
        """Generate summary of screenshots taken."""
        if not self.screenshots_taken:
            return {'message': 'No error screenshots taken - clean session!'}
        
        error_types = {}
        for screenshot in self.screenshots_taken:
            error_type = screenshot['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total': len(self.screenshots_taken),
            'by_error_type': error_types,
            'first_error': self.screenshots_taken[0]['timestamp'],
            'last_error': self.screenshots_taken[-1]['timestamp']
        }
    
    def _save_human_readable_summary(self, report: Dict[str, Any], filepath: Path) -> None:
        """Save human-readable session summary."""
        session_info = report['session_info']
        exploration = report['exploration_results']
        screenshots = report['screenshots']
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"🔍 QA AI Exploration Session Report\n")
            f.write(f"=" * 50 + "\n\n")
            
            f.write(f"📋 Session Information:\n")
            f.write(f"  Session ID: {session_info['session_id']}\n")
            f.write(f"  Domain: {session_info['domain']}\n")
            f.write(f"  Base URL: {session_info['base_url']}\n")
            f.write(f"  Duration: {session_info.get('duration', 0):.1f} seconds\n\n")
            
            # Exploration summary
            summary = exploration.get('exploration_summary', {})
            f.write(f"🎯 Exploration Results:\n")
            f.write(f"  Pages visited: {summary.get('total_pages_visited', 0)}\n")
            f.write(f"  Actions performed: {summary.get('total_actions_performed', 0)}\n")
            f.write(f"  Bugs found: {summary.get('bugs_found', 0)}\n")
            f.write(f"  Warnings: {summary.get('warnings', 0)}\n\n")
            
            # State statistics
            state_stats = summary.get('state_statistics', {})
            if state_stats:
                f.write(f"🔄 State Mapping:\n")
                f.write(f"  States discovered: {state_stats.get('total_states_discovered', 0)}\n")
                f.write(f"  State transitions: {state_stats.get('total_state_transitions', 0)}\n")
                f.write(f"  Unique fingerprints: {state_stats.get('unique_state_fingerprints', 0)}\n\n")
            
            # Screenshot summary
            f.write(f"📸 Error Screenshots:\n")
            if screenshots['total_screenshots'] == 0:
                f.write(f"  ✅ No error screenshots - clean session!\n\n")
            else:
                f.write(f"  Total screenshots: {screenshots['total_screenshots']}\n")
                error_summary = screenshots['screenshot_summary']
                for error_type, count in error_summary.get('by_error_type', {}).items():
                    f.write(f"    {error_type}: {count} screenshot(s)\n")
                f.write(f"\n  📁 Screenshots saved in: screenshots/\n\n")
            
            # Files generated
            f.write(f"📁 Files Generated:\n")
            f.write(f"  Session directory: {report['files_generated']['session_directory']}\n")
            f.write(f"  Screenshots: {report['files_generated']['screenshots_dir']}\n")
            f.write(f"  Reports: {report['files_generated']['reports_dir']}\n")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information."""
        return {
            'session_id': self.session_id,
            'session_dir': str(self.session_dir),
            'domain': self.domain,
            'screenshots_taken': len(self.screenshots_taken)
        } 