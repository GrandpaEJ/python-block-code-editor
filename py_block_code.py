import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QScrollArea, QLineEdit, QMenu, 
                             QAction, QToolBar, QSplitter, QTextEdit, QSizePolicy, QComboBox,
                             QDockWidget, QGroupBox, QFormLayout, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QMimeData, QPoint, QSize, pyqtSignal, QRect
from PyQt5.QtGui import QDrag, QColor, QPainter, QPen, QFont, QIcon, QBrush, QLinearGradient

# Load block definitions from JSON
BLOCK_DEFINITIONS_FILE = "block_definitions.json"

class BlockInputSlot(QFrame):
    """A slot where other blocks can be inserted as input"""
    
    def __init__(self, parent=None, name="", default_text=""):
        super().__init__(parent)
        self.name = name
        self.default_text = default_text
        self.contained_block = None
        
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(30)
        self.setMaximumHeight(40)
        self.setMinimumWidth(100)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 2, 5, 2)
        
        # Use a line edit for text input when no block is inserted
        self.text_input = QLineEdit(default_text)
        self.layout.addWidget(self.text_input)
        
        # Set styling - improved contrast and visibility
        self.setStyleSheet("""
            BlockInputSlot {
                background-color: rgba(255, 255, 255, 180);
                border: 1px dashed #666;
                border-radius: 4px;
            }
            BlockInputSlot:hover {
                border: 2px dashed #444;
                background-color: rgba(240, 240, 255, 220);
            }
            QLineEdit {
                border: 1px solid #bbb;
                border-radius: 3px;
                padding: 2px;
                background-color: #fdfdfd;
            }
        """)
        
    def dragEnterEvent(self, event):
        """Allow dragging blocks into this slot"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet("""
                BlockInputSlot {
                    background-color: rgba(220, 240, 255, 220);
                    border: 2px dashed #4080C0;
                    border-radius: 4px;
                }
            """)
            
    def dragLeaveEvent(self, event):
        """Reset styling when drag leaves"""
        self.setStyleSheet("""
            BlockInputSlot {
                background-color: rgba(255, 255, 255, 180);
                border: 1px dashed #666;
                border-radius: 4px;
            }
            BlockInputSlot:hover {
                border: 2px dashed #444;
                background-color: rgba(240, 240, 255, 220);
            }
            QLineEdit {
                border: 1px solid #bbb;
                border-radius: 3px;
                padding: 2px;
                background-color: #fdfdfd;
            }
        """)
            
    def dropEvent(self, event):
        """Handle dropping a block into this slot"""
        block_type = event.mimeData().text()
        
        # Find main window to get block definitions
        main_window = self.get_main_window()
        if not main_window:
            return
            
        # Create a new block in this slot
        if self.contained_block:
            self.contained_block.setParent(None)
            self.contained_block.deleteLater()
            
        # Create the new block
        self.contained_block = CodeBlock(block_type, self, is_nested=True)
        
        # Hide the text input and add the block
        self.text_input.hide()
        self.layout.addWidget(self.contained_block)
        
        # Reset styling
        self.setStyleSheet("""
            BlockInputSlot {
                background-color: rgba(255, 255, 255, 150);
                border: 1px dashed #888;
                border-radius: 4px;
            }
        """)
        
        event.acceptProposedAction()
        
    def get_main_window(self):
        """Get reference to the main window"""
        parent = self.parent()
        while parent:
            if isinstance(parent, CodeBlockEditor):
                return parent
            parent = parent.parent()
        return None
        
    def get_value(self):
        """Get the value of this input slot - either text or generated code from a nested block"""
        if self.contained_block:
            # Generate code from the contained block
            return self.contained_block.generate_code(include_indent=False)
        else:
            # Return the text value, handle string formatting
            value = self.text_input.text()
            
            # If this is a prompt or message, automatically add quotes if they're not there
            # and the text looks like a string (no variables or expressions)
            if (self.name in ["message", "prompt", "text"] and 
                not (value.startswith('"') and value.endswith('"')) and
                not (value.startswith("'") and value.endswith("'")) and
                not "{" in value and not "+" in value):
                return f'"{value}"'
            return value
        
    def clear(self):
        """Clear the slot"""
        if self.contained_block:
            self.contained_block.setParent(None)
            self.contained_block.deleteLater()
            self.contained_block = None
            
        self.text_input.setText(self.default_text)
        self.text_input.show()
        
    def to_json(self):
        """Serialize the slot to JSON"""
        if self.contained_block:
            return {
                "type": "block",
                "block": self.contained_block.to_json()
            }
        else:
            return {
                "type": "text",
                "value": self.text_input.text()
            }
            
    def from_json(self, data, main_window):
        """Deserialize the slot from JSON"""
        if data.get("type") == "block" and "block" in data:
            block_type = data["block"].get("type")
            if block_type:
                self.contained_block = CodeBlock(block_type, self, is_nested=True)
                self.text_input.hide()
                self.layout.addWidget(self.contained_block)
                self.contained_block.from_json(data["block"], main_window)
        else:
            self.text_input.setText(data.get("value", self.default_text))
            self.text_input.show()

class CodeBlockEditor(QMainWindow):
    """Main window for the Python Block Code editor"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Block Code Editor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application style - improved with better contrast and readability
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QToolBar {
                background-color: #2c3e50;
                border: none;
                color: white;
                spacing: 5px;
                padding: 3px;
                font-weight: bold;
            }
            QToolBar QToolButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px;
                margin: 2px;
                font-size: 14px;
            }
            QToolBar QToolButton:hover {
                background-color: #2980b9;
            }
            QToolBar QToolButton:pressed {
                background-color: #1c6ea4;
            }
            QScrollArea {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f8f8;
            }
            QGroupBox {
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333;
            }
            QLabel {
                color: #333;
            }
            QSplitter::handle {
                background-color: #ccc;
            }
            QSplitter::handle:horizontal {
                width: 4px;
            }
            QSplitter::handle:vertical {
                height: 4px;
            }
        """)
        
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Block palette panel
        self.setup_block_palette()
        
        # Workspace panel
        self.setup_workspace()
        
        # Output panel
        self.setup_output_panel()
        
        # Setup toolbar
        self.setup_toolbar()
        
        # Initialize block types
        self.initialize_block_types()
        
    def setup_block_palette(self):
        """Set up the panel containing block categories and blocks"""
        self.palette_widget = QWidget()
        self.palette_layout = QVBoxLayout(self.palette_widget)
        self.palette_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
            }
        """)
        
        # Title for palette
        palette_title = QLabel("Block Palette")
        palette_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding: 8px;
            border-bottom: 1px solid #ddd;
            margin-bottom: 8px;
        """)
        self.palette_layout.addWidget(palette_title)
        
        # Block categories
        self.categories = {
            "Basic": ["Print", "Variable", "Input", "Comment", "DirectCode"],
            "Values": ["Value", "StringValue", "NumberValue", "BooleanValue", "ListValue", "DictValue"],
            "Math": ["Add", "Subtract", "Multiply", "Divide", "Modulo", "Power"],
            "Logic": ["Compare", "And", "Or", "Not", "If", "IfElse", "While", "For"],
            "Functions": ["Define Function", "Call Function", "Return"],
            "Data": ["List Get", "List Set", "List Append", "Dict Get", "Dict Set"]
        }
        
        # Category colors
        self.category_colors = {
            "Basic": "#3498db",
            "Values": "#f39c12",
            "Math": "#e74c3c",
            "Logic": "#9b59b6",
            "Functions": "#2ecc71",
            "Data": "#1abc9c"
        }
        
        for category, blocks in self.categories.items():
            group = QGroupBox(category)
            group.setStyleSheet(f"""
                QGroupBox {{
                    border: 1px solid {self.category_colors[category]};
                    border-radius: 6px;
                    margin-top: 12px;
                    font-weight: bold;
                    color: {self.category_colors[category]};
                    background-color: rgba({self.hex_to_rgba(self.category_colors[category], 0.05)});
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }}
            """)
            group_layout = QVBoxLayout()
            group_layout.setSpacing(4)
            
            for block_type in blocks:
                block = BlockPaletteItem(block_type, self.category_colors[category])
                group_layout.addWidget(block)
            
            group.setLayout(group_layout)
            self.palette_layout.addWidget(group)
        
        # Add stretch to push blocks to the top
        self.palette_layout.addStretch(1)
        
        # Create scroll area for palette
        palette_scroll = QScrollArea()
        palette_scroll.setWidgetResizable(True)
        palette_scroll.setWidget(self.palette_widget)
        
        self.splitter.addWidget(palette_scroll)
        
    def hex_to_rgba(self, hex_color, alpha=1.0):
        """Convert hex color to rgba string"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}, {alpha}"
        
    def setup_workspace(self):
        """Set up the main workspace where blocks will be arranged"""
        self.workspace = WorkspaceWidget()
        # Add faint grid pattern to workspace
        self.workspace.setStyleSheet("""
            WorkspaceWidget {
                background-color: white;
                background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoAQMAAAC2MCouAAAABlBMVEXs7Oz////p38LwAAAAE0lEQVQI12P4DwUMo4xhxRjMAQAJMAF5dXMM2wAAAABJRU5ErkJggg==');
                background-repeat: repeat;
            }
        """)
        
        # Create a container for the workspace with a title
        workspace_container = QWidget()
        workspace_layout = QVBoxLayout(workspace_container)
        
        # Title for workspace
        workspace_title = QLabel("Workspace")
        workspace_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding: 8px;
            border-bottom: 1px solid #ddd;
            margin-bottom: 8px;
        """)
        workspace_layout.addWidget(workspace_title)
        
        # Create scroll area for workspace
        workspace_scroll = QScrollArea()
        workspace_scroll.setWidgetResizable(True)
        workspace_scroll.setWidget(self.workspace)
        workspace_layout.addWidget(workspace_scroll)
        
        self.splitter.addWidget(workspace_container)
        
    def setup_output_panel(self):
        """Set up the output panel for code preview and execution results"""
        self.output_widget = QWidget()
        self.output_layout = QVBoxLayout(self.output_widget)
        self.output_widget.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                font-size: 13px;
                line-height: 1.4;
                padding: 5px;
            }
        """)
        
        # Title for output
        output_title = QLabel("Output")
        output_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding: 8px;
            border-bottom: 1px solid #ddd;
            margin-bottom: 8px;
        """)
        self.output_layout.addWidget(output_title)
        
        # Code preview
        self.code_preview_label = QLabel("Python Code:")
        self.code_preview_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-top: 5px;")
        self.output_layout.addWidget(self.code_preview_label)
        
        self.code_preview = QTextEdit()
        self.code_preview.setReadOnly(True)
        # Add syntax highlighting
        self.code_preview.setStyleSheet("""
            QTextEdit {
                background-color: #282c34;
                color: #abb2bf;
                border: 1px solid #181a1f;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 8px;
            }
        """)
        self.output_layout.addWidget(self.code_preview)
        
        # Execution output
        self.execution_label = QLabel("Execution Output:")
        self.execution_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-top: 10px;")
        self.output_layout.addWidget(self.execution_label)
        
        self.execution_output = QTextEdit()
        self.execution_output.setReadOnly(True)
        self.execution_output.setStyleSheet("""
            QTextEdit {
                background-color: #282c34;
                color: #98c379;
                border: 1px solid #181a1f;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 8px;
            }
        """)
        self.output_layout.addWidget(self.execution_output)
        
        # Add to splitter
        self.splitter.setSizes([250, 600, 350])
        
    def setup_toolbar(self):
        """Set up the application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # Run button
        run_action = QAction("▶ Run", self)
        run_action.setStatusTip("Execute the generated Python code")
        run_action.triggered.connect(self.run_code)
        toolbar.addAction(run_action)
        
        toolbar.addSeparator()
        
        # Save button
        save_action = QAction("💾 Save", self)
        save_action.setStatusTip("Save current project")
        save_action.triggered.connect(self.save_project)
        toolbar.addAction(save_action)
        
        # Load button
        load_action = QAction("📂 Load", self)
        load_action.setStatusTip("Load a project")
        load_action.triggered.connect(self.load_project)
        toolbar.addAction(load_action)
        
        toolbar.addSeparator()
        
        # Clear workspace button
        clear_action = QAction("🗑 Clear", self)
        clear_action.setStatusTip("Clear the workspace")
        clear_action.triggered.connect(self.clear_workspace)
        toolbar.addAction(clear_action)
        
        # Add an about button
        toolbar.addSeparator()
        about_action = QAction("ℹ️ About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
        
        # Add status bar
        self.statusBar().showMessage("Ready")
        
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Python Block Code Editor", 
                         """<h2>Python Block Code Editor</h2>
                         <p>A visual programming environment for Python that allows 
                         you to create Python programs by dragging and dropping code blocks, 
                         similar to Sketchware/Kodular for Java.</p>
                         <p>Features include:</p>
                         <ul>
                         <li>Nestable blocks</li>
                         <li>Direct code insertion</li>
                         <li>Real-time code preview</li>
                         <li>JSON-based block definitions</li>
                         </ul>
                         <p><small>Version 1.0.0</small></p>""")
        
    def initialize_block_types(self):
        """Initialize the block type definitions"""
        self.block_definitions = {
            # Basic blocks
            "Print": {
                "color": QColor(100, 180, 255),
                "inputs": [{"name": "message", "type": "slot", "default": "Hello World"}],
                "code_template": "print({message})"
            },
            "Variable": {
                "color": QColor(255, 180, 100),
                "inputs": [
                    {"name": "name", "type": "text", "default": "my_var"},
                    {"name": "value", "type": "slot", "default": "0"}
                ],
                "code_template": "{name} = {value}",
                "output_enabled": True,
                "output_value": "{name}"
            },
            "Input": {
                "color": QColor(180, 255, 100),
                "inputs": [
                    {"name": "variable", "type": "text", "default": "user_input"},
                    {"name": "prompt", "type": "slot", "default": "Enter something:"}
                ],
                "code_template": "{variable} = input({prompt})"
            },
            "Comment": {
                "color": QColor(150, 150, 150),
                "inputs": [
                    {"name": "text", "type": "text", "default": "Add your comment here"}
                ],
                "code_template": "# {text}"
            },
            "DirectCode": {
                "color": QColor(150, 150, 150),
                "inputs": [
                    {"name": "code", "type": "text", "default": "# Write your Python code here"}
                ],
                "code_template": "{code}"
            },
            
            # Value blocks
            "Value": {
                "color": QColor(255, 200, 100),
                "inputs": [
                    {"name": "value", "type": "text", "default": "0"}
                ],
                "output_enabled": True,
                "output_value": "{value}"
            },
            "StringValue": {
                "color": QColor(100, 220, 255),
                "inputs": [
                    {"name": "text", "type": "text", "default": "text"}
                ],
                "output_enabled": True,
                "output_value": "\"{text}\""
            },
            "NumberValue": {
                "color": QColor(255, 220, 100),
                "inputs": [
                    {"name": "number", "type": "text", "default": "0"}
                ],
                "output_enabled": True,
                "output_value": "{number}"
            },
            "BooleanValue": {
                "color": QColor(180, 150, 255),
                "inputs": [
                    {"name": "value", "type": "choice", "options": ["True", "False"], "default": "True"}
                ],
                "output_enabled": True,
                "output_value": "{value}"
            },
            "ListValue": {
                "color": QColor(100, 200, 180),
                "inputs": [
                    {"name": "items", "type": "text", "default": "1, 2, 3"}
                ],
                "output_enabled": True,
                "output_value": "[{items}]"
            },
            "DictValue": {
                "color": QColor(180, 200, 100),
                "inputs": [
                    {"name": "items", "type": "text", "default": "'key1': 'value1', 'key2': 'value2'"}
                ],
                "output_enabled": True,
                "output_value": "{{{items}}}"
            },
            
            # Math blocks
            "Add": {
                "color": QColor(255, 100, 100),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "0"},
                    {"name": "b", "type": "slot", "default": "0"},
                    {"name": "result", "type": "text", "default": "result"}
                ],
                "code_template": "{result} = {a} + {b}",
                "output_enabled": True,
                "output_value": "({a} + {b})"
            },
            "Subtract": {
                "color": QColor(255, 120, 120),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "0"},
                    {"name": "b", "type": "slot", "default": "0"},
                    {"name": "result", "type": "text", "default": "result"}
                ],
                "code_template": "{result} = {a} - {b}",
                "output_enabled": True,
                "output_value": "({a} - {b})"
            },
            "Multiply": {
                "color": QColor(255, 140, 140),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "0"},
                    {"name": "b", "type": "slot", "default": "0"},
                    {"name": "result", "type": "text", "default": "result"}
                ],
                "code_template": "{result} = {a} * {b}",
                "output_enabled": True,
                "output_value": "({a} * {b})"
            },
            "Divide": {
                "color": QColor(255, 160, 160),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "0"},
                    {"name": "b", "type": "slot", "default": "1"},
                    {"name": "result", "type": "text", "default": "result"}
                ],
                "code_template": "{result} = {a} / {b}",
                "output_enabled": True,
                "output_value": "({a} / {b})"
            },
            "Modulo": {
                "color": QColor(255, 180, 180),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "0"},
                    {"name": "b", "type": "slot", "default": "1"},
                    {"name": "result", "type": "text", "default": "result"}
                ],
                "code_template": "{result} = {a} % {b}",
                "output_enabled": True,
                "output_value": "({a} % {b})"
            },
            "Power": {
                "color": QColor(255, 200, 200),
                "inputs": [
                    {"name": "base", "type": "slot", "default": "2"},
                    {"name": "exponent", "type": "slot", "default": "2"},
                    {"name": "result", "type": "text", "default": "result"}
                ],
                "code_template": "{result} = {base} ** {exponent}",
                "output_enabled": True,
                "output_value": "({base} ** {exponent})"
            },
            
            # Logic blocks
            "Compare": {
                "color": QColor(180, 150, 255),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "0"},
                    {"name": "operator", "type": "choice", "options": ["==", "!=", ">", "<", ">=", "<="], "default": "=="},
                    {"name": "b", "type": "slot", "default": "0"}
                ],
                "output_enabled": True,
                "output_value": "({a} {operator} {b})"
            },
            "And": {
                "color": QColor(170, 140, 230),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "True"},
                    {"name": "b", "type": "slot", "default": "True"}
                ],
                "output_enabled": True,
                "output_value": "({a} and {b})"
            },
            "Or": {
                "color": QColor(190, 160, 240),
                "inputs": [
                    {"name": "a", "type": "slot", "default": "True"},
                    {"name": "b", "type": "slot", "default": "True"}
                ],
                "output_enabled": True,
                "output_value": "({a} or {b})"
            },
            "Not": {
                "color": QColor(200, 170, 250),
                "inputs": [
                    {"name": "condition", "type": "slot", "default": "True"}
                ],
                "output_enabled": True,
                "output_value": "(not {condition})"
            },
            "If": {
                "color": QColor(200, 100, 255),
                "inputs": [{"name": "condition", "type": "slot", "default": "True"}],
                "code_template": "if {condition}:",
                "has_children": True
            },
            "IfElse": {
                "color": QColor(180, 100, 200),
                "inputs": [{"name": "condition", "type": "slot", "default": "True"}],
                "code_template": "if {condition}:",
                "else_template": "else:",
                "has_children": True,
                "has_else_children": True
            },
            "While": {
                "color": QColor(100, 255, 200),
                "inputs": [{"name": "condition", "type": "slot", "default": "True"}],
                "code_template": "while {condition}:",
                "has_children": True
            },
            "For": {
                "color": QColor(100, 200, 255),
                "inputs": [
                    {"name": "variable", "type": "text", "default": "i"},
                    {"name": "iterable", "type": "slot", "default": "range(10)"}
                ],
                "code_template": "for {variable} in {iterable}:",
                "has_children": True
            },
            
            # Function blocks
            "Define Function": {
                "color": QColor(100, 200, 150),
                "inputs": [
                    {"name": "name", "type": "text", "default": "my_function"},
                    {"name": "params", "type": "text", "default": ""}
                ],
                "code_template": "def {name}({params}):",
                "has_children": True
            },
            "Call Function": {
                "color": QColor(120, 220, 170),
                "inputs": [
                    {"name": "name", "type": "text", "default": "my_function"},
                    {"name": "args", "type": "text", "default": ""}
                ],
                "code_template": "{name}({args})",
                "output_enabled": True,
                "output_value": "{name}({args})"
            },
            "Return": {
                "color": QColor(140, 240, 190),
                "inputs": [
                    {"name": "value", "type": "slot", "default": ""}
                ],
                "code_template": "return {value}"
            },
            
            # Data structure blocks
            "List Get": {
                "color": QColor(100, 180, 200),
                "inputs": [
                    {"name": "list", "type": "slot", "default": "my_list"},
                    {"name": "index", "type": "slot", "default": "0"}
                ],
                "output_enabled": True,
                "output_value": "{list}[{index}]"
            },
            "List Set": {
                "color": QColor(120, 200, 220),
                "inputs": [
                    {"name": "list", "type": "slot", "default": "my_list"},
                    {"name": "index", "type": "slot", "default": "0"},
                    {"name": "value", "type": "slot", "default": "new_value"}
                ],
                "code_template": "{list}[{index}] = {value}"
            },
            "List Append": {
                "color": QColor(140, 220, 240),
                "inputs": [
                    {"name": "list", "type": "slot", "default": "my_list"},
                    {"name": "value", "type": "slot", "default": "new_item"}
                ],
                "code_template": "{list}.append({value})"
            },
            "Dict Get": {
                "color": QColor(180, 200, 100),
                "inputs": [
                    {"name": "dict", "type": "slot", "default": "my_dict"},
                    {"name": "key", "type": "slot", "default": "'key'"}
                ],
                "output_enabled": True,
                "output_value": "{dict}[{key}]"
            },
            "Dict Set": {
                "color": QColor(200, 220, 120),
                "inputs": [
                    {"name": "dict", "type": "slot", "default": "my_dict"},
                    {"name": "key", "type": "slot", "default": "'key'"},
                    {"name": "value", "type": "slot", "default": "new_value"}
                ],
                "code_template": "{dict}[{key}] = {value}"
            }
        }
        
        # Try to load block definitions from JSON if available
        try:
            if os.path.exists(BLOCK_DEFINITIONS_FILE):
                with open(BLOCK_DEFINITIONS_FILE, 'r') as f:
                    json_defs = json.load(f)
                    
                # Process JSON definitions
                for block_type, def_data in json_defs.items():
                    if "color" in def_data:
                        color_data = def_data["color"]
                        if isinstance(color_data, list) and len(color_data) >= 3:
                            def_data["color"] = QColor(*color_data)
                            
                    self.block_definitions[block_type] = def_data
        except Exception as e:
            print(f"Error loading block definitions: {e}")
        
    def generate_code(self):
        """Generate Python code from blocks in the workspace"""
        code = self.workspace.generate_code()
        
        # Apply syntax highlighting through CSS (simplified method)
        # In a real implementation, you would use a proper Python syntax highlighter
        highlighted_code = ""
        for line in code.split('\n'):
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.strip().startswith('def ') or line.strip().startswith('class '):
                highlighted_code += f'<span style="color: #61afef;">{line}</span><br>'
            elif line.strip().startswith('if ') or line.strip().startswith('else') or line.strip().startswith('for ') or line.strip().startswith('while '):
                highlighted_code += f'<span style="color: #c678dd;">{line}</span><br>'
            elif line.strip().startswith('return '):
                highlighted_code += f'<span style="color: #e06c75;">{line}</span><br>'
            elif line.strip().startswith('#'):
                highlighted_code += f'<span style="color: #98c379;">{line}</span><br>'
            elif "=" in line and not "==" in line:
                highlighted_code += f'<span style="color: #d19a66;">{line}</span><br>'
            else:
                highlighted_code += f'{line}<br>'
                
        self.code_preview.setHtml(highlighted_code)
        return code
        
    def run_code(self):
        """Run the generated Python code"""
        code = self.generate_code()
        self.execution_output.clear()
        
        try:
            # Redirect stdout to capture print output
            import io
            import sys
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            with redirect_stdout(output):
                exec(code)
                
            self.execution_output.setText(output.getvalue())
        except Exception as e:
            self.execution_output.setText(f"Error: {str(e)}")
            
    def save_project(self):
        """Save the current project to a file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Python Block Code Project (*.pbc);;All Files (*)")
        
        if not filename:
            return
        
        # Add extension if it doesn't have one
        if not filename.endswith('.pbc'):
            filename += '.pbc'
        
        try:
            # Create project data
            project_data = self.workspace.to_json()
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(project_data, f, indent=2)
                
            QMessageBox.information(self, "Save Successful", f"Project saved successfully to {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An error occurred while saving: {str(e)}")
        
    def load_project(self):
        """Load a project from a file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Python Block Code Project (*.pbc);;All Files (*)")
        
        if not filename:
            return
        
        try:
            # Load project data
            with open(filename, 'r') as f:
                project_data = json.load(f)
                
            # Apply to workspace
            self.workspace.from_json(project_data, self)
            
            # Update code preview
            self.generate_code()
            
            QMessageBox.information(self, "Load Successful", f"Project loaded successfully from {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"An error occurred while loading: {str(e)}")
        
    def clear_workspace(self):
        """Clear all blocks from the workspace"""
        self.workspace.clear()
        

class BlockPaletteItem(QFrame):
    """Represents a block in the palette that can be dragged to the workspace"""
    
    def __init__(self, block_type, color="#3498db"):
        super().__init__()
        self.block_type = block_type
        self.color = color
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)
        self.setMinimumHeight(40)
        self.setMaximumHeight(40)
        
        # Set rounded corners and gradient background - improved visuals
        self.setStyleSheet(f"""
            BlockPaletteItem {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {color}, stop:1 {self.darker_color(color)});
                color: white;
                border-radius: 6px;
                border: 1px solid {self.darker_color(color)};
            }}
            BlockPaletteItem:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {self.lighter_color(color)}, stop:1 {color});
                border: 1px solid {self.darker_color(self.darker_color(color))};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        
        # Add an icon or indicator
        icon_label = QLabel("◆")
        icon_label.setMaximumWidth(20)
        icon_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: transparent; border: none;")
        layout.addWidget(icon_label)
        
        # Add the main text label
        label = QLabel(block_type)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setStyleSheet("color: white; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(label)
        
        # Make cursor indicate draggability
        self.setCursor(Qt.OpenHandCursor)
        
    def darker_color(self, color):
        """Return a darker version of the color"""
        qcolor = QColor(color)
        h, s, v, a = qcolor.getHsv()
        qcolor.setHsv(h, s, max(0, v - 30), a)
        return qcolor.name()
        
    def lighter_color(self, color):
        """Return a lighter version of the color"""
        qcolor = QColor(color)
        h, s, v, a = qcolor.getHsv()
        qcolor.setHsv(h, min(255, s - 10 if s > 10 else s), min(255, v + 30), a)
        return qcolor.name()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.ClosedHandCursor)  # Change cursor on click

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.OpenHandCursor)  # Restore cursor
            
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.block_type)
        drag.setMimeData(mime_data)
        
        # Create a nice looking drag pixmap with shadow effect
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Show feedback to user
        self.setStyleSheet(f"""
            BlockPaletteItem {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {self.color}, stop:1 {self.darker_color(self.color)});
                color: white;
                border-radius: 6px;
                border: 1px solid {self.darker_color(self.color)};
                opacity: 0.7;
            }}
        """)
        
        result = drag.exec_(Qt.CopyAction)
        
        # Restore normal appearance
        self.setStyleSheet(f"""
            BlockPaletteItem {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {self.color}, stop:1 {self.darker_color(self.color)});
                color: white;
                border-radius: 6px;
                border: 1px solid {self.darker_color(self.color)};
            }}
            BlockPaletteItem:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {self.lighter_color(self.color)}, stop:1 {self.color});
                border: 1px solid {self.darker_color(self.darker_color(self.color))};
            }}
        """)
        self.setCursor(Qt.OpenHandCursor)  # Restore cursor


class CodeBlock(QFrame):
    """Represents a code block in the workspace"""
    
    def __init__(self, block_type, parent=None, is_nested=False):
        super().__init__(parent)
        self.block_type = block_type
        self.input_widgets = {}
        self.input_slots = {}
        self.child_blocks = []
        self.else_blocks = []
        self.is_nested = is_nested  # Whether this block is nested in an input slot
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)
        
        if is_nested:
            self.setMinimumHeight(30)
            self.setMaximumHeight(40)
        else:
            self.setMinimumHeight(50)
            
        self.setMinimumWidth(200)
        
        # Get block definition from parent window
        main_window = self.get_main_window()
        if main_window and block_type in main_window.block_definitions:
            self.definition = main_window.block_definitions[block_type]
            bg_color = self.definition.get("color", QColor(200, 200, 200))
            
            # Create a gradient effect for the block - improved with better contrast
            gradient_color = self.lighter_color(bg_color.name())
            dark_border = self.darker_color(bg_color.name())
            
            # Set base style
            base_style = f"""
                CodeBlock {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                            stop:0 {gradient_color}, stop:1 {bg_color.name()});
                    border-radius: 8px;
                    border: 2px solid {dark_border};
                }}
                QLabel {{
                    color: black;
                    background: transparent;
                    border: none;
                }}
                QLineEdit {{
                    border: 1px solid #bbb;
                    border-radius: 4px;
                    padding: 3px;
                    background: white;
                    selection-background-color: {bg_color.name()};
                }}
                QLineEdit:focus {{
                    border: 1px solid {bg_color.name()};
                    background: #fafafa;
                }}
                QPushButton {{
                    background: #e74c3c;
                    color: white;
                    border-radius: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: #c0392b;
                }}
            """
            
            # Add shadow or hover effects for non-nested blocks
            if not is_nested:
                base_style += f"""
                    CodeBlock:hover {{
                        border: 2px solid {self.darker_color(dark_border)};
                    }}
                """
                
            self.setStyleSheet(base_style)
        else:
            self.definition = {
                "inputs": [],
                "code_template": f"# {block_type}",
                "has_children": False
            }
            self.setStyleSheet("""
                CodeBlock {
                    background: #e0e0e0;
                    border-radius: 8px;
                    border: 2px solid #aaaaaa;
                }
                CodeBlock:hover {
                    border: 2px solid #888888;
                }
            """)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(10, 5, 10, 5)
        
        # Header with block type
        header_layout = QHBoxLayout()
        
        # Add a small indicator icon for the block type
        if not is_nested:
            icon_label = QLabel("◆")
            icon_label.setMaximumWidth(20)
            icon_label.setStyleSheet("color: rgba(0, 0, 0, 0.4); font-size: 12px;")
            header_layout.addWidget(icon_label)
        
        # Add the block title
        header_label = QLabel(block_type)
        if is_nested:
            header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        else:
            header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        
        # Add spacer
        header_layout.addStretch(1)
        
        # Don't add delete button for nested blocks
        if not is_nested:
            # Add delete button
            delete_button = QPushButton("×")
            delete_button.setMaximumWidth(20)
            delete_button.setMaximumHeight(20)
            delete_button.setToolTip("Delete this block")
            delete_button.clicked.connect(self.remove_block)
            header_layout.addWidget(delete_button)
        
        self.layout.addLayout(header_layout)
        
        # Add input fields based on block definition
        self.setup_inputs()
        
        # For nested blocks, we reduce the size and simplify the UI
        if is_nested:
            self.setFrameShape(QFrame.NoFrame)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(2)
            
        # If block can have children, add container for them
        if self.definition.get("has_children", False) and not is_nested:
            self.setup_child_container()
            
            # Also setup else container if needed
            if self.definition.get("has_else_children", False):
                self.setup_else_container()
        
        # Make block draggable unless it's nested
        if not is_nested:
            self.setMouseTracking(True)
            self.dragging = False
            self.drag_start_position = None
            self.setCursor(Qt.OpenHandCursor)  # Set cursor to indicate draggability
            
    def setup_child_container(self):
        """Setup container for child blocks"""
        self.child_container = QWidget(self)
        self.child_container.setStyleSheet("""
            background: rgba(255, 255, 255, 120);
            border-radius: 6px;
            border: 1px dashed rgba(0, 0, 0, 0.2);
        """)
        self.child_layout = QVBoxLayout(self.child_container)
        self.child_layout.setContentsMargins(20, 5, 5, 5)
        self.layout.addWidget(self.child_container)
        
        # Add a placeholder for dropping blocks
        self.drop_placeholder = QLabel("Drop blocks here")
        self.drop_placeholder.setAlignment(Qt.AlignCenter)
        self.drop_placeholder.setStyleSheet("""
            background-color: rgba(200, 200, 200, 100);
            border: 1px dashed gray;
            border-radius: 4px;
            color: #555;
            padding: 10px;
            margin: 5px;
        """)
        self.drop_placeholder.setMinimumHeight(40)
        self.child_layout.addWidget(self.drop_placeholder)
        
        # Make the child container accept drops
        self.child_container.setAcceptDrops(True)
        self.child_container.dragEnterEvent = self.child_drag_enter
        self.child_container.dropEvent = self.child_drop_event
        
    def child_drag_enter(self, event):
        """Handle drag enter on child container"""
        if event.mimeData().hasText():
            self.child_container.setStyleSheet("""
                background: rgba(220, 240, 255, 180);
                border-radius: 6px;
                border: 1px dashed rgba(0, 0, 150, 0.3);
            """)
            event.acceptProposedAction()
            
    def child_drop_event(self, event):
        """Handle drop on child container"""
        block_type = event.mimeData().text()
        
        # Create a new block
        new_block = CodeBlock(block_type, self.child_container)
        self.child_layout.insertWidget(self.child_layout.count() - 1, new_block)  # Insert before placeholder
        self.child_blocks.append(new_block)
        
        # Reset styling
        self.child_container.setStyleSheet("""
            background: rgba(255, 255, 255, 120);
            border-radius: 6px;
            border: 1px dashed rgba(0, 0, 0, 0.2);
        """)
        
        event.acceptProposedAction()
        
    def setup_else_container(self):
        """Setup container for else blocks"""
        # Add an 'else' label
        else_label = QLabel("else:")
        else_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(else_label)
        
        self.else_container = QWidget(self)
        self.else_container.setStyleSheet("""
            background: rgba(255, 255, 255, 120);
            border-radius: 6px;
            border: 1px dashed rgba(0, 0, 0, 0.2);
        """)
        self.else_layout = QVBoxLayout(self.else_container)
        self.else_layout.setContentsMargins(20, 5, 5, 5)
        self.layout.addWidget(self.else_container)
        
        # Add a placeholder for dropping blocks
        self.else_drop_placeholder = QLabel("Drop 'else' blocks here")
        self.else_drop_placeholder.setAlignment(Qt.AlignCenter)
        self.else_drop_placeholder.setStyleSheet("""
            background-color: rgba(200, 200, 200, 100);
            border: 1px dashed gray;
            border-radius: 4px;
            color: #555;
            padding: 10px;
            margin: 5px;
        """)
        self.else_drop_placeholder.setMinimumHeight(40)
        self.else_layout.addWidget(self.else_drop_placeholder)
        
        # Make the else container accept drops
        self.else_container.setAcceptDrops(True)
        self.else_container.dragEnterEvent = self.else_drag_enter
        self.else_container.dropEvent = self.else_drop_event
        
    def else_drag_enter(self, event):
        """Handle drag enter on else container"""
        if event.mimeData().hasText():
            self.else_container.setStyleSheet("""
                background: rgba(220, 240, 255, 180);
                border-radius: 6px;
                border: 1px dashed rgba(0, 0, 150, 0.3);
            """)
            event.acceptProposedAction()
            
    def else_drop_event(self, event):
        """Handle drop on else container"""
        block_type = event.mimeData().text()
        
        # Create a new block
        new_block = CodeBlock(block_type, self.else_container)
        self.else_layout.insertWidget(self.else_layout.count() - 1, new_block)  # Insert before placeholder
        self.else_blocks.append(new_block)
        
        # Reset styling
        self.else_container.setStyleSheet("""
            background: rgba(255, 255, 255, 120);
            border-radius: 6px;
            border: 1px dashed rgba(0, 0, 0, 0.2);
        """)
        
        event.acceptProposedAction()
    
    def lighter_color(self, color):
        """Return a lighter version of the color"""
        qcolor = QColor(color)
        h, s, v, a = qcolor.getHsv()
        qcolor.setHsv(h, max(0, s - 20), min(255, v + 40), a)
        return qcolor.name()
        
    def darker_color(self, color):
        """Return a darker version of the color"""
        qcolor = QColor(color)
        h, s, v, a = qcolor.getHsv()
        qcolor.setHsv(h, min(255, s + 20), max(0, v - 40), a)
        return qcolor.name()
    
    def setup_inputs(self):
        """Set up input fields based on block definition"""
        if "inputs" not in self.definition:
            return
            
        inputs_layout = QFormLayout()
        inputs_layout.setContentsMargins(5, 0, 5, 0)
        inputs_layout.setVerticalSpacing(5)
        inputs_layout.setHorizontalSpacing(10)
        
        for input_def in self.definition["inputs"]:
            name = input_def["name"]
            input_type = input_def.get("type", "text")
            default = input_def.get("default", "")
            
            if input_type == "text":
                input_widget = QLineEdit(default)
                # Add placeholder text
                input_widget.setPlaceholderText(f"Enter {name}...")
                self.input_widgets[name] = input_widget
                inputs_layout.addRow(f"{name}:", input_widget)
            elif input_type == "choice":
                input_widget = QComboBox()
                for option in input_def.get("options", []):
                    input_widget.addItem(option)
                if default:
                    input_widget.setCurrentText(default)
                self.input_widgets[name] = input_widget
                inputs_layout.addRow(f"{name}:", input_widget)
            elif input_type == "slot":
                # Create a slot that can accept other blocks
                input_slot = BlockInputSlot(self, name, default)
                self.input_slots[name] = input_slot
                inputs_layout.addRow(f"{name}:", input_slot)
            
        self.layout.addLayout(inputs_layout)
        
    def get_main_window(self):
        """Get reference to the main window"""
        parent = self.parent()
        while parent:
            if isinstance(parent, CodeBlockEditor):
                return parent
            parent = parent.parent()
        return None
        
    def remove_block(self):
        """Remove this block from the workspace"""
        # Show confirmation dialog
        reply = QMessageBox.question(self, "Remove Block", 
                                    f"Are you sure you want to remove this '{self.block_type}' block?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return
            
        # Find if this block is in a workspace
        workspace = None
        parent = self.parent()
        while parent:
            if isinstance(parent, WorkspaceWidget):
                workspace = parent
                break
            parent = parent.parent()
            
        if workspace:
            workspace.blocks.remove(self)
            
        self.setParent(None)
        self.deleteLater()
        
    def generate_code(self, indent_level=0, include_indent=True):
        """Generate Python code for this block and its children"""
        indent = "    " * indent_level if include_indent else ""
        
        # Replace template variables with values from input widgets and slots
        code_template = self.definition.get("code_template", f"# {self.block_type}")
        code = code_template
        
        # Process text input widgets
        for name, widget in self.input_widgets.items():
            if isinstance(widget, QLineEdit):
                value = widget.text()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            else:
                value = str(widget)
                
            code = code.replace(f"{{{name}}}", value)
            
        # Process input slots
        for name, slot in self.input_slots.items():
            value = slot.get_value()
            code = code.replace(f"{{{name}}}", value)
        
        # For nested blocks that can output a value, just return the output value
        if self.is_nested and self.definition.get("output_enabled", False):
            output_value = self.definition.get("output_value", "")
            
            # Substitute any remaining variables in the output value
            for name, widget in self.input_widgets.items():
                if isinstance(widget, QLineEdit):
                    value = widget.text()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                else:
                    value = str(widget)
                    
                output_value = output_value.replace(f"{{{name}}}", value)
                
            # Also process slots
            for name, slot in self.input_slots.items():
                value = slot.get_value()
                output_value = output_value.replace(f"{{{name}}}", value)
                
            return output_value
            
        # For regular blocks, add the code with indentation
        result = indent + code + "\n"
        
        # Add code for child blocks if applicable
        if self.definition.get("has_children", False) and not self.is_nested:
            for child in self.child_blocks:
                result += child.generate_code(indent_level + 1)
                
            # Add else section if applicable
            if self.definition.get("has_else_children", False) and self.definition.get("else_template"):
                result += indent + self.definition.get("else_template") + "\n"
                
                for else_child in self.else_blocks:
                    result += else_child.generate_code(indent_level + 1)
                
        return result
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_nested:
            self.drag_start_position = event.pos()
            self.dragging = True
            self.setCursor(Qt.ClosedHandCursor)  # Change cursor on click
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_nested:
            self.dragging = False
            self.setCursor(Qt.OpenHandCursor)  # Restore cursor
            
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not self.dragging or self.is_nested:
            return
            
        # Calculate distance moved
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # For non-nested blocks, create a drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.block_type)
        drag.setMimeData(mime_data)
        
        # Create a pixmap of the block
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Find if this block is in a workspace
        workspace = None
        parent = self.parent()
        while parent:
            if isinstance(parent, WorkspaceWidget):
                workspace = parent
                break
            parent = parent.parent()
            
        if workspace:
            # Remove this block from the workspace during drag
            workspace.blocks.remove(self)
            self.setParent(None)
            
        # Execute the drag
        result = drag.exec_(Qt.MoveAction)
        
        # If drag was cancelled, add block back to workspace
        if result == Qt.IgnoreAction and workspace:
            self.setParent(workspace)
            workspace.layout.addWidget(self)
            workspace.blocks.append(self)
            self.setCursor(Qt.OpenHandCursor)  # Restore cursor


class WorkspaceWidget(QWidget):
    """Workspace where blocks are arranged"""
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        
        # Use a layout for the workspace
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Add some instruction text
        instructions = QLabel("Drag blocks from the palette and drop them here")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("""
            color: #777;
            font-style: italic;
            font-size: 14px;
            padding: 20px;
            background-color: rgba(240, 240, 240, 150);
            border: 1px dashed #aaa;
            border-radius: 8px;
        """)
        self.layout.addWidget(instructions)
        
        self.blocks = []
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            # Visual feedback
            self.setStyleSheet("""
                WorkspaceWidget {
                    background-color: white;
                    background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoAQMAAAC2MCouAAAABlBMVEXs7Oz////p38LwAAAAE0lEQVQI12P4DwUMo4xhxRjMAQAJMAF5dXMM2wAAAABJRU5ErkJggg==');
                    background-repeat: repeat;
                    border: 2px dashed #3498db;
                }
            """)
            event.acceptProposedAction()
            
    def dragLeaveEvent(self, event):
        # Reset styling
        self.setStyleSheet("""
            WorkspaceWidget {
                background-color: white;
                background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoAQMAAAC2MCouAAAABlBMVEXs7Oz////p38LwAAAAE0lEQVQI12P4DwUMo4xhxRjMAQAJMAF5dXMM2wAAAABJRU5ErkJggg==');
                background-repeat: repeat;
            }
        """)
        
    def dropEvent(self, event):
        block_type = event.mimeData().text()
        
        # Create a new block
        block = CodeBlock(block_type, self)
        self.layout.addWidget(block)
        self.blocks.append(block)
        
        # Reset styling
        self.setStyleSheet("""
            WorkspaceWidget {
                background-color: white;
                background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoAQMAAAC2MCouAAAABlBMVEXs7Oz////p38LwAAAAE0lEQVQI12P4DwUMo4xhxRjMAQAJMAF5dXMM2wAAAABJRU5ErkJggg==');
                background-repeat: repeat;
            }
        """)
        
        event.acceptProposedAction()
        
    def clear(self):
        """Remove all blocks from the workspace"""
        # Ask for confirmation
        if self.blocks:
            reply = QMessageBox.question(self, "Clear Workspace", 
                                     "Are you sure you want to clear the workspace? All blocks will be deleted.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                                     
            if reply == QMessageBox.No:
                return
                
        for block in self.blocks[:]:
            block.setParent(None)
            block.deleteLater()
        self.blocks.clear()
        
    def generate_code(self):
        """Generate Python code from all blocks in the workspace"""
        code = "# Generated Python Code\n\n"
        
        for block in self.blocks:
            code += block.generate_code()
            
        return code
        
    def to_json(self):
        """Serialize workspace to JSON"""
        data = {
            "blocks": []
        }
        
        for block in self.blocks:
            data["blocks"].append(block.to_json())
            
        return data
        
    def from_json(self, data, main_window):
        """Deserialize workspace from JSON"""
        self.clear()
        
        for block_data in data.get("blocks", []):
            block_type = block_data.get("type", "")
            if not block_type:
                continue
                
            block = CodeBlock(block_type, self)
            self.layout.addWidget(block)
            self.blocks.append(block)
            block.from_json(block_data, main_window)


def main():
    app = QApplication(sys.argv)
    window = CodeBlockEditor()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 