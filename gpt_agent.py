"""
GPT-4 agent for making decisions about web interactions and evaluating outcomes.
"""

import json
import os
from typing import Dict, List, Any, Optional
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class GPTAgent:
    """
    AI agent that uses GPT-4 to make decisions about web interactions and evaluate results.
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo-preview"):
        """
        Initialize the GPT agent.
        
        Args:
            api_key: OpenAI API key (if not provided, will use OPENAI_API_KEY env var)
            model: OpenAI model to use for decisions
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        
        # System prompts for different tasks
        self.action_system_prompt = """You are an AI QA agent that explores web applications to find bugs and test functionality.

Your goal is to systematically test web applications by:
1. Interacting with forms, buttons, and links
2. Trying to break functionality 
3. Finding edge cases and error conditions
4. Testing user workflows

When given a list of interactive elements on a page, choose the MOST INTERESTING action to perform next that would:
- Test important functionality
- Potentially reveal bugs
- Explore new areas of the application
- Fill out forms with realistic test data

Respond with a JSON object containing:
{
  "action": "click|type|select|navigate",
  "target": "CSS selector or element identifier", 
  "value": "text to type (for type action) or option value (for select)",
  "reasoning": "brief explanation of why this action was chosen"
}

If no good actions are available, respond with {"action": "wait", "reasoning": "explanation"}.

Prioritize:
1. Filling out and submitting forms
2. Clicking important buttons (login, submit, save, etc.)
3. Navigating to new sections
4. Testing interactive components
5. Exploring error conditions"""

        self.evaluation_system_prompt = """You are an AI QA agent that evaluates whether web application behavior is correct or indicates a bug.

Analyze the provided information about a web interaction and determine if the result indicates:
1. SUCCESS - Normal, expected behavior
2. BUG - Unexpected behavior, errors, or broken functionality  
3. WARNING - Suspicious behavior that might indicate an issue

Look for these potential issues:
- Error messages or HTTP error codes
- Unexpected redirects or page changes
- Missing content or broken layouts
- Console errors or JavaScript failures
- Form validation issues
- Accessibility problems
- Performance issues

Respond with a JSON object:
{
  "status": "SUCCESS|BUG|WARNING",
  "confidence": 0.1-1.0,
  "issues": ["list of specific issues found"],
  "summary": "brief description of what happened",
  "severity": "LOW|MEDIUM|HIGH" 
}"""

    def choose_action(self, 
                     elements: List[Dict[str, Any]], 
                     page_info: Dict[str, Any], 
                     previous_actions: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use GPT-4 to choose the next action to perform on the page.
        
        Args:
            elements: List of interactive elements found on the page
            page_info: Information about the current page
            previous_actions: List of previously performed actions
            
        Returns:
            Dictionary containing the chosen action
        """
        try:
            # Prepare context for the LLM
            context = {
                "page_info": page_info,
                "interactive_elements": elements[:20],  # Limit to prevent token overflow
                "previous_actions": (previous_actions or [])[-5:],  # Last 5 actions
                "url": page_info.get('url', 'unknown')
            }
            
            user_prompt = f"""Current page analysis:

URL: {context['url']}
Title: {page_info.get('title', 'No title')}
Headings: {page_info.get('headings', [])}

Interactive elements found:
"""
            
            for i, element in enumerate(elements[:15]):  # Show top 15 elements
                user_prompt += f"\n{i+1}. Type: {element['type']}"
                
                if element.get('text'):
                    user_prompt += f", Text: '{element['text'][:50]}'"
                if element.get('placeholder'):
                    user_prompt += f", Placeholder: '{element['placeholder'][:30]}'"
                if element.get('href'):
                    user_prompt += f", Link: {element['href'][:50]}"
                    
                user_prompt += f", Selector: {element['selector']}"
            
            if previous_actions:
                user_prompt += f"\n\nRecent actions performed:\n"
                for action in previous_actions[-3:]:
                    action_data = action.get('action', {})
                    user_prompt += f"- {action_data.get('action')} on {action_data.get('target', 'unknown')}\n"
            
            user_prompt += "\n\nWhat should I do next to test this application effectively?"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.action_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            action_data = self._parse_json_response(response_text)
            
            if not action_data or 'action' not in action_data:
                logger.warning(f"Invalid action response from GPT: {response_text}")
                return {"action": "wait", "reasoning": "Invalid response from AI"}
            
            logger.info(f"GPT chose action: {action_data.get('action')} - {action_data.get('reasoning', '')}")
            return action_data
            
        except Exception as e:
            logger.error(f"Error getting action from GPT: {e}")
            return {"action": "wait", "reasoning": f"Error: {str(e)}"}
    
    def evaluate_result(self, 
                       action: Dict[str, Any], 
                       before_state: Dict[str, Any], 
                       after_state: Dict[str, Any],
                       console_logs: List[str] = None) -> Dict[str, Any]:
        """
        Use GPT-4 to evaluate whether an action result indicates a bug or success.
        
        Args:
            action: The action that was performed
            before_state: Page state before the action
            after_state: Page state after the action
            console_logs: Any console error messages
            
        Returns:
            Dictionary containing the evaluation result
        """
        try:
            # Prepare evaluation context
            context = {
                "action": action,
                "url_before": before_state.get('url', 'unknown'),
                "url_after": after_state.get('url', 'unknown'),
                "title_before": before_state.get('title', ''),
                "title_after": after_state.get('title', ''),
                "errors_before": before_state.get('error_indicators', []),
                "errors_after": after_state.get('error_indicators', []),
                "console_logs": console_logs or []
            }
            
            user_prompt = f"""Action performed: {action.get('action')} on {action.get('target', 'unknown')}
Action reasoning: {action.get('reasoning', 'No reasoning provided')}

BEFORE ACTION:
- URL: {context['url_before']}
- Title: {context['title_before']}
- Error indicators: {context['errors_before']}

AFTER ACTION:
- URL: {context['url_after']}
- Title: {context['title_after']}
- Error indicators: {context['errors_after']}

Console logs: {context['console_logs']}

Changes detected:
- URL changed: {context['url_before'] != context['url_after']}
- Title changed: {context['title_before'] != context['title_after']}
- New errors appeared: {len(context['errors_after']) > len(context['errors_before'])}

Please evaluate if this behavior indicates a bug, success, or warning."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.evaluation_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            evaluation = self._parse_json_response(response_text)
            
            if not evaluation or 'status' not in evaluation:
                logger.warning(f"Invalid evaluation response from GPT: {response_text}")
                return {
                    "status": "WARNING",
                    "confidence": 0.5,
                    "issues": ["Could not parse AI evaluation"],
                    "summary": "AI evaluation failed",
                    "severity": "LOW"
                }
            
            logger.info(f"GPT evaluation: {evaluation.get('status')} - {evaluation.get('summary', '')}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error getting evaluation from GPT: {e}")
            return {
                "status": "WARNING",
                "confidence": 0.5,
                "issues": [f"Evaluation error: {str(e)}"],
                "summary": "Could not evaluate result",
                "severity": "LOW"
            }
    
    def suggest_test_inputs(self, input_element: Dict[str, Any]) -> str:
        """
        Generate appropriate test input for a form field.
        
        Args:
            input_element: Dictionary describing the input element
            
        Returns:
            Suggested test value
        """
        try:
            input_type = input_element.get('input_type', 'text')
            placeholder = input_element.get('placeholder', '')
            name = input_element.get('name', '')
            
            prompt = f"""Generate a realistic test value for this form field:
Type: {input_type}
Name: {name}
Placeholder: {placeholder}

Provide ONLY the test value, no explanation. For emails use test@example.com format.
For passwords use TestPassword123! format. For names use realistic names.
For phone numbers use +1234567890 format."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You generate realistic test data for form fields. Respond with only the test value."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating test input: {e}")
            # Fallback to simple values
            fallback_values = {
                'email': 'test@example.com',
                'password': 'TestPassword123!',
                'text': 'Test Input',
                'tel': '+1234567890',
                'url': 'https://example.com'
            }
            return fallback_values.get(input_element.get('input_type', 'text'), 'Test')
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response from GPT, handling potential formatting issues.
        
        Args:
            response_text: Raw response text from GPT
            
        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        try:
            # Try direct JSON parsing first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object in the text
            json_match = re.search(r'\{[^{}]*\}', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Could not parse JSON from response: {response_text}")
            return None
    
    def generate_exploration_strategy(self, page_info: Dict[str, Any], visited_pages: List[str]) -> Dict[str, Any]:
        """
        Generate a high-level strategy for exploring the application.
        
        Args:
            page_info: Information about the current page
            visited_pages: List of previously visited page URLs
            
        Returns:
            Dictionary containing exploration strategy
        """
        try:
            prompt = f"""I'm exploring a web application for QA testing. 

Current page: {page_info.get('url', 'unknown')}
Title: {page_info.get('title', 'No title')}
Forms on page: {len(page_info.get('forms', []))}
Navigation present: {page_info.get('has_nav', False)}

Pages already visited: {len(visited_pages)}
Recent pages: {visited_pages[-5:] if visited_pages else 'None'}

Based on this information, suggest a testing strategy. What types of functionality should I prioritize testing? What are the most important user flows to verify?

Respond with a JSON object:
{{
  "priority_areas": ["list of functionality to prioritize"],
  "test_scenarios": ["list of test scenarios to attempt"],
  "risk_areas": ["areas likely to contain bugs"],
  "exploration_approach": "description of how to proceed"
}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a QA strategist helping plan comprehensive testing of web applications."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=400
            )
            
            response_text = response.choices[0].message.content.strip()
            strategy = self._parse_json_response(response_text)
            
            if strategy:
                logger.info(f"Generated exploration strategy: {strategy.get('exploration_approach', '')}")
                return strategy
            else:
                # Fallback strategy
                return {
                    "priority_areas": ["Forms", "Navigation", "User workflows"],
                    "test_scenarios": ["Fill out forms", "Test navigation", "Try error conditions"],
                    "risk_areas": ["Input validation", "Authentication", "Data submission"],
                    "exploration_approach": "Systematically test all interactive elements"
                }
                
        except Exception as e:
            logger.error(f"Error generating exploration strategy: {e}")
            return {
                "priority_areas": ["Basic functionality"],
                "test_scenarios": ["Test available interactions"],
                "risk_areas": ["Unknown"],
                "exploration_approach": "Explore available elements systematically"
            } 