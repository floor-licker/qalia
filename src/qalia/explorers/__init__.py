"""
Explorer Implementations

Different explorer implementations for various use cases:
- BasicExplorer: Simple systematic exploration
- AdvancedExplorer: Full-featured exploration with AI
- SpecializedExplorers: Domain-specific explorers (SPA, ecommerce, DeFi)
"""

from .basic_explorer import CleanWebExplorer as BasicExplorer

__all__ = [
    'BasicExplorer'
] 