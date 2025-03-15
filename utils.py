import json
import os
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from PyQt5.QtGui import QColor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('utils')

# Try to import numpy for ML features, with fallback to stub implementation
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available. Code suggestion features will be limited.")

def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """
    Convert hex color to rgba string.
    
    Args:
        hex_color: Hex color code (e.g., '#3498db')
        alpha: Alpha value (0-1)
        
    Returns:
        rgba string (e.g., 'rgba(52, 152, 219, 1.0)')
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
    return f"rgba({r}, {g}, {b}, {alpha})"

def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    Load a JSON file with error handling.
    
    Args:
        file_path: Path to the JSON file
        default: Default value to return if loading fails
        
    Returns:
        The parsed JSON data or the default value if loading fails
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"File not found: {file_path}")
            return default if default is not None else {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return default if default is not None else {}

def save_json_file(file_path: str, data: Any, indent: int = 2) -> bool:
    """
    Save data to a JSON file with error handling.
    
    Args:
        file_path: Path to save the JSON file
        data: Data to save
        indent: Indentation level for the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory:
            ensure_directory_exists(directory)
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}")
        return False

def ensure_directory_exists(directory_path: str) -> bool:
    """
    Check if a directory exists and create it if it doesn't.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if the directory exists or was created, False otherwise
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            logger.info(f"Created directory: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def color_with_brightness(color: str, brightness_factor: float) -> str:
    """
    Adjust the brightness of a color.
    
    Args:
        color: Hex color code (e.g., '#3498db')
        brightness_factor: Factor to adjust brightness (>1 for lighter, <1 for darker)
        
    Returns:
        Adjusted hex color code
    """
    if not color.startswith('#'):
        return color
    
    # Remove leading #
    hex_color = color.lstrip('#')
    
    # Expand shorthand (e.g., #abc to #aabbcc)
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    # Convert to RGB
    r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
    
    # Adjust brightness
    r = max(0, min(255, int(r * brightness_factor)))
    g = max(0, min(255, int(g * brightness_factor)))
    b = max(0, min(255, int(b * brightness_factor)))
    
    # Convert back to hex
    return f"#{r:02x}{g:02x}{b:02x}"

def format_code(code: str, indent_size: int = 4) -> str:
    """
    Format Python code with proper indentation.
    
    Args:
        code: Python code to format
        indent_size: Number of spaces per indentation level
        
    Returns:
        Formatted Python code
    """
    lines = code.split('\n')
    result = []
    indent_level = 0
    
    for line in lines:
        # Strip leading/trailing whitespace
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            result.append('')
            continue
        
        # Check for dedent before processing the line
        if (stripped.startswith('elif ') or 
            stripped.startswith('else:') or 
            stripped.startswith('except') or 
            stripped.startswith('finally:') or 
            stripped == 'pass'):
            indent_level = max(0, indent_level - 1)
        
        # Add indentation
        indentation = ' ' * indent_size * indent_level
        result.append(indentation + stripped)
        
        # Check for indent after processing the line
        if (stripped.endswith(':') and not stripped.startswith('#')):
            if not (stripped.startswith('class ') and ' def ' in stripped):  # Skip one-line method definitions
                indent_level += 1
        
        # Check for specific dedent keywords
        if stripped.startswith('return ') or stripped == 'return' or stripped.startswith('break') or stripped.startswith('continue'):
            indent_level = max(0, indent_level - 1)
    
    return '\n'.join(result)

class CodeSuggestionModel:
    """
    Simple machine learning model for code suggestions based on n-grams.
    
    This model analyzes code patterns and suggests completions for code blocks.
    It uses a probabilistic approach based on token sequences seen during training.
    """
    def __init__(self, n_gram_size: int = 3):
        """
        Initialize the code suggestion model.
        
        Args:
            n_gram_size: Size of the n-grams to use for analysis
        """
        self.n_gram_size = n_gram_size
        self.transitions = {}  # Maps n-grams to possible next tokens
        self.token_counts = {}  # Frequency of each token
        self.total_tokens = 0
        
        # Initialize numpy arrays if available
        if NUMPY_AVAILABLE:
            self.transition_probs = {}
    
    def tokenize(self, code: str) -> List[str]:
        """
        Tokenize Python code into a list of tokens.
        
        Args:
            code: Python code to tokenize
            
        Returns:
            List of tokens
        """
        # Simple tokenization by whitespace and operators
        # In a real implementation, we would use a proper Python tokenizer
        code = code.replace('\n', ' <NEWLINE> ')
        code = code.replace(':', ' : ')
        code = code.replace('(', ' ( ')
        code = code.replace(')', ' ) ')
        code = code.replace('[', ' [ ')
        code = code.replace(']', ' ] ')
        code = code.replace('{', ' { ')
        code = code.replace('}', ' } ')
        code = code.replace(',', ' , ')
        code = code.replace('.', ' . ')
        code = code.replace('=', ' = ')
        code = code.replace('==', ' == ')
        code = code.replace('!=', ' != ')
        code = code.replace('>', ' > ')
        code = code.replace('<', ' < ')
        code = code.replace('>=', ' >= ')
        code = code.replace('<=', ' <= ')
        code = code.replace('+', ' + ')
        code = code.replace('-', ' - ')
        code = code.replace('*', ' * ')
        code = code.replace('/', ' / ')
        
        # Split by whitespace and filter out empty tokens
        tokens = [token for token in code.split() if token]
        
        return tokens
    
    def train(self, code_samples: List[str]) -> None:
        """
        Train the model on a list of code samples.
        
        Args:
            code_samples: List of Python code strings
        """
        for code in code_samples:
            tokens = self.tokenize(code)
            
            # Count token frequencies
            for token in tokens:
                self.token_counts[token] = self.token_counts.get(token, 0) + 1
                self.total_tokens += 1
            
            # Build n-gram transitions
            for i in range(len(tokens) - self.n_gram_size):
                n_gram = tuple(tokens[i:i+self.n_gram_size])
                next_token = tokens[i+self.n_gram_size]
                
                if n_gram not in self.transitions:
                    self.transitions[n_gram] = {}
                
                self.transitions[n_gram][next_token] = self.transitions[n_gram].get(next_token, 0) + 1
        
        # Calculate transition probabilities
        if NUMPY_AVAILABLE:
            for n_gram, next_tokens in self.transitions.items():
                total = sum(next_tokens.values())
                self.transition_probs[n_gram] = {
                    token: count / total for token, count in next_tokens.items()
                }
    
    def suggest(self, context: str, max_suggestions: int = 3) -> List[Tuple[str, float]]:
        """
        Generate suggestions for code completion based on the context.
        
        Args:
            context: Current code context
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of (suggestion, probability) tuples
        """
        # Tokenize the context
        context_tokens = self.tokenize(context)
        
        # If we don't have enough context tokens, return the most common tokens
        if len(context_tokens) < self.n_gram_size:
            if not self.token_counts:
                return []
                
            # Return the most common tokens
            top_tokens = sorted(self.token_counts.items(), key=lambda x: x[1], reverse=True)[:max_suggestions]
            return [(token, count / self.total_tokens) for token, count in top_tokens]
        
        # Get the most recent n-gram
        recent_n_gram = tuple(context_tokens[-self.n_gram_size:])
        
        # If we haven't seen this n-gram, return the most common tokens
        if recent_n_gram not in self.transitions:
            if not self.token_counts:
                return []
                
            # Return the most common tokens
            top_tokens = sorted(self.token_counts.items(), key=lambda x: x[1], reverse=True)[:max_suggestions]
            return [(token, count / self.total_tokens) for token, count in top_tokens]
        
        # Get the next token suggestions based on transition probabilities
        next_tokens = self.transitions[recent_n_gram]
        suggestions = sorted(next_tokens.items(), key=lambda x: x[1], reverse=True)[:max_suggestions]
        
        # Calculate probabilities
        total = sum(next_tokens.values())
        return [(token, count / total) for token, count in suggestions]
    
    def save(self, file_path: str) -> bool:
        """
        Save the model to a file.
        
        Args:
            file_path: Path to save the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            model_data = {
                "n_gram_size": self.n_gram_size,
                "transitions": {
                    # Convert tuple keys to strings for JSON
                    ','.join(n_gram): next_tokens
                    for n_gram, next_tokens in self.transitions.items()
                },
                "token_counts": self.token_counts,
                "total_tokens": self.total_tokens
            }
            
            return save_json_file(file_path, model_data)
        except Exception as e:
            logger.error(f"Error saving model to {file_path}: {e}")
            return False
    
    @classmethod
    def load(cls, file_path: str) -> Optional['CodeSuggestionModel']:
        """
        Load the model from a file.
        
        Args:
            file_path: Path to load the model from
            
        Returns:
            The loaded model or None if loading failed
        """
        try:
            model_data = load_json_file(file_path)
            if not model_data:
                return None
            
            # Create a new model instance
            model = cls(n_gram_size=model_data.get("n_gram_size", 3))
            
            # Load transitions
            model.transitions = {
                # Convert string keys back to tuples
                tuple(n_gram.split(',')): next_tokens
                for n_gram, next_tokens in model_data.get("transitions", {}).items()
            }
            
            # Load token counts
            model.token_counts = model_data.get("token_counts", {})
            model.total_tokens = model_data.get("total_tokens", 0)
            
            # Calculate transition probabilities if numpy is available
            if NUMPY_AVAILABLE:
                for n_gram, next_tokens in model.transitions.items():
                    total = sum(next_tokens.values())
                    model.transition_probs[n_gram] = {
                        token: count / total for token, count in next_tokens.items()
                    }
            
            return model
        except Exception as e:
            logger.error(f"Error loading model from {file_path}: {e}")
            return None

try:
    import numpy as np
    
    # Only define ML functions if numpy is available
    class CodeSuggestionModel:
        """A simple code suggestion model using n-gram analysis"""
        def __init__(self, n=3):
            self.n = n
            self.transitions = {}
            self.start_tokens = {}
            
        def train(self, code_samples):
            """Train the model on a list of code samples"""
            for code in code_samples:
                tokens = self._tokenize(code)
                if len(tokens) < self.n:
                    continue
                    
                # Record starting n-grams
                start_key = ' '.join(tokens[:self.n-1])
                self.start_tokens[start_key] = self.start_tokens.get(start_key, 0) + 1
                
                # Record transitions
                for i in range(len(tokens) - self.n + 1):
                    context = ' '.join(tokens[i:i+self.n-1])
                    next_token = tokens[i+self.n-1]
                    
                    if context not in self.transitions:
                        self.transitions[context] = {}
                    
                    self.transitions[context][next_token] = self.transitions[context].get(next_token, 0) + 1
                    
        def _tokenize(self, code):
            """Simple tokenization for Python code"""
            import re
            # Replace newlines with space
            code = code.replace('\n', ' ')
            # Add spaces around punctuation
            code = re.sub(r'([^\w\s])', r' \1 ', code)
            # Remove extra whitespace
            code = re.sub(r'\s+', ' ', code).strip()
            return code.split()
            
        def suggest_completion(self, context, max_length=10):
            """Suggest completion for given context"""
            tokens = self._tokenize(context)
            if len(tokens) < self.n - 1:
                return ""
                
            # Get the last n-1 tokens as context
            context_key = ' '.join(tokens[-(self.n-1):])
            
            # If we have no transitions for this context, return empty
            if context_key not in self.transitions:
                return ""
                
            # Choose next token based on frequency
            candidates = self.transitions[context_key]
            next_token = max(candidates.items(), key=lambda x: x[1])[0]
            
            # Generate rest of suggestion
            suggestion = [next_token]
            for _ in range(max_length - 1):
                # Update context
                context_tokens = tokens[-(self.n-2):] + suggestion
                context_key = ' '.join(context_tokens[-(self.n-1):])
                
                if context_key not in self.transitions:
                    break
                    
                # Choose next token
                candidates = self.transitions[context_key]
                next_token = max(candidates.items(), key=lambda x: x[1])[0]
                suggestion.append(next_token)
                
            return ' '.join(suggestion)
            
    def load_code_model():
        """Load or create a code suggestion model"""
        model_file = 'code_model.json'
        model = CodeSuggestionModel()
        
        # Try to load existing model
        data = load_json_file(model_file)
        if data:
            model.transitions = data.get('transitions', {})
            model.start_tokens = data.get('start_tokens', {})
            model.n = data.get('n', 3)
        
        return model
        
    def save_code_model(model):
        """Save the code suggestion model"""
        model_file = 'code_model.json'
        data = {
            'transitions': model.transitions,
            'start_tokens': model.start_tokens,
            'n': model.n
        }
        save_json_file(model_file, data)
        
except ImportError:
    logger.warning("NumPy not available, machine learning features will be disabled")
    
    # Provide stub implementations
    class CodeSuggestionModel:
        def __init__(self, n=3):
            self.n = n
            
        def train(self, code_samples):
            pass
            
        def suggest_completion(self, context, max_length=10):
            return ""
            
    def load_code_model():
        return CodeSuggestionModel()
        
    def save_code_model(model):
        pass

class DotDict(dict):
    """
    A dictionary that allows dot notation access to its items.
    This makes template formatting cleaner in the generate_code method.
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return ""

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            pass

def format_error_message(error: Exception, block_type: str = "") -> str:
    """
    Format an error message for display to the user.
    
    Args:
        error: The exception that occurred
        block_type: The type of block where the error occurred
        
    Returns:
        A formatted error message string
    """
    prefix = f"Error in {block_type}: " if block_type else "Error: "
    return f"{prefix}{str(error)}"

def safely_format_template(template: str, context: dict) -> str:
    """
    Safely format a template string with a context dictionary.
    
    Args:
        template: The template string to format
        context: The context dictionary with values
        
    Returns:
        The formatted string or an error message
    """
    try:
        return template.format(**context)
    except Exception as e:
        logger.error(f"Error formatting template: {str(e)}")
        return f"# Error formatting template: {str(e)}"

def is_variable_reference(value: str) -> bool:
    """
    Check if a string looks like a variable reference.
    
    Args:
        value: The string to check
        
    Returns:
        True if the string looks like a variable reference
    """
    if not value:
        return False
        
    # Check if it has quotes (string literal)
    if value.startswith('"') or value.startswith("'"):
        return False
        
    # Check if it's a digit (number literal)
    if value.isdigit():
        return False
        
    # Check for expressions with operators
    operators = ['+', '-', '*', '/', '(', ')', '[', ']', '{', '}']
    if any(op in value for op in operators):
        return False
        
    # Check for valid variable naming pattern (allowing underscores)
    return value.isalnum() or '_' in value

def apply_safe_quote_rules(value: str, data_type: str = "string") -> str:
    """
    Apply quoting rules to a value based on its context and type.
    
    Args:
        value: The value to potentially quote
        data_type: The expected data type
        
    Returns:
        The value, potentially with quotes added
    """
    # If already quoted, keep as is
    if value.startswith('"') or value.startswith("'"):
        return value
        
    # For string type, check if this is a variable reference
    if data_type == "string":
        if is_variable_reference(value):
            return value
        else:
            # Add quotes for strings that aren't variable references
            return f'"{value}"'
    
    # For other types, don't add quotes
    return value 