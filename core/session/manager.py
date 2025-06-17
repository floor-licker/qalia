import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    
    async def save_session_report(self, exploration_results: Dict[str, Any]) -> str:
        """
        Save comprehensive session report.
        
        Args:
            exploration_results: Results from exploration
            
        Returns:
            Path to saved report
        """
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
        
        # Generate and save detailed action analysis XML for ChatGPT
        analysis_xml = self.generate_detailed_action_analysis_xml(exploration_results)
        analysis_xml_path = self.session_dir / "reports" / "action_analysis_for_chatgpt.xml"
        with open(analysis_xml_path, 'w', encoding='utf-8') as f:
            f.write(analysis_xml)
        logger.info(f"🤖 ChatGPT analysis XML saved: {analysis_xml_path}")
        
        # Automatically send to ChatGPT for analysis (if API key available)
        chatgpt_analysis_file = await self.analyze_with_chatgpt(analysis_xml, exploration_results)
        
        # Include ChatGPT analysis information in the report
        if chatgpt_analysis_file:
            report['chatgpt_analysis'] = {
                'status': 'completed',
                'analysis_file': str(chatgpt_analysis_file)
            }
        else:
            report['chatgpt_analysis'] = {
                'status': 'failed',
                'error': 'ChatGPT analysis failed or API key not available'
            }
        
        # Re-save the report with ChatGPT analysis info
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
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
    
    def generate_detailed_action_analysis_xml(self, exploration_results: Dict[str, Any]) -> str:
        """
        Generate enhanced XML report optimized for ChatGPT integration test generation.
        Includes user journey mapping, modal interactions, and test-ready data structure.
        """
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Extract action history from exploration results
        action_history = exploration_results.get('detailed_results', {}).get('executed_actions', [])
        
        # If no action history found, try alternative keys
        if not action_history:
            action_history = exploration_results.get('action_history', [])
            if not action_history:
                action_history = exploration_results.get('actions_performed', [])
        
        root = Element("IntegrationTestAnalysis")
        root.set("domain", self.base_url)
        root.set("session_id", self.session_id)
        root.set("timestamp", str(time.time()))
        root.set("total_actions", str(len(action_history)))
        root.set("application_type", "SPA_DeFi")  # Help ChatGPT understand context
        
        # Enhanced Session Summary with test context
        summary = SubElement(root, "SessionSummary")
        SubElement(summary, "ApplicationType").text = "Single Page Application (DeFi)"
        SubElement(summary, "TotalActions").text = str(len(action_history))
        SubElement(summary, "SuccessfulActions").text = str(sum(1 for action in action_history if action.get('success', False)))
        SubElement(summary, "FailedActions").text = str(sum(1 for action in action_history if not action.get('success', True)))
        SubElement(summary, "OverallSuccessRate").text = f"{(sum(1 for action in action_history if action.get('success', False)) / max(len(action_history), 1)):.2%}"
        SubElement(summary, "TotalDuration").text = f"{sum(action.get('duration', 0) for action in action_history):.2f}s"
        SubElement(summary, "AverageDuration").text = f"{sum(action.get('duration', 0) for action in action_history) / max(len(action_history), 1):.2f}s"
        
        # User Journey Mapping - Group actions into logical workflows
        journeys = self._extract_user_journeys(action_history)
        if journeys:
            journeys_section = SubElement(root, "UserJourneys")
            for journey_name, journey_actions in journeys.items():
                journey_elem = SubElement(journeys_section, "Journey")
                journey_elem.set("name", journey_name)
                journey_elem.set("action_count", str(len(journey_actions)))
                
                SubElement(journey_elem, "Description").text = self._get_journey_description(journey_name)
                SubElement(journey_elem, "TestPriority").text = self._get_journey_priority(journey_name)
                
                for action in journey_actions:
                    action_ref = SubElement(journey_elem, "ActionReference")
                    action_ref.set("sequence", str(action.get('sequence', 0)))
                    action_ref.text = f"{action.get('action', {}).get('action', '')} on {action.get('action', {}).get('text', '')}"
        
        # Modal Interactions - Highlight these for DeFi test generation
        modal_actions = [action for action in action_history if self._is_modal_action(action)]
        if modal_actions:
            modal_section = SubElement(root, "ModalInteractions")
            modal_section.set("count", str(len(modal_actions)))
            
            for action in modal_actions:
                modal_elem = SubElement(modal_section, "ModalWorkflow")
                modal_elem.set("trigger_action", action.get('action', {}).get('text', ''))
                modal_elem.set("sequence", str(action.get('sequence', 0)))
                
                # Modal trigger details
                trigger = SubElement(modal_elem, "ModalTrigger")
                SubElement(trigger, "ElementType").text = action.get('action', {}).get('element_type', '')
                SubElement(trigger, "ElementText").text = action.get('action', {}).get('text', '')
                SubElement(trigger, "ExpectedBehavior").text = "Modal should appear with interactive options"
                
                # Modal content analysis
                if 'modal_results' in action:
                    content = SubElement(modal_elem, "ModalContent")
                    modal_results = action.get('modal_results', [])
                    SubElement(content, "InteractiveElements").text = str(len(modal_results))
                    
                    for modal_action in modal_results:
                        element = SubElement(content, "ModalElement")
                        element.set("text", modal_action.get('action', {}).get('text', ''))
                        element.set("clickable", "true")
                        SubElement(element, "TestScenario").text = f"User should be able to click '{modal_action.get('action', {}).get('text', '')}' option"
        
        # Enhanced Actions Section with test context
        actions_section = SubElement(root, "DetailedActions")
        
        for i, action_record in enumerate(action_history):
            action_elem = SubElement(actions_section, "ActionResultPair")
            action_elem.set("sequence", str(i + 1))
            action_elem.set("success", str(action_record.get('success', False)))
            action_elem.set("test_category", self._categorize_action_for_testing(action_record))
            
            # Action Details with test context
            action_details = SubElement(action_elem, "ActionDetails")
            action_data = action_record.get('action', {})
            SubElement(action_details, "ActionType").text = action_data.get('action', 'unknown')
            SubElement(action_details, "ElementType").text = action_data.get('element_type', 'unknown')
            SubElement(action_details, "ElementSelector").text = action_data.get('target', 'unknown')
            SubElement(action_details, "ElementText").text = action_data.get('text', '')
            SubElement(action_details, "InputValue").text = action_data.get('value', '')
            SubElement(action_details, "TestSelector").text = self._generate_test_selector(action_data)
            
            # Context Information
            context = SubElement(action_elem, "Context")
            SubElement(context, "CurrentURL").text = action_record.get('url', 'unknown')
            SubElement(context, "StateBeforeAction").text = action_record.get('state_before', 'unknown')
            SubElement(context, "StateAfterAction").text = action_record.get('state_after', 'unknown')
            SubElement(context, "PageTitle").text = action_record.get('page_title', '')
            SubElement(context, "ApplicationState").text = self._determine_app_state(action_record)
            
            # Expected Behavior for test generation
            expected = SubElement(action_elem, "ExpectedBehavior")
            element_type = action_data.get('element_type', '')
            action_type = action_data.get('action', '')
            
            if action_type == 'click':
                if element_type == 'link':
                    expected_text = "SPA navigation or state change (no full page reload expected)"
                elif element_type == 'button':
                    if 'CONNECT' in action_data.get('text', '').upper():
                        expected_text = "Wallet connection modal should appear with wallet options"
                    else:
                        expected_text = "Button action should trigger state change or modal"
                else:
                    expected_text = "Interactive response or state change"
            elif action_type == 'input':
                expected_text = "Text input accepted and element value updated"
            else:
                expected_text = "Element interaction completed successfully"
                
            SubElement(expected, "Description").text = expected_text
            SubElement(expected, "ExpectedDuration").text = "< 3 seconds for normal interactions"
            SubElement(expected, "TestAssertion").text = self._generate_test_assertion(action_record)
            
            # Actual Results with test validation context
            results = SubElement(action_elem, "ActualResults")
            SubElement(results, "Success").text = str(action_record.get('success', False))
            SubElement(results, "Duration").text = f"{action_record.get('duration', 0):.2f}s"
            SubElement(results, "URLChanged").text = str(action_record.get('url_changed', False))
            SubElement(results, "StateChanged").text = str(action_record.get('state_changed', False))
            SubElement(results, "NavigationOccurred").text = str(action_record.get('navigation_occurred', False))
            SubElement(results, "ModalAppeared").text = str(self._check_modal_appeared(action_record))
            SubElement(results, "TestValidation").text = self._validate_test_expectation(action_record)
            
            # Performance Analysis for test timing
            performance = SubElement(action_elem, "Performance")
            duration = action_record.get('duration', 0)
            if duration > 5.0:
                SubElement(performance, "PerformanceFlag").text = "SLOW_RESPONSE"
                SubElement(performance, "TestTiming").text = f"Test should allow {duration + 2:.0f}s timeout"
                SubElement(performance, "Analysis").text = f"Action took {duration:.2f}s - consider performance test"
            elif duration > 10.0:
                SubElement(performance, "PerformanceFlag").text = "VERY_SLOW_RESPONSE"
                SubElement(performance, "TestTiming").text = f"Test should allow {duration + 5:.0f}s timeout"
                SubElement(performance, "Analysis").text = f"Action took {duration:.2f}s - requires performance optimization test"
            else:
                SubElement(performance, "PerformanceFlag").text = "NORMAL"
                SubElement(performance, "TestTiming").text = "Standard 3s timeout sufficient"
                SubElement(performance, "Analysis").text = "Normal performance - standard test timing"
            
            # Test Automation Recommendations
            automation = SubElement(action_elem, "TestAutomation")
            automation_data = self._generate_automation_recommendations(action_record)
            for key, value in automation_data.items():
                SubElement(automation, key).text = str(value)
        
        # Console Errors Section with test context
        console_errors = exploration_results.get('detailed_results', {}).get('error_analysis', {}).get('recent_errors', [])
        if console_errors:
            console_section = SubElement(root, "ConsoleErrors")
            console_section.set("total_errors", str(len(console_errors)))
            console_section.set("test_impact", "Monitor for error handling tests")
            
            for i, error in enumerate(console_errors[-10:]):  # Last 10 errors
                error_elem = SubElement(console_section, "ConsoleError")
                error_elem.set("sequence", str(i + 1))
                SubElement(error_elem, "Message").text = error.get('message', '')
                SubElement(error_elem, "Level").text = error.get('level', 'unknown')
                SubElement(error_elem, "Timestamp").text = str(error.get('timestamp', ''))
                SubElement(error_elem, "TestImplication").text = self._analyze_error_for_testing(error)
        
        # Typo Analysis Section
        typo_analysis = exploration_results.get('detailed_results', {}).get('typo_analysis', {})
        if typo_analysis and typo_analysis.get('total_typos_found', 0) > 0:
            typos_section = SubElement(root, "TypoAnalysis")
            typos_section.set("total_typos", str(typo_analysis.get('total_typos_found', 0)))
            typos_section.set("high_confidence_typos", str(typo_analysis.get('high_confidence_typos', 0)))
            typos_section.set("test_priority", "Medium")
            
            SubElement(typos_section, "Summary").text = f"Found {typo_analysis.get('total_typos_found', 0)} potential typos across {typo_analysis.get('pages_with_typos', 0)} pages. High confidence typos: {typo_analysis.get('high_confidence_typos', 0)}"
            SubElement(typos_section, "TestRecommendation").text = "Include typo detection tests in content validation suite. Monitor for UI text quality and proofreading processes."
            
            # Most common typos for testing focus
            if typo_analysis.get('most_common_typos'):
                common_typos = SubElement(typos_section, "MostCommonTypos")
                for typo_word, count in typo_analysis.get('most_common_typos', [])[:5]:
                    typo_elem = SubElement(common_typos, "Typo")
                    typo_elem.set("word", typo_word)
                    typo_elem.set("frequency", str(count))
                    typo_elem.text = f"'{typo_word}' appears {count} times - priority for content review"
            
            # Typo distribution by element type
            if typo_analysis.get('typo_by_element_type'):
                distribution = SubElement(typos_section, "TypoDistribution")
                for element_type, count in typo_analysis.get('typo_by_element_type', {}).items():
                    elem = SubElement(distribution, "ElementType")
                    elem.set("type", element_type)
                    elem.set("typo_count", str(count))
                    elem.text = f"{element_type} elements contain {count} typos"
        
        # Test Suite Recommendations
        test_suites = SubElement(root, "RecommendedTestSuites")
        
        # Wallet Connection Test Suite
        wallet_suite = SubElement(test_suites, "TestSuite")
        wallet_suite.set("name", "WalletConnectionTests")
        wallet_suite.set("priority", "High")
        SubElement(wallet_suite, "Description").text = "Tests for DeFi wallet connection workflows"
        SubElement(wallet_suite, "TestCount").text = str(len(modal_actions))
        
        # Navigation Test Suite  
        nav_suite = SubElement(test_suites, "TestSuite")
        nav_suite.set("name", "NavigationTests")
        nav_suite.set("priority", "Medium")
        SubElement(nav_suite, "Description").text = "Tests for SPA navigation and state management"
        nav_actions = [a for a in action_history if a.get('action', {}).get('element_type') == 'link']
        SubElement(nav_suite, "TestCount").text = str(len(nav_actions))
        
        # Performance Test Suite
        perf_suite = SubElement(test_suites, "TestSuite")
        perf_suite.set("name", "PerformanceTests")
        perf_suite.set("priority", "Low")
        SubElement(perf_suite, "Description").text = "Tests for interaction timing and performance"
        slow_actions = [a for a in action_history if a.get('duration', 0) > 3.0]
        SubElement(perf_suite, "TestCount").text = str(len(slow_actions))
        
        # Content Quality Test Suite (if typos were found)
        if typo_analysis and typo_analysis.get('total_typos_found', 0) > 0:
            content_suite = SubElement(test_suites, "TestSuite")
            content_suite.set("name", "ContentQualityTests")
            content_suite.set("priority", "Medium")
            SubElement(content_suite, "Description").text = "Tests for text content quality, typos, and proofreading"
            SubElement(content_suite, "TestCount").text = str(typo_analysis.get('total_typos_found', 0))
            SubElement(content_suite, "Focus").text = "Automated spell-checking, content validation, and UI text review"
        
        # Convert to pretty XML string
        rough_string = tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _extract_user_journeys(self, action_history: list) -> dict:
        """Extract logical user journeys from action sequence."""
        journeys = {}
        current_journey = []
        journey_name = "Initial_Exploration"
        
        for action in action_history:
            action_text = action.get('action', {}).get('text', '').upper()
            
            # Start new journey on significant navigation
            if any(keyword in action_text for keyword in ['CONNECT', 'HOME', 'PROFILE']):
                if current_journey:
                    journeys[journey_name] = current_journey
                
                if 'CONNECT' in action_text:
                    journey_name = "Wallet_Connection_Flow"
                elif 'HOME' in action_text:
                    journey_name = "Home_Navigation"
                elif 'PROFILE' in action_text:
                    journey_name = "Profile_Management"
                else:
                    journey_name = f"Journey_{len(journeys) + 1}"
                
                current_journey = []
            
            current_journey.append(action)
        
        # Add final journey
        if current_journey:
            journeys[journey_name] = current_journey
        
        return journeys
    
    def _get_journey_description(self, journey_name: str) -> str:
        """Get description for journey type."""
        descriptions = {
            "Wallet_Connection_Flow": "User attempts to connect a DeFi wallet through modal interface",
            "Home_Navigation": "User navigates through main application pages",
            "Profile_Management": "User accesses and manages profile settings",
            "Initial_Exploration": "Initial application exploration and element discovery"
        }
        return descriptions.get(journey_name, "User interaction sequence")
    
    def _get_journey_priority(self, journey_name: str) -> str:
        """Get test priority for journey type."""
        priorities = {
            "Wallet_Connection_Flow": "High",
            "Profile_Management": "Medium", 
            "Home_Navigation": "Medium",
            "Initial_Exploration": "Low"
        }
        return priorities.get(journey_name, "Medium")
    
    def _is_modal_action(self, action: dict) -> bool:
        """Check if action involves modal interaction."""
        action_data = action.get('action', {})
        element_text = action_data.get('text', '').upper()
        
        # Check for modal trigger buttons
        if 'CONNECT' in element_text and action_data.get('element_type') == 'button':
            return True
        
        # Check if action has modal results
        return 'modal_results' in action
    
    def _categorize_action_for_testing(self, action: dict) -> str:
        """Categorize action for test organization."""
        action_data = action.get('action', {})
        element_text = action_data.get('text', '').upper()
        element_type = action_data.get('element_type', '')
        
        if 'CONNECT' in element_text:
            return "WalletConnection"
        elif element_type == 'link':
            return "Navigation"
        elif element_type == 'button':
            return "ButtonAction"
        elif element_type == 'input':
            return "FormInput"
        else:
            return "General"
    
    def _generate_test_selector(self, action_data: dict) -> str:
        """Generate a test-friendly selector."""
        element_text = action_data.get('text', '')
        element_type = action_data.get('element_type', '')
        
        if element_text:
            return f"[data-testid='{element_text.lower().replace(' ', '-')}'], button:contains('{element_text}'), a:contains('{element_text}')"
        else:
            return f"{element_type}[data-testid], {element_type}[id], {element_type}[class]"
    
    def _determine_app_state(self, action: dict) -> str:
        """Determine application state based on action context."""
        url = action.get('url', '')
        if 'profile' in url:
            return "ProfilePage"
        elif url.endswith('/'):
            return "HomePage"
        else:
            return "UnknownState"
    
    def _generate_test_assertion(self, action: dict) -> str:
        """Generate appropriate test assertion for action."""
        action_data = action.get('action', {})
        element_text = action_data.get('text', '').upper()
        element_type = action_data.get('element_type', '')
        
        if 'CONNECT' in element_text:
            return "Verify modal appears with wallet options (Argent, Braavos)"
        elif element_type == 'link':
            return "Verify state change or navigation occurs"
        elif element_type == 'button':
            return "Verify button action completes successfully"
        else:
            return "Verify element interaction succeeds"
    
    def _check_modal_appeared(self, action: dict) -> bool:
        """Check if modal appeared after action."""
        return 'modal_results' in action or 'modal' in str(action.get('state_changes', [])).lower()
    
    def _validate_test_expectation(self, action: dict) -> str:
        """Validate if action met test expectations."""
        if action.get('success', False):
            if self._check_modal_appeared(action):
                return "PASSED - Modal interaction successful"
            elif action.get('state_changed', False):
                return "PASSED - State change as expected"
            else:
                return "PASSED - Action completed successfully"
        else:
            return "FAILED - Action did not complete as expected"
    
    def _generate_automation_recommendations(self, action: dict) -> dict:
        """Generate recommendations for test automation."""
        action_data = action.get('action', {})
        element_text = action_data.get('text', '')
        duration = action.get('duration', 0)
        
        return {
            "TestFramework": "Playwright or Selenium",
            "WaitStrategy": "Wait for element visible and clickable",
            "TimeoutRecommendation": f"{max(5, int(duration + 2))}s",
            "RetryStrategy": "Retry up to 3 times with 1s delay",
            "DataTestId": f"data-testid='{element_text.lower().replace(' ', '-')}'" if element_text else "Add data-testid attribute",
            "AssertionType": "Visual and functional validation"
        }
    
    def _analyze_error_for_testing(self, error: dict) -> str:
        """Analyze console error for test implications."""
        message = error.get('message', '').lower()
        
        if 'permissions' in message:
            return "Test error handling for permissions violations"
        elif 'network' in message or 'fetch' in message:
            return "Test network failure scenarios"
        elif 'timeout' in message:
            return "Test timeout handling and retry logic"
        else:
            return "Monitor error frequency and impact on user experience"
    
    async def analyze_with_chatgpt(self, xml_content: str, exploration_results: Dict[str, Any]) -> Optional[str]:
        """
        Automatically send XML analysis to ChatGPT and save the response.
        
        Args:
            xml_content: The XML content to analyze
            exploration_results: Original exploration results for context
            
        Returns:
            Path to saved analysis or None if failed
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY not found in .env - skipping automatic ChatGPT analysis")
            logger.info("💡 To enable automatic analysis, add OPENAI_API_KEY to your .env file")
            return None
        
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            
            # Prepare the analysis prompt
            prompt = self._create_analysis_prompt(exploration_results)
            
            logger.info("🤖 Sending XML to ChatGPT for automated bug analysis...")
            
            # Send to ChatGPT
            response = await client.chat.completions.create(
                model="gpt-4o",  # Use the latest model
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert QA automation engineer specializing in integration test generation for DeFi web applications. Your primary goal is to analyze automated testing sessions and generate comprehensive, automatable test scenarios. Focus on user journey mapping, modal interactions, wallet connection workflows, and creating structured test cases that can be easily converted into automated tests using frameworks like Playwright or Selenium. Provide actionable test scenarios with specific selectors, assertions, and timing requirements."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nXML Report:\n{xml_content}"
                    }
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=4000
            )
            
            chatgpt_response = response.choices[0].message.content
            
            # Save responses in multiple formats
            response_files = await self._save_chatgpt_analysis(chatgpt_response, exploration_results)
            
            logger.info(f"✅ ChatGPT analysis completed and saved:")
            for file_path in response_files:
                logger.info(f"   📄 {file_path}")
            
            return response_files[0]  # Return primary analysis file
            
        except ImportError:
            logger.error("❌ OpenAI library not installed. Run: pip install openai>=1.0.0")
            return None
        except Exception as e:
            logger.error(f"❌ ChatGPT analysis failed: {e}")
            logger.info("📄 XML analysis available for manual review")
            return None
    
    def _create_analysis_prompt(self, exploration_results: Dict[str, Any]) -> str:
        """Create a comprehensive prompt for ChatGPT analysis focused on integration test generation."""
        
        summary = exploration_results.get('exploration_summary', {})
        
        prompt = f"""You are an expert QA automation engineer analyzing a DeFi (Decentralized Finance) web application testing session to generate integration test scenarios.

IMPORTANT CONTEXT:


- Focus on user flow validation and functional correctness
- Consider whether a sequence of events ( a user flow, or use-case ) is intuitive and easy to understand

TESTING SESSION DATA:
- Website: {self.base_url} (DeFi Application)
- Application Type: Single Page Application (SPA)
- Total Actions: {summary.get('total_actions_performed', 0)}
- Success Rate: {summary.get('success_rate', 0):.1%}
- Duration: {summary.get('duration', 0):.1f} seconds
- Pages Visited: {summary.get('pages_visited', 0)}
- Errors Found: {summary.get('errors_found', 0)}
- Typos Found: {summary.get('typos_found', 0)} (High Confidence: {summary.get('confirmed_typos', 0)})

PRIMARY OBJECTIVE: Generate integration test scenarios that can be automated

ANALYSIS REQUIREMENTS:

1. **User Journey Analysis**: 
   - Identify complete user workflows (e.g., wallet connection, navigation patterns, checkout, login)
   - Map ALL critical paths through the application
   - Highlight modal-based interactions 

2. **Integration Test Scenarios**: For each identified workflow, provide:
   - Test name (clear, descriptive)
   - Preconditions (what state should app be in)
   - Test steps (sequence of actions to automate)
   - Expected outcomes (what should happen at each step)
   - Assertions to validate (what to check for success)

3. **Test Categories**:
   - **Navigation Tests**: Menu navigation, page transitions, URL changes
   - **State Management Tests**: Application state consistency across interactions
   - **Performance Tests**: Interaction timing, load performance
   - **Error Handling Tests**: How app handles failed actions, network issues
   - **Content Quality Tests**: UI text validation, typo detection, proofreading verification

4. **Critical Focus Areas**:
   - Modal workflows 
   - State transitions and data persistence
   - User authentication flows
   - Cross-page functionality
   - Application-specific critical use-cases where applicable (Add to cart, create session, login, etc)

5. **Test Automation Ready Output**: 
   - Provide test scenarios in structured format that can be parsed
   - Include specific selectors, expected values, and timing considerations
   - Group related tests into test suites

IGNORE THESE COMMON SPA PATTERNS (NOT BUGS):
- Links that trigger state changes without URL navigation
- JavaScript-driven content updates
- Dynamic loading of page sections
- Modal overlays for user interactions

OUTPUT FORMAT:
Structure your response with clear sections:
1. **User Experience Map**: High-level workflows identified exhaustively
2. **Critical Test Scenarios**: Detailed test cases for automation
3. **Integration Points**: External dependencies (wallets, APIs)
4. **Recommended Test Priorities**: What to test first

For each test scenario, use this format:
```
Test: [Descriptive Name]
Priority: High/Medium/Low
User Story: A user wants to...
Preconditions: [Starting state]
Steps:
  1. [Action] -> [Expected Result]
  2. [Action] -> [Expected Result]
Assertions:
  - Verify [specific condition]
  - Check [specific element/state]
Automation Notes: [Selectors, timing, special considerations]
```

Focus on creating comprehensive, automatable test scenarios rather than identifying bugs."""

        return prompt
    
    async def _save_chatgpt_analysis(self, chatgpt_response: str, exploration_results: Dict[str, Any]) -> list[str]:
        """Save ChatGPT analysis in multiple formats."""
        
        saved_files = []
        timestamp = datetime.now().isoformat()
        
        # 1. Save raw ChatGPT response
        raw_file = self.session_dir / "reports" / "chatgpt_raw_response.txt"
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(f"ChatGPT Bug Analysis Report\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Website: {self.base_url}\n")
            f.write("=" * 80 + "\n\n")
            f.write(chatgpt_response)
        saved_files.append(str(raw_file))
        
        # 2. Save structured JSON analysis
        structured_analysis = self._parse_chatgpt_response(chatgpt_response, exploration_results)
        json_file = self.session_dir / "reports" / "chatgpt_bug_analysis.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(structured_analysis, f, indent=2, default=str)
        saved_files.append(str(json_file))
        
        # 3. Save formatted Markdown report
        markdown_file = self.session_dir / "reports" / "chatgpt_bug_analysis.md"
        markdown_content = self._create_markdown_report(structured_analysis, chatgpt_response)
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        saved_files.append(str(markdown_file))
        
        return saved_files
    
    def _parse_chatgpt_response(self, response: str, exploration_results: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ChatGPT response into structured data."""
        
        return {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "website": self.base_url,
                "model_used": "gpt-4o",
                "analysis_version": "1.0"
            },
            "session_summary": exploration_results.get('exploration_summary', {}),
            "chatgpt_analysis": {
                "raw_response": response,
                "analysis_length": len(response),
                "contains_bug_reports": "bug" in response.lower() or "issue" in response.lower(),
                "contains_recommendations": "recommend" in response.lower() or "suggest" in response.lower(),
                "severity_mentions": {
                    "critical": response.lower().count("critical"),
                    "high": response.lower().count("high"),
                    "medium": response.lower().count("medium"), 
                    "low": response.lower().count("low")
                }
            },
            "automated_flags": {
                "potential_bugs_detected": len([line for line in response.split('\n') if 'bug' in line.lower()]),
                "performance_issues_mentioned": 'performance' in response.lower() or 'slow' in response.lower(),
                "navigation_issues_mentioned": 'navigation' in response.lower() or 'link' in response.lower(),
                "requires_developer_attention": any(word in response.lower() for word in ['critical', 'high', 'bug', 'broken', 'error']),
                "analysis_confidence": "high" if len(response) > 500 else "medium"
            },
            "next_steps": {
                "requires_manual_review": True,
                "priority_level": "high" if any(word in response.lower() for word in ['critical', 'broken']) else "medium",
                "estimated_review_time": "15-30 minutes"
            }
        }
    
    def _create_markdown_report(self, structured_data: Dict[str, Any], raw_response: str) -> str:
        """Create a formatted Markdown report with integrated typo analysis."""
        
        metadata = structured_data["analysis_metadata"]
        summary = structured_data.get("session_summary", {})
        flags = structured_data.get("automated_flags", {})
        
        markdown = f"""# 🤖 ChatGPT Bug Analysis Report

## 📊 Session Overview
- **Website**: {metadata['website']}
- **Session ID**: {metadata['session_id']}
- **Analysis Date**: {metadata['timestamp']}
- **Model Used**: {metadata['model_used']}

## 🎯 Testing Summary
- **Total Actions**: {summary.get('total_actions_performed', 0)}
- **Success Rate**: {summary.get('success_rate', 0):.1%}
- **Duration**: {summary.get('duration', 0):.1f} seconds
- **Pages Visited**: {summary.get('pages_visited', 0)}
- **Errors Found**: {summary.get('errors_found', 0)}

## 🚨 Automated Analysis Flags
- **Potential Bugs Detected**: {flags.get('potential_bugs_detected', 0)}
- **Performance Issues**: {'Yes' if flags.get('performance_issues_mentioned') else 'No'}
- **Navigation Issues**: {'Yes' if flags.get('navigation_issues_mentioned') else 'No'}
- **Requires Developer Attention**: {'Yes' if flags.get('requires_developer_attention') else 'No'}
- **Analysis Confidence**: {flags.get('analysis_confidence', 'unknown').title()}

## 🔍 ChatGPT Analysis

{raw_response}"""

        # Add typo analysis section if available
        typo_analysis = self._get_typo_analysis_content()
        if typo_analysis:
            markdown += f"""

## 🔤 Content Quality Analysis (Typo Detection)

{typo_analysis}"""

        markdown += f"""

## 📋 Next Steps
- **Manual Review Required**: {structured_data.get('next_steps', {}).get('requires_manual_review', True)}
- **Priority Level**: {structured_data.get('next_steps', {}).get('priority_level', 'medium').title()}
- **Estimated Review Time**: {structured_data.get('next_steps', {}).get('estimated_review_time', '15-30 minutes')}
"""
        
        return markdown 
    
    def _get_typo_analysis_content(self) -> str:
        """Get typo analysis content to include in the main report."""
        typo_analysis_file = self.session_dir / "reports" / "typo_analysis_summary.txt"
        llm_typo_file = self.session_dir / "reports" / "llm_typo_analysis.json"
        
        content = ""
        
        # Check for LLM typo analysis results first
        if llm_typo_file.exists():
            try:
                import json
                with open(llm_typo_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                llm_analysis = data.get('llm_analysis', {})
                word_candidates = data.get('word_candidates', [])
                
                analyzed_words = llm_analysis.get('analyzed_words', 0)
                confirmed_typos = llm_analysis.get('confirmed_typos', [])
                intentional_words = llm_analysis.get('intentional_words', [])
                uncertain_words = llm_analysis.get('uncertain_words', [])
                confidence_score = llm_analysis.get('confidence_score', 0)
                
                content += f"""### 📊 Summary
- **Total word candidates analyzed**: {analyzed_words}
- **Confirmed typos**: {len(confirmed_typos)}
- **Intentional words**: {len(intentional_words)}
- **Uncertain words**: {len(uncertain_words)}
- **Analysis confidence**: {confidence_score:.1%}

"""
                
                if confirmed_typos:
                    content += """### 🚨 Confirmed Typos
The following spelling errors were detected and should be corrected:

"""
                    for i, typo in enumerate(confirmed_typos, 1):
                        word = typo.get('word', 'Unknown')
                        correction = typo.get('suggested_correction', 'N/A')
                        reason = typo.get('reasoning', 'No reason provided')
                        content += f"{i}. **'{word}'** → **'{correction}'**\n   - Reason: {reason}\n\n"
                
                if intentional_words and len(intentional_words) <= 20:  # Only show if reasonable number
                    content += f"""### ✅ Intentional Words ({len(intentional_words)} found)
The following words were correctly identified as intentional (brand names, tech terms, etc.):

"""
                    # Group by category for better readability
                    by_category = {}
                    for word in intentional_words:
                        category = word.get('category', 'general')
                        if category not in by_category:
                            by_category[category] = []
                        by_category[category].append(word.get('word', 'Unknown'))
                    
                    for category, words in by_category.items():
                        content += f"**{category.title()} terms**: {', '.join(words[:10])}"
                        if len(words) > 10:
                            content += f" (and {len(words) - 10} more)"
                        content += "\n\n"
                
                elif intentional_words and len(intentional_words) > 20:
                    content += f"""### ✅ Intentional Words
{len(intentional_words)} words were correctly identified as intentional (brand names, tech terms, etc.) - see detailed report for full list.

"""
                
                if uncertain_words:
                    content += """### ❓ Words Requiring Manual Review
The following words need human judgment:

"""
                    for i, word in enumerate(uncertain_words, 1):
                        word_text = word.get('word', 'Unknown')
                        reason = word.get('reasoning', 'No reason provided')
                        content += f"{i}. **'{word_text}'** - {reason}\n"
                
                # Add testing recommendation
                if confirmed_typos:
                    content += f"""
### 🧪 Testing Recommendations
- **Priority**: Medium - Content quality impacts user experience
- **Test Type**: Automated spell-checking in CI/CD pipeline
- **Action Items**: 
  - Fix the {len(confirmed_typos)} confirmed typo(s) above
  - Consider adding spell-check validation to content workflow
  - Review content creation and review processes

"""
                elif analyzed_words > 0:
                    content += """
### 🧪 Testing Recommendations
- **Priority**: Low - No typos detected
- **Status**: ✅ Content quality is good
- **Recommendation**: Continue current content review practices

"""
                
                return content.strip()
                
            except Exception as e:
                logger.warning(f"Failed to read LLM typo analysis: {e}")
        
        # Fallback to basic typo analysis file if LLM analysis not available
        if typo_analysis_file.exists():
            try:
                with open(typo_analysis_file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                    
                # Extract key info from the text file
                lines = raw_content.split('\n')
                summary_lines = []
                
                for line in lines:
                    if 'Total word candidates analyzed:' in line or \
                       'Confirmed typos:' in line or \
                       'Intentional words:' in line or \
                       'Analysis confidence:' in line:
                        summary_lines.append(f"- **{line.strip()}**")
                
                if summary_lines:
                    content = "### 📊 Summary\n" + '\n'.join(summary_lines) + "\n\n"
                    content += "See detailed typo analysis report for complete breakdown.\n"
                    return content
                        
            except Exception as e:
                logger.warning(f"Failed to read typo analysis summary: {e}")
        
        return "" 