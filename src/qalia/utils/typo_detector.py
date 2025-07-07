"""
Typo Detection Utility

Smart typo detection system that:
1. Extracts all visible text from web pages
2. Identifies words not in English dictionary with their frequency
3. Uses ChatGPT/LLM analysis to distinguish typos from intentional words (brands, tech terms, etc.)
4. Tracks potential typos across sessions for intelligent reporting

Features:
- Dictionary-based word filtering to find candidates
- Frequency tracking for context analysis
- LLM-powered judgment for intelligent typo classification
- Context-aware detection (ignores URLs, code, etc.)
- Integration with existing action results and ChatGPT reporting
"""

import logging
import re
import json
import os
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WordCandidate:
    """Represents a word candidate for typo analysis."""
    word: str
    frequency: int
    contexts: List[str]  # List of contexts where this word appears
    element_types: List[str]  # Types of elements where found
    pages_found: List[str]  # URLs where this word was found
    first_seen: str  # First context where seen
    confidence_factors: Dict[str, Any]  # Factors affecting confidence


@dataclass
class LLMTypoAnalysis:
    """Results from LLM analysis of word candidates."""
    analyzed_words: int
    confirmed_typos: List[Dict[str, Any]]
    intentional_words: List[Dict[str, Any]]
    uncertain_words: List[Dict[str, Any]]
    analysis_reasoning: str
    confidence_score: float


@dataclass
class TypoReport:
    """Comprehensive typo analysis report."""
    total_words_analyzed: int
    candidate_words_found: int
    llm_analysis: Optional[LLMTypoAnalysis]
    word_candidates: List[WordCandidate]
    tech_terms_filtered: int
    common_patterns_filtered: int
    session_summary: Dict[str, Any]


class TypoDetector:
    """
    Intelligent typo detection system using LLM judgment.
    """
    
    def __init__(self, session_dir: Optional[str] = None):
        """
        Initialize typo detector.
        
        Args:
            session_dir: Directory for storing typo analysis data
        """
        self.session_dir = session_dir
        self.min_word_length = 3      # Only check words 3+ characters
        self.min_frequency_for_llm = 1  # Send words to LLM even if seen once
        
        # Word candidates tracking
        self.word_candidates: Dict[str, WordCandidate] = {}
        
        # Common patterns to ignore (definitely not typos)
        self.ignore_patterns = [
            r'^https?://',           # URLs
            r'^\w+@\w+\.\w+',       # Email addresses
            r'^\d+[\d\.\,]*$',      # Numbers
            r'^[A-Z]{2,}$',         # Acronyms
            r'^\w*\d\w*$',          # Words with numbers (like API keys)
            r'^[A-F0-9]{8,}$',      # Hex strings
            r'^\$\w+',              # CSS variables
            r'^\w+\(\)',            # Function names
            r'^[a-z]+-[a-z-]+$',    # CSS classes like 'btn-primary'
            r'^0x[a-fA-F0-9]+$',    # Ethereum addresses
        ]
        
        # Common programming/web/crypto terms (not typos)
        self.tech_terms = {
            'api', 'url', 'html', 'css', 'js', 'json', 'xml', 'http', 'https',
            'www', 'src', 'href', 'div', 'span', 'img', 'btn', 'nav', 'app',
            'dev', 'prod', 'config', 'auth', 'oauth', 'jwt', 'ssl', 'tls',
            'github', 'gitlab', 'npm', 'cdn', 'aws', 'ui', 'ux', 'seo', 'cms',
            'defi', 'nft', 'dao', 'dapp', 'eth', 'btc', 'crypto', 'blockchain',
            'metamask', 'argent', 'braavos', 'ethereum', 'polygon', 'arbitrum',
            'optimism', 'starknet', 'mainnet', 'testnet', 'wei', 'gwei', 'steth',
            'usdc', 'usdt', 'dai', 'weth', 'lido', 'aave', 'uniswap', 'compound',
            'chainlink', 'yearn', 'curve', 'balancer', 'synthetix', 'makerdao',
            'opensea', 'rarible', 'superrare', 'async', 'await', 'const', 'let',
            'var', 'npm', 'yarn', 'webpack', 'babel', 'eslint', 'tsx', 'jsx'
        }
        
        # Initialize English dictionary
        self.english_words = self._load_english_dictionary()
        
        # Load previous analysis data
        self.analysis_file = None
        if session_dir:
            self.analysis_file = Path(session_dir) / "reports" / "typo_candidates.json"
            self._load_previous_analysis()
        
        logger.info(f"🔤 Enhanced typo detector initialized with {len(self.english_words):,} English words")
    
    def _load_english_dictionary(self) -> Set[str]:
        """Load English dictionary from multiple sources."""
        english_words = set()
        
        # Basic common words (expanded set)
        common_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 
            'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 
            'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my',
            'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if',
            'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like',
            'time', 'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
            'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look',
            'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two',
            'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because',
            'any', 'these', 'give', 'day', 'most', 'us', 'is', 'water', 'long', 'find',
            'here', 'thing', 'place', 'right', 'move', 'try', 'man', 'hand', 'may', 'turn',
            'ask', 'play', 'run', 'own', 'say', 'great', 'where', 'help', 'through', 'much',
            'before', 'line', 'too', 'mean', 'old', 'any', 'same', 'tell', 'boy', 'follow',
            'came', 'want', 'show', 'also', 'around', 'form', 'three', 'small', 'set',
            'put', 'end', 'why', 'again', 'turn', 'every', 'start', 'home', 'never', 'open',
            'seem', 'together', 'next', 'white', 'children', 'begin', 'got', 'walk', 'example',
            'ease', 'paper', 'group', 'always', 'music', 'those', 'both', 'mark', 'often',
            'letter', 'until', 'mile', 'river', 'car', 'feet', 'care', 'second', 'book',
            'carry', 'took', 'science', 'eat', 'room', 'friend', 'began', 'idea', 'fish',
            'mountain', 'stop', 'once', 'base', 'hear', 'horse', 'cut', 'sure', 'watch',
            'color', 'face', 'wood', 'main', 'enough', 'plain', 'girl', 'usual', 'young',
            'ready', 'above', 'ever', 'red', 'list', 'though', 'feel', 'talk', 'bird',
            'soon', 'body', 'dog', 'family', 'direct', 'leave', 'song', 'measure', 'door',
            'product', 'black', 'short', 'numeral', 'class', 'wind', 'question', 'happen',
            'complete', 'ship', 'area', 'half', 'rock', 'order', 'fire', 'south', 'problem',
            'piece', 'told', 'knew', 'pass', 'since', 'top', 'whole', 'king', 'space',
            'heard', 'best', 'hour', 'better', 'during', 'hundred', 'five', 'remember',
            'step', 'early', 'hold', 'west', 'ground', 'interest', 'reach', 'fast', 'verb',
            'sing', 'listen', 'six', 'table', 'travel', 'less', 'morning', 'ten', 'simple',
            'several', 'vowel', 'toward', 'war', 'lay', 'against', 'pattern', 'slow',
            'center', 'love', 'person', 'money', 'serve', 'appear', 'road', 'map', 'rain',
            'rule', 'govern', 'pull', 'cold', 'notice', 'voice', 'unit', 'power', 'town',
            'fine', 'certain', 'fly', 'fall', 'lead', 'cry', 'dark', 'machine', 'note',
            'wait', 'plan', 'figure', 'star', 'box', 'noun', 'field', 'rest', 'correct',
            'able', 'pound', 'done', 'beauty', 'drive', 'stood', 'contain', 'front', 'teach',
            'week', 'final', 'gave', 'green', 'oh', 'quick', 'develop', 'ocean', 'warm',
            'free', 'minute', 'strong', 'special', 'mind', 'behind', 'clear', 'tail', 'produce',
            'fact', 'street', 'inch', 'multiply', 'nothing', 'course', 'stay', 'wheel', 'full',
            'force', 'blue', 'object', 'decide', 'surface', 'deep', 'moon', 'island', 'foot',
            'system', 'busy', 'test', 'record', 'boat', 'common', 'gold', 'possible', 'plane',
            'stead', 'dry', 'wonder', 'laugh', 'thousands', 'ago', 'ran', 'check', 'game',
            'shape', 'equate', 'hot', 'miss', 'brought', 'heat', 'snow', 'tire', 'bring',
            'yes', 'distant', 'fill', 'east', 'paint', 'language', 'among', 'grand', 'ball',
            'yet', 'wave', 'drop', 'heart', 'am', 'present', 'heavy', 'dance', 'engine',
            'position', 'arm', 'wide', 'sail', 'material', 'size', 'vary', 'settle', 'speak',
            'weight', 'general', 'ice', 'matter', 'circle', 'pair', 'include', 'divide',
            'syllable', 'felt', 'perhaps', 'pick', 'sudden', 'count', 'square', 'reason',
            'length', 'represent', 'art', 'subject', 'region', 'energy', 'hunt', 'probable',
            'bed', 'brother', 'egg', 'ride', 'cell', 'believe', 'fraction', 'forest', 'sit',
            'race', 'window', 'store', 'summer', 'train', 'sleep', 'prove', 'lone', 'leg',
            'exercise', 'wall', 'catch', 'mount', 'wish', 'sky', 'board', 'joy', 'winter',
            'sat', 'written', 'wild', 'instrument', 'kept', 'glass', 'grass', 'cow', 'job',
            'edge', 'sign', 'visit', 'past', 'soft', 'fun', 'bright', 'gas', 'weather',
            'month', 'million', 'bear', 'finish', 'happy', 'hope', 'flower', 'clothe',
            'strange', 'gone', 'jump', 'baby', 'eight', 'village', 'meet', 'root', 'buy',
            'raise', 'solve', 'metal', 'whether', 'push', 'seven', 'paragraph', 'third',
            'shall', 'held', 'hair', 'describe', 'cook', 'floor', 'either', 'result',
            'burn', 'hill', 'safe', 'cat', 'century', 'consider', 'type', 'law', 'bit',
            'coast', 'copy', 'phrase', 'silent', 'tall', 'sand', 'soil', 'roll', 'temperature',
            'finger', 'industry', 'value', 'fight', 'lie', 'beat', 'excite', 'natural',
            'view', 'sense', 'ear', 'else', 'quite', 'broke', 'case', 'middle', 'kill',
            'son', 'lake', 'moment', 'scale', 'loud', 'spring', 'observe', 'child', 'straight',
            'consonant', 'nation', 'dictionary', 'milk', 'speed', 'method', 'organ', 'pay',
            'age', 'section', 'dress', 'cloud', 'surprise', 'quiet', 'stone', 'tiny', 'climb',
            'bad', 'oil', 'blood', 'touch', 'grew', 'cent', 'mix', 'team', 'wire', 'cost',
            'lost', 'brown', 'wear', 'garden', 'equal', 'sent', 'choose', 'fell', 'fit',
            'flow', 'fair', 'bank', 'collect', 'save', 'control', 'decimal', 'gentle',
            'woman', 'captain', 'practice', 'separate', 'difficult', 'doctor', 'please',
            'protect', 'noon', 'whose', 'locate', 'ring', 'character', 'insect', 'caught',
            'period', 'indicate', 'radio', 'spoke', 'atom', 'human', 'history', 'effect',
            'electric', 'expect', 'crop', 'modern', 'element', 'hit', 'student', 'corner',
            'party', 'supply', 'bone', 'rail', 'imagine', 'provide', 'agree', 'thus',
            'capital', 'chair', 'danger', 'fruit', 'rich', 'thick', 'soldier', 'process',
            'operate', 'guess', 'necessary', 'sharp', 'wing', 'create', 'neighbor', 'wash',
            'bat', 'rather', 'crowd', 'corn', 'compare', 'poem', 'string', 'bell', 'depend',
            'meat', 'rub', 'tube', 'famous', 'dollar', 'stream', 'fear', 'sight', 'thin',
            'triangle', 'planet', 'hurry', 'chief', 'colony', 'clock', 'mine', 'tie', 'enter',
            'major', 'fresh', 'search', 'send', 'yellow', 'gun', 'allow', 'print', 'dead',
            'spot', 'desert', 'suit', 'current', 'lift', 'rose', 'continue', 'block', 'chart',
            'hat', 'sell', 'success', 'company', 'subtract', 'event', 'particular', 'deal',
            'swim', 'term', 'opposite', 'wife', 'shoe', 'shoulder', 'spread', 'arrange',
            'camp', 'invent', 'cotton', 'born', 'determine', 'quart', 'nine', 'truck',
            'noise', 'level', 'chance', 'gather', 'shop', 'stretch', 'throw', 'shine',
            'property', 'column', 'molecule', 'select', 'wrong', 'gray', 'repeat', 'require',
            'broad', 'prepare', 'salt', 'nose', 'plural', 'anger', 'claim', 'continent',
            'oxygen', 'sugar', 'death', 'pretty', 'skill', 'women', 'season', 'solution',
            'magnet', 'silver', 'thank', 'branch', 'match', 'suffix', 'especially', 'fig',
            'afraid', 'huge', 'sister', 'steel', 'discuss', 'forward', 'similar', 'guide',
            'experience', 'score', 'apple', 'bought', 'led', 'pitch', 'coat', 'mass', 'card',
            'band', 'rope', 'slip', 'win', 'dream', 'evening', 'condition', 'feed', 'tool',
            'total', 'basic', 'smell', 'valley', 'nor', 'double', 'seat', 'arrive', 'master',
            'track', 'parent', 'shore', 'division', 'sheet', 'substance', 'favor', 'connect',
            'post', 'spend', 'chord', 'fat', 'glad', 'original', 'share', 'station', 'dad',
            'bread', 'charge', 'proper', 'bar', 'offer', 'segment', 'slave', 'duck', 'instant',
            'market', 'degree', 'populate', 'chick', 'dear', 'enemy', 'reply', 'drink',
            'occur', 'support', 'speech', 'nature', 'range', 'steam', 'motion', 'path',
            'liquid', 'log', 'meant', 'quotient', 'teeth', 'shell', 'neck', 'claim',
            'stake', 'staking', 'unstake', 'yield', 'farming', 'liquidity', 'pool', 'swap',
            'bridge', 'deposit', 'withdraw', 'connect', 'wallet', 'balance', 'transaction',
            'block', 'hash', 'gas', 'fee', 'reward', 'penalty', 'slashing', 'validator'
        }
        
        english_words.update(common_words)
        
        # Add tech terms to English words (they're valid, not typos)
        english_words.update(self.tech_terms)
        
        return english_words
    
    def _load_previous_analysis(self) -> None:
        """Load previous word candidate analysis."""
        if self.analysis_file and self.analysis_file.exists():
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert back to WordCandidate objects
                for word_data in data.get('word_candidates', []):
                    candidate = WordCandidate(**word_data)
                    self.word_candidates[candidate.word] = candidate
                    
                logger.info(f"📖 Loaded {len(self.word_candidates)} previous word candidates")
            except Exception as e:
                logger.warning(f"Could not load previous analysis: {e}")
    
    def _save_analysis_data(self) -> None:
        """Save word candidate analysis."""
        if not self.analysis_file:
            return
            
        # Ensure directory exists
        self.analysis_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'word_candidates': [asdict(candidate) for candidate in self.word_candidates.values()],
            'analysis_metadata': {
                'total_candidates': len(self.word_candidates),
                'last_updated': str(Path(__file__).stat().st_mtime),
                'english_words_count': len(self.english_words),
                'tech_terms_count': len(self.tech_terms)
            }
        }
        
        try:
            with open(self.analysis_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save analysis data: {e}")
    
    def _should_ignore_word(self, word: str) -> bool:
        """Check if word should be ignored (patterns, known terms)."""
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if re.match(pattern, word):
                return True
        
        # Check if it's a known tech term
        if word.lower() in self.tech_terms:
            return True
            
        # Check minimum length
        if len(word) < self.min_word_length:
            return True
            
        return False
    
    def _extract_words_from_text(self, text: str) -> List[str]:
        """Extract words from text, filtering out non-word content."""
        # Remove common non-text patterns first
        clean_text = re.sub(r'https?://[^\s]+', '', text)  # URLs
        clean_text = re.sub(r'\w+@\w+\.\w+', '', clean_text)  # Emails
        clean_text = re.sub(r'\d+[\d\.\,]*', '', clean_text)  # Numbers
        
        # Extract words (letters only, 3+ chars)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_text)
        
        # Filter and clean
        filtered_words = []
        for word in words:
            word = word.lower().strip()
            if word and not self._should_ignore_word(word):
                filtered_words.append(word)
        
        return filtered_words

    async def extract_page_text(self, page) -> Dict[str, Any]:
        """Extract all visible text from page elements."""
        try:
            text_data = {
                'page_url': page.url,
                'elements': [],
                'extraction_time': str(Path(__file__).stat().st_mtime)
            }
            
            # Define selectors for text extraction
            text_selectors = [
                'h1, h2, h3, h4, h5, h6',      # Headers
                'p',                            # Paragraphs  
                'span',                         # Spans
                'div',                          # Divs
                'button',                       # Buttons
                'a',                            # Links
                'label',                        # Labels
                'input[placeholder]',           # Input placeholders
                'li',                           # List items
                '[title]',                      # Elements with titles
                '[aria-label]',                 # Accessibility labels
                'td, th',                       # Table cells
            ]
            
            for selector in text_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    
                    for i, element in enumerate(elements):
                        try:
                            # Get element type
                            element_type = await element.evaluate('el => el.tagName.toLowerCase()')
                            
                            # Extract text based on element type
                            text = ""
                            if element_type == 'input':
                                text = await element.get_attribute('placeholder')
                            elif selector == '[title]':
                                text = await element.get_attribute('title')
                            elif selector == '[aria-label]':
                                text = await element.get_attribute('aria-label')
                            else:
                                text = await element.inner_text()
                            
                            if text and text.strip():
                                # Generate a basic selector for context
                                try:
                                    elem_id = await element.get_attribute('id')
                                    if elem_id:
                                        context_selector = f"#{elem_id}"
                                    else:
                                        context_selector = f"{selector}:nth-of-type({i+1})"
                                except:
                                    context_selector = f"{selector}:nth-of-type({i+1})"
                                
                                text_data['elements'].append({
                                    'text': text.strip(),
                                    'element_type': element_type,
                                    'selector': context_selector,
                                    'length': len(text.strip())
                                })
                        
                        except Exception as e:
                            logger.debug(f"Error processing element {i}: {e}")
                
                except Exception as e:
                    logger.debug(f"Error extracting text from {selector}: {e}")
            
            return text_data
            
        except Exception as e:
            logger.error(f"Failed to extract page text: {e}")
            return {'page_url': page.url, 'elements': [], 'error': str(e)}

    def analyze_text_for_typos(self, text_data: Dict[str, Any]) -> TypoReport:
        """
        Analyze extracted text data to identify word candidates for LLM analysis.
        
        Args:
            text_data: Text data from extract_page_text()
            
        Returns:
            TypoReport with candidate words for LLM judgment
        """
        page_url = text_data['page_url']
        words_analyzed = 0
        candidates_found = 0
        tech_terms_filtered = 0
        patterns_filtered = 0
        
        # Analyze each text element
        for element in text_data.get('elements', []):
            text = element['text']
            words = self._extract_words_from_text(text)
            words_analyzed += len(words)
            
            # Check each word for candidate status
            for word in words:
                # Skip if it's in English dictionary
                if word in self.english_words:
                    continue
                
                # Skip if it's a tech term (already handled above but double-check)
                if word.lower() in self.tech_terms:
                    tech_terms_filtered += 1
                    continue
                
                # Skip if matches ignore patterns
                if self._should_ignore_word(word):
                    patterns_filtered += 1
                    continue
                
                # This is a candidate word - track it
                candidates_found += 1
                
                if word not in self.word_candidates:
                    self.word_candidates[word] = WordCandidate(
                        word=word,
                        frequency=0,
                        contexts=[],
                        element_types=[],
                        pages_found=[],
                        first_seen=text[:100],
                        confidence_factors={}
                    )
                
                # Update candidate data
                candidate = self.word_candidates[word]
                candidate.frequency += 1
                
                # Add context (limit to avoid memory issues)
                context = text[:100] + ('...' if len(text) > 100 else '')
                if context not in candidate.contexts:
                    candidate.contexts.append(context)
                    if len(candidate.contexts) > 5:  # Keep only 5 most recent contexts
                        candidate.contexts = candidate.contexts[-5:]
                
                # Track element types
                if element['element_type'] not in candidate.element_types:
                    candidate.element_types.append(element['element_type'])
                
                # Track pages
                if page_url not in candidate.pages_found:
                    candidate.pages_found.append(page_url)
                
                # Update confidence factors
                candidate.confidence_factors.update({
                    'appears_in_multiple_contexts': len(candidate.contexts) > 1,
                    'appears_in_multiple_elements': len(candidate.element_types) > 1,
                    'appears_on_multiple_pages': len(candidate.pages_found) > 1,
                    'high_frequency': candidate.frequency > 3,
                    'element_types': candidate.element_types
                })
        
        # Save updated analysis data
        self._save_analysis_data()
        
        # Create word candidates list for this analysis
        session_candidates = [
            candidate for candidate in self.word_candidates.values()
            if page_url in candidate.pages_found
        ]
        
        report = TypoReport(
            total_words_analyzed=words_analyzed,
            candidate_words_found=candidates_found,
            llm_analysis=None,  # Will be filled by LLM analysis
            word_candidates=session_candidates,
            tech_terms_filtered=tech_terms_filtered,
            common_patterns_filtered=patterns_filtered,
            session_summary=self.get_session_summary()
        )
        
        logger.info(f"🔤 Word candidate analysis complete:")
        logger.info(f"   📊 Words analyzed: {words_analyzed}")
        logger.info(f"   ❓ Candidate words: {candidates_found}")
        logger.info(f"   🔧 Tech terms filtered: {tech_terms_filtered}")
        logger.info(f"   🚫 Patterns filtered: {patterns_filtered}")
        logger.info(f"   📝 Total unique candidates: {len(self.word_candidates)}")
        
        return report
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of all word candidates found in this session."""
        if not self.word_candidates:
            return {
                'total_candidates': 0,
                'unique_words': 0,
                'high_frequency_words': 0,
                'multi_context_words': 0,
                'ready_for_llm_analysis': False
            }
        
        high_freq_words = [c for c in self.word_candidates.values() if c.frequency > 2]
        multi_context_words = [c for c in self.word_candidates.values() if len(c.contexts) > 1]
        
        return {
            'total_candidates': len(self.word_candidates),
            'unique_words': len(set(c.word for c in self.word_candidates.values())),
            'high_frequency_words': len(high_freq_words),
            'multi_context_words': len(multi_context_words),
            'most_frequent_candidates': Counter([c.word for c in self.word_candidates.values()]).most_common(10),
            'candidates_by_element_type': self._group_candidates_by_element_type(),
            'ready_for_llm_analysis': len(self.word_candidates) > 0
        }
    
    def _group_candidates_by_element_type(self) -> Dict[str, int]:
        """Group candidates by the element types they appear in."""
        element_type_counts = Counter()
        for candidate in self.word_candidates.values():
            for element_type in candidate.element_types:
                element_type_counts[element_type] += 1
        return dict(element_type_counts)
    
    def generate_llm_analysis_prompt(self) -> str:
        """
        Generate a prompt for LLM analysis of word candidates.
        
        Returns:
            Formatted prompt string for ChatGPT/LLM analysis
        """
        if not self.word_candidates:
            return "No word candidates found for analysis."
        
        # Sort candidates by frequency (most frequent first)
        sorted_candidates = sorted(
            self.word_candidates.values(), 
            key=lambda c: c.frequency, 
            reverse=True
        )
        
        prompt = f"""Please analyze these {len(sorted_candidates)} words found on a website to determine which are likely typos vs intentional words (brand names, technical terms, etc.).

CONTEXT: This is from a web application. Such sites often contain:
- Domain-specific terminology
- Brand names and product names  
- Technical jargon and abbreviations
- Acronyms and initialisms
- Multi-language content
- Industry-specific terms

For each word, classify as:
1. TYPO - Likely a spelling mistake
2. INTENTIONAL - Brand name, tech term, or valid non-English word
3. UNCERTAIN - Could be either, needs human review

WORD CANDIDATES TO ANALYZE:

"""
        
        for i, candidate in enumerate(sorted_candidates[:50], 1):  # Limit to top 50
            contexts_text = " | ".join(candidate.contexts[:3])  # Show up to 3 contexts
            
            prompt += f"{i}. '{candidate.word}' (frequency: {candidate.frequency})\n"
            prompt += f"   Contexts: {contexts_text}\n"
            prompt += f"   Found in: {', '.join(candidate.element_types)}\n"
            
            if len(candidate.pages_found) > 1:
                prompt += f"   Appears on {len(candidate.pages_found)} different pages\n"
            
            prompt += "\n"
        
        prompt += """
Please respond in this JSON format:
{
  "analysis": {
    "confirmed_typos": [
      {"word": "word", "reasoning": "why it's a typo", "suggested_correction": "correct spelling"}
    ],
    "intentional_words": [
      {"word": "word", "reasoning": "why it's intentional", "category": "brand/tech/foreign/etc"}
    ],
    "uncertain_words": [
      {"word": "word", "reasoning": "why uncertain"}
    ]
  },
  "summary": {
    "total_analyzed": 0,
    "typos_found": 0,
    "intentional_found": 0,
    "uncertain_found": 0,
    "confidence": "high/medium/low"
  }
}"""
        
        return prompt
    
    async def analyze_with_llm(self, api_key: str = None) -> LLMTypoAnalysis:
        """
        Send word candidates to LLM for analysis.
        
        Args:
            api_key: OpenAI API key (optional, will check environment)
            
        Returns:
            LLMTypoAnalysis results or None if failed
        """
        if not self.word_candidates:
            logger.info("🔤 No word candidates to analyze with LLM")
            return None
        
        # Get API key
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY not found - skipping LLM typo analysis")
            return None
        
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            
            prompt = self.generate_llm_analysis_prompt()
            
            logger.info(f"🤖 Sending {len(self.word_candidates)} word candidates to LLM for analysis...")
            
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert linguist and web content analyst. Analyze words to distinguish between typos and intentional terms (brands, technical terms, etc.). Be conservative - only mark clear spelling errors as typos."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                import json
                
                # Try to extract JSON from response if it's wrapped in markdown or other text
                json_text = response_text
                if '```json' in response_text:
                    # Extract JSON from markdown code block
                    start = response_text.find('```json') + 7
                    end = response_text.find('```', start)
                    if end != -1:
                        json_text = response_text[start:end].strip()
                elif '{' in response_text:
                    # Find first { and last }
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start != -1 and end > start:
                        json_text = response_text[start:end]
                
                analysis_data = json.loads(json_text)
                
                llm_analysis = LLMTypoAnalysis(
                    analyzed_words=analysis_data.get('summary', {}).get('total_analyzed', len(self.word_candidates)),
                    confirmed_typos=analysis_data.get('analysis', {}).get('confirmed_typos', []),
                    intentional_words=analysis_data.get('analysis', {}).get('intentional_words', []),
                    uncertain_words=analysis_data.get('analysis', {}).get('uncertain_words', []),
                    analysis_reasoning=response_text,
                    confidence_score=self._convert_confidence_to_score(
                        analysis_data.get('summary', {}).get('confidence', 'medium')
                    )
                )
                
                logger.info(f"✅ LLM analysis complete:")
                logger.info(f"   🔍 Words analyzed: {llm_analysis.analyzed_words}")
                logger.info(f"   ❌ Confirmed typos: {len(llm_analysis.confirmed_typos)}")
                logger.info(f"   ✅ Intentional words: {len(llm_analysis.intentional_words)}")
                logger.info(f"   ❓ Uncertain words: {len(llm_analysis.uncertain_words)}")
                
                # Save analysis results
                if self.session_dir:
                    await self._save_llm_analysis(llm_analysis)
                
                return llm_analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response (first 500 chars): {response_text[:500]}...")
                raise ValueError(f"❌ CRITICAL: LLM returned unparseable response. This indicates an AI model issue: {e}")
                
        except ImportError:
            raise ImportError("❌ CRITICAL: OpenAI library not installed. Typo analysis requires OpenAI. Run: pip install openai>=1.0.0")
        except Exception as e:
            raise RuntimeError(f"❌ CRITICAL: LLM typo analysis failed: {e}")
    
    def _convert_confidence_to_score(self, confidence_str: str) -> float:
        """Convert confidence string to numeric score."""
        confidence_map = {
            'high': 0.9,
            'medium': 0.7,
            'low': 0.5
        }
        return confidence_map.get(confidence_str.lower(), 0.7)
    
    async def _save_llm_analysis(self, analysis: LLMTypoAnalysis) -> None:
        """Save LLM analysis results to files."""
        if not self.session_dir:
            return
        
        reports_dir = Path(self.session_dir) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed analysis as JSON
        analysis_file = reports_dir / "llm_typo_analysis.json"
        analysis_data = {
            'llm_analysis': asdict(analysis),
            'word_candidates': [asdict(c) for c in self.word_candidates.values()],
            'metadata': {
                'analysis_timestamp': str(Path(__file__).stat().st_mtime),
                'total_candidates_analyzed': len(self.word_candidates),
                'session_dir': str(self.session_dir)
            }
        }
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, default=str)
        
        # Save human-readable summary
        summary_file = reports_dir / "typo_analysis_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("🔤 LLM Typo Analysis Summary\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total word candidates analyzed: {analysis.analyzed_words}\n")
            f.write(f"Confirmed typos: {len(analysis.confirmed_typos)}\n")
            f.write(f"Intentional words: {len(analysis.intentional_words)}\n")
            f.write(f"Uncertain words: {len(analysis.uncertain_words)}\n")
            f.write(f"Analysis confidence: {analysis.confidence_score:.1%}\n\n")
            
            if analysis.confirmed_typos:
                f.write("🚨 CONFIRMED TYPOS:\n")
                f.write("-" * 30 + "\n")
                for typo in analysis.confirmed_typos:
                    f.write(f"• '{typo['word']}' → '{typo.get('suggested_correction', 'N/A')}'\n")
                    f.write(f"  Reason: {typo['reasoning']}\n\n")
            
            if analysis.intentional_words:
                f.write("✅ INTENTIONAL WORDS:\n")
                f.write("-" * 30 + "\n")
                for word in analysis.intentional_words:
                    f.write(f"• '{word['word']}' ({word.get('category', 'Unknown')})\n")
                    f.write(f"  Reason: {word['reasoning']}\n\n")
            
            if analysis.uncertain_words:
                f.write("❓ UNCERTAIN WORDS (Manual Review Needed):\n")
                f.write("-" * 30 + "\n")
                for word in analysis.uncertain_words:
                    f.write(f"• '{word['word']}'\n")
                    f.write(f"  Reason: {word['reasoning']}\n\n")
        
        logger.info(f"💾 LLM typo analysis saved:")
        logger.info(f"   📄 {analysis_file}")
        logger.info(f"   📄 {summary_file}")

    def generate_chatgpt_xml(self) -> str:
        """
        Generate XML report for ChatGPT that includes LLM-analyzed typos.
        
        Returns:
            XML string with enhanced typo analysis data
        """
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        root = Element("EnhancedTypoAnalysis")
        
        # Summary
        summary = SubElement(root, "Summary")
        session_summary = self.get_session_summary()
        
        SubElement(summary, "TotalCandidatesFound").text = str(session_summary.get('total_candidates', 0))
        SubElement(summary, "UniqueWords").text = str(session_summary.get('unique_words', 0))
        SubElement(summary, "HighFrequencyWords").text = str(session_summary.get('high_frequency_words', 0))
        SubElement(summary, "MultiContextWords").text = str(session_summary.get('multi_context_words', 0))
        SubElement(summary, "ReadyForLLMAnalysis").text = str(session_summary.get('ready_for_llm_analysis', False))
        
        # Word candidates section
        candidates_section = SubElement(root, "WordCandidates")
        candidates_section.set("total", str(len(self.word_candidates)))
        
        for word, candidate in self.word_candidates.items():
            candidate_elem = SubElement(candidates_section, "Candidate")
            
            SubElement(candidate_elem, "Word").text = candidate.word
            SubElement(candidate_elem, "Frequency").text = str(candidate.frequency)
            SubElement(candidate_elem, "ElementTypes").text = ", ".join(candidate.element_types)
            SubElement(candidate_elem, "PagesFound").text = str(len(candidate.pages_found))
            SubElement(candidate_elem, "FirstContext").text = candidate.first_seen
            
            # Confidence factors
            factors_elem = SubElement(candidate_elem, "ConfidenceFactors")
            for factor, value in candidate.confidence_factors.items():
                factor_elem = SubElement(factors_elem, "Factor")
                factor_elem.set("name", factor)
                factor_elem.text = str(value)
        
        # LLM Analysis prompt
        llm_section = SubElement(root, "LLMAnalysisReady")
        prompt = self.generate_llm_analysis_prompt()
        SubElement(llm_section, "AnalysisPrompt").text = prompt[:1000] + ("..." if len(prompt) > 1000 else "")
        SubElement(llm_section, "ReadyForAnalysis").text = str(len(self.word_candidates) > 0)
        
        # Convert to pretty XML
        xml_str = tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ") 