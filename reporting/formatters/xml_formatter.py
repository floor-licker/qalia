"""
Session Reporter Utility

Handles generation of comprehensive session reports, XML sitemaps, and analysis data
for website exploration results.
"""

import json
import logging
import time
from typing import Dict, Any, List
from xml.dom import minidom
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class SessionReporter:
    """
    Generates comprehensive reports from exploration session data.
    
    Provides XML sitemap generation, JSON reports, and formatted
    analysis data for ChatGPT consumption.
    """
    
    def __init__(self, base_url: str, domain: str):
        self.base_url = base_url
        self.domain = domain
    
    def generate_xml_sitemap(self, session_data: Dict[str, Any]) -> str:
        """Generate XML sitemap for ChatGPT analysis."""
        root = ET.Element('ApplicationStateFingerprint')
        root.set('domain', self.domain)
        root.set('base_url', self.base_url)
        root.set('timestamp', str(time.time()))
        
        # Add summary
        summary = ET.SubElement(root, 'Summary')
        
        elements_found = session_data.get('total_elements', 0)
        actions_performed = session_data.get('total_actions', 0)
        errors_found = session_data.get('total_errors', 0)
        
        ET.SubElement(summary, 'TotalElements').text = str(elements_found)
        ET.SubElement(summary, 'ActionsPerformed').text = str(actions_performed)
        ET.SubElement(summary, 'ErrorsFound').text = str(errors_found)
        
        # Add states
        states_section = ET.SubElement(root, 'States')
        states_data = session_data.get('states', {})
        
        for state_hash, state_info in states_data.items():
            state_elem = ET.SubElement(states_section, 'State')
            state_elem.set('hash', state_hash)
            state_elem.set('url', state_info.get('url', ''))
            
            elements_elem = ET.SubElement(state_elem, 'Elements')
            elements_elem.set('count', str(state_info.get('elements_count', 0)))
        
        # Add errors
        if session_data.get('errors'):
            errors_section = ET.SubElement(root, 'Errors')
            
            for error in session_data['errors'][:10]:  # Limit for XML size
                error_elem = ET.SubElement(errors_section, 'Error')
                error_elem.set('type', error.get('type', 'unknown'))
                error_elem.set('severity', error.get('severity', 'medium'))
                error_elem.text = error.get('message', '')[:200]
        
        # Format and return
        return self._format_xml(root)
    
    def generate_json_report(self, session_data: Dict[str, Any]) -> str:
        """Generate comprehensive JSON report."""
        report = {
            'session_info': {
                'base_url': self.base_url,
                'domain': self.domain,
                'timestamp': time.time(),
                'duration': session_data.get('duration', 0)
            },
            'exploration_summary': {
                'total_elements_discovered': session_data.get('total_elements', 0),
                'total_actions_performed': session_data.get('total_actions', 0),
                'total_errors_found': session_data.get('total_errors', 0),
                'states_discovered': len(session_data.get('states', {})),
                'success_rate': session_data.get('success_rate', 0.0)
            },
            'detailed_results': session_data
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def _format_xml(self, root: ET.Element) -> str:
        """Format XML with proper indentation."""
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def generate_chatgpt_analysis_prompt(self, xml_sitemap: str, 
                                       session_data: Dict[str, Any]) -> str:
        """Generate analysis prompt for ChatGPT."""
        prompt = f"""
Please analyze this website exploration report for bugs, anomalies, and issues:

Domain: {self.domain}
Base URL: {self.base_url}

EXPLORATION SUMMARY:
- Elements Discovered: {session_data.get('total_elements', 0)}
- Actions Performed: {session_data.get('total_actions', 0)}
- Errors Found: {session_data.get('total_errors', 0)}
- Success Rate: {session_data.get('success_rate', 0.0):.2%}

XML STATE FINGERPRINT:
{xml_sitemap}

Please identify:
1. Critical bugs and errors
2. Usability issues
3. Broken functionality
4. Performance problems
5. Accessibility concerns

Focus on actionable findings that developers can investigate and fix.
"""
        return prompt 