import logging
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                           QTextEdit, QLabel, QPushButton, QFrame)

from settings_loader import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('output_panel')

class OutputPanel(QWidget):
    """
    Panel displaying the generated Python code and execution output.
    Provides code highlighting and execution results.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Title bar for the output section
        self.title_bar = QWidget()
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        
        # Title label
        self.title_label = QLabel("Output")
        self.title_label.setStyleSheet("font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        # Add clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_execution_output)
        title_layout.addWidget(self.clear_button)
        
        self.layout.addWidget(self.title_bar)
        
        # Splitter for code preview and execution output
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)
        
        # Code preview section
        self.code_preview = QTextEdit()
        self.code_preview.setReadOnly(True)
        self.setup_code_preview()
        self.splitter.addWidget(self.code_preview)
        
        # Execution output section
        self.execution_output = QTextEdit()
        self.execution_output.setReadOnly(True)
        self.setup_execution_output()
        self.splitter.addWidget(self.execution_output)
        
        # Set initial sizes
        self.splitter.setSizes([int(self.height() * 0.6), int(self.height() * 0.4)])
        
        # Apply theme
        self.update_style()
    
    def setup_code_preview(self):
        """Configure the code preview text edit"""
        # Set monospace font
        font_family = settings.get_app_setting("ui", "font_family", default="Consolas, 'Courier New', monospace")
        font_size = settings.get_app_setting("ui", "font_size", default=12)
        
        font = QFont(font_family.split(',')[0].strip(), font_size)
        font.setFixedPitch(True)
        self.code_preview.setFont(font)
        
        # Set header
        self.code_preview.setPlaceholderText("Code preview will appear here")
    
    def setup_execution_output(self):
        """Configure the execution output text edit"""
        # Set monospace font
        font_family = settings.get_app_setting("ui", "font_family", default="Consolas, 'Courier New', monospace")
        font_size = settings.get_app_setting("ui", "font_size", default=12)
        
        font = QFont(font_family.split(',')[0].strip(), font_size)
        font.setFixedPitch(True)
        self.execution_output.setFont(font)
        
        # Set header
        self.execution_output.setPlaceholderText("Execution output will appear here")
    
    def update_style(self):
        """Update the panel style based on the current theme"""
        theme = settings.get_current_theme()
        
        # Get colors from theme
        panel_color = theme.get("panel_color", "#ffffff")
        text_color = theme.get("text_color", "#333333")
        border_color = theme.get("border_color", "#dddddd")
        
        # Style the components
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {panel_color};
                color: {text_color};
            }}
            QTextEdit {{
                background-color: {panel_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-top: none;
            }}
            QPushButton {{
                background-color: {theme.get("accent_color", "#3498db")};
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {theme.get("highlight_color", "#9b59b6")};
            }}
        """)
        
        # Title bar style
        self.title_bar.setStyleSheet(f"""
            background-color: {theme.get("accent_color", "#3498db")};
            color: white;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        """)
        
        self.title_label.setStyleSheet("color: white; font-weight: bold;")
        
        # Set a custom style for the clear button
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                padding: 3px 8px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
    
    def set_code_preview(self, code: str):
        """
        Set the code preview with syntax highlighting.
        
        Args:
            code: Python code to display
        """
        # Clean and normalize the code to prevent indentation errors
        cleaned_code = self.clean_code(code)
        
        # Apply syntax highlighting
        highlighted_code = self.apply_syntax_highlighting(cleaned_code)
        self.code_preview.setHtml(highlighted_code)
    
    def clean_code(self, code: str) -> str:
        """Clean and normalize the code to prevent indentation errors."""
        if not code.strip():
            return ""
            
        # Split into lines
        lines = code.split('\n')
        
        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in lines]
        
        # Remove empty lines at the beginning and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Normalize indentation
        # Find the first non-empty line's indentation
        first_indent = None
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if first_indent is None:
                    first_indent = indent
                if indent < first_indent:
                    first_indent = indent
                    
        # If there's inconsistent indentation at the root level, fix it
        if first_indent and first_indent > 0:
            normalized_lines = []
            for line in lines:
                if line.strip():
                    # Only adjust lines that have content
                    curr_indent = len(line) - len(line.lstrip())
                    if curr_indent >= first_indent:
                        normalized_lines.append(line[first_indent:])
                    else:
                        normalized_lines.append(line)
                else:
                    normalized_lines.append(line)
            lines = normalized_lines
        
        # Join lines back together
        return '\n'.join(lines)
    
    def apply_syntax_highlighting(self, code: str) -> str:
        """
        Apply syntax highlighting to Python code.
        
        Args:
            code: Python code to highlight
            
        Returns:
            HTML formatted code with syntax highlighting
        """
        # Simple syntax highlighting using HTML and CSS
        # In a production app, you'd use a more sophisticated highlighting library
        
        # Get theme colors
        theme = settings.get_current_theme()
        bg_color = theme.get("panel_color", "#ffffff")
        
        # Define colors for different syntax elements
        colors = {
            'keyword': "#0000FF",  # blue
            'builtin': "#990000",  # dark red
            'string': "#008800",   # green
            'comment': "#888888",  # gray
            'number': "#FF8800",   # orange
            'function': "#660066", # purple
            'class': "#0066BB",    # dark blue
            'operator': "#666600", # olive
        }
        
        # Simple list of Python keywords for highlighting
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif',
            'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
        ]
        
        builtins = [
            'abs', 'all', 'any', 'bool', 'chr', 'dict', 'dir', 'enumerate', 'eval', 'exec',
            'filter', 'float', 'format', 'frozenset', 'getattr', 'hasattr', 'hex', 'id',
            'input', 'int', 'isinstance', 'issubclass', 'len', 'list', 'map', 'max', 'min',
            'next', 'object', 'open', 'ord', 'pow', 'print', 'property', 'range', 'repr',
            'reversed', 'round', 'set', 'setattr', 'slice', 'sorted', 'str', 'sum', 'super',
            'tuple', 'type', 'vars', 'zip'
        ]
        
        # Start with HTML scaffolding
        html = f"""
        <html>
        <head>
        <style>
            body {{ background-color: {bg_color}; font-family: monospace; white-space: pre; }}
            .keyword {{ color: {colors['keyword']}; font-weight: bold; }}
            .builtin {{ color: {colors['builtin']}; }}
            .string {{ color: {colors['string']}; }}
            .comment {{ color: {colors['comment']}; font-style: italic; }}
            .number {{ color: {colors['number']}; }}
            .function {{ color: {colors['function']}; }}
            .class {{ color: {colors['class']}; font-weight: bold; }}
            .operator {{ color: {colors['operator']}; }}
            .line-number {{ 
                color: {colors['comment']}; 
                display: inline-block;
                width: 30px;
                text-align: right;
                margin-right: 10px;
                user-select: none;
                -webkit-user-select: none;
                border-right: 1px solid {colors['comment']};
                padding-right: 5px;
            }}
        </style>
        </head>
        <body>
        <table border="0" cellspacing="0" cellpadding="0" style="border-collapse: collapse; width: 100%;">
        """
        
        # Split code into lines for processing
        lines = code.split('\n')
        line_num = 1
        
        # Process each line
        for line in lines:
            html += "<tr><td>"
            # Add line number if enabled in settings
            if settings.get_app_setting("ui", "show_line_numbers", default=True):
                html += f"<span class='line-number'>{line_num}</span>"
            
            html += "</td><td width='100%'>"
            
            # Replace special HTML characters
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Simple highlighting of keywords
            for keyword in keywords:
                line = line.replace(f' {keyword} ', f' <span class="keyword">{keyword}</span> ')
                line = line.replace(f'{keyword}:', f'<span class="keyword">{keyword}</span>:')
                line = line.replace(f' {keyword}(', f' <span class="keyword">{keyword}</span>(')
            
            # Highlight builtins
            for builtin in builtins:
                line = line.replace(f' {builtin}(', f' <span class="builtin">{builtin}</span>(')
            
            # Add line to HTML
            html += line + "</td></tr>\n"
            line_num += 1
        
        # Close HTML
        html += """
        </table>
        </body>
        </html>
        """
        
        return html
    
    def set_execution_output(self, output: str):
        """
        Set the execution output.
        
        Args:
            output: Text output from code execution
        """
        self.execution_output.setText(output)
    
    def clear_execution_output(self):
        """Clear the execution output"""
        self.execution_output.clear()
    
    def get_code_preview(self) -> str:
        """
        Get the current code from the preview.
        
        Returns:
            The Python code as plain text, cleaned and normalized
        """
        raw_code = self.code_preview.toPlainText()
        
        # Clean and sanitize the code to prevent indentation issues
        clean_code = ""
        for line in raw_code.splitlines():
            # Only add lines with actual content
            if line.strip():
                # Ensure no indentation at the top level
                clean_code += line.lstrip() + "\n"
            else:
                clean_code += "\n"  # Preserve empty lines
        
        # Log the code for debugging
        logger.debug(f"Code from preview (clean):\n{clean_code}")
        
        return clean_code 