"""
Exploration Strategies

Different approaches to website exploration:
- Systematic: BFS/DFS methodical exploration
- Intelligent: AI-guided exploration using GPT
- Hybrid: Combines systematic and intelligent approaches
"""

from .systematic import SystematicStrategy
from .intelligent_agent import GPTAgent

__all__ = ['SystematicStrategy', 'GPTAgent'] 