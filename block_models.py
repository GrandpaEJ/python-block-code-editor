from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLineEdit, QComboBox, QFormLayout,
                           QVBoxLayout, QLabel, QPushButton, QMessageBox, QWidget, QSizePolicy, QApplication,
                           QMenu, QAction)
from PyQt5.QtCore import Qt, QMimeData, QPoint, pyqtSignal, QRect, QRectF, QSize
from PyQt5.QtGui import QDrag, QColor, QPainter, QPen, QBrush, QLinearGradient, QPainterPath, QFont

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

from settings_loader import settings
from utils import DotDict, is_variable_reference, apply_safe_quote_rules, safely_format_template, format_error_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('block_models')

class BlockInputSlot(QFrame):
    """
    An input slot for a code block that can accept other blocks for nesting.
    """
    valueChanged = pyqtSignal(str, str)  # input_name, new_value
    contentChanged = pyqtSignal()
    blockDropped = pyqtSignal(object, object, str)  # slot, block_data, drop_type
    
    def __init__(self, parent=None, input_name: str = "", placeholder: str = "Drop block here",
                 parent_block_type: str = "", default_value: str = ""):
        super().__init__(parent)
        self.parent_block_type = parent_block_type
        self.input_name = input_name
        self.placeholder = placeholder
        self.default_value = default_value
        self.nested_block = None  # Holds reference to nested block
        self.setAcceptDrops(True)
        
        # Setup UI
        self.init_ui()
        
        # Set value
        if default_value:
            self.set_value(default_value)
        
    def init_ui(self):
        """Initialize UI components"""
        self.setMinimumSize(120, 30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.layout.setSpacing(0)
        
        # Label for the empty state
        self.placeholder_label = QLabel(self.placeholder)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("background-color: transparent; color: rgba(0, 0, 0, 120); font-style: italic;")
        self.placeholder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.placeholder_label.setWordWrap(True)  # Allow placeholder text to wrap
        self.placeholder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.placeholder_label.setWordWrap(True)  # Allow placeholder text to wrap
        self.layout.addWidget(self.placeholder_label)
        
        # Style
        self.update_style()
    
    def update_style(self):
        """Update the style based on the current state"""
        theme = settings.get_current_theme()
        border_color = theme.get("border_color", "#dddddd")
        background_color = theme.get("panel_color", "#ffffff")
        accent_color = theme.get("accent_color", "#3498db")
        
        self.setStyleSheet(f"""
            BlockInputSlot {{
                background-color: rgba(255, 255, 255, 140);
                border: 2px dashed {border_color};
                border-radius: 4px;
                min-height: 30px;
                padding: 2px;
            }}
            BlockInputSlot:hover {{
                background-color: rgba(255, 255, 255, 180);
                border: 2px dashed {accent_color};
            }}
        """)
    
    def sizeHint(self) -> QSize:
        """Return preferred size that adapts to content"""
        width = self.parent().width() - 30 if self.parent() else 150  # Parent width minus margin
        height = 36  # Default minimum height
        
        if self.nested_block:
            # Adjust size based on nested block
            block_width = self.nested_block.sizeHint().width() + 10
            block_height = self.nested_block.sizeHint().height() + 8
            
            width = max(width, block_width)
            height = max(height, block_height)
            
        return QSize(width, height)
    
    def minimumSizeHint(self) -> QSize:
        """Return minimum size needed"""
        width = 150  # Minimum width
        height = 36  # Minimum height
        
        if self.nested_block:
            # Ensure minimum size can accommodate nested block
            block_width = self.nested_block.minimumSizeHint().width() + 10
            block_height = self.nested_block.minimumSizeHint().height() + 8
            
            width = max(width, block_width)
            height = max(height, block_height)
            
        return QSize(width, height)
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.nested_block:
            # Update layout when resized to ensure nested block is positioned correctly
            self.layout.invalidate()
            self.layout.activate()
            
            # Make sure nested block gets proper size
            self.nested_block.updateGeometry()
    
    def get_value(self) -> str:
        """Get the current value of this input slot"""
        # If there's a nested block, use its output
        if hasattr(self, 'nested_block') and self.nested_block:
            try:
                # Get the output value from the nested block
                if hasattr(self.nested_block, 'get_output_value'):
                    return self.nested_block.get_output_value()
                # If no specific output method, use the generated code
                return self.nested_block.generate_code(indent_level=0).strip()
            except Exception as e:
                logger.error(f"Error getting value from nested block: {e}")
                return f"Error: {str(e)}"
        # Otherwise return the text value
        return self.default_value
    
    def set_value(self, value: str) -> None:
        """Set the text value for this input slot"""
        self.default_value = value
        # Update the display if no nested block
        if not hasattr(self, 'nested_block') or not self.nested_block:
            if hasattr(self, 'text_edit'):
                self.text_edit.setText(value)
            elif hasattr(self, 'line_edit'):
                self.line_edit.setText(value)
        # Emit the value changed signal
        self.valueChanged.emit(self.input_name, value)
    
    def add_block(self, block) -> None:
        """
        Add a block to this slot.
        
        Args:
            block: The block to add
        """
        # Check if the block is compatible
        if not self.can_accept_block(block):
            logger.warning(f"Cannot add incompatible block to slot: {block.block_type}")
            return
            
        # If we already have a block, remove it first
        if hasattr(self, 'nested_block') and self.nested_block:
            self.remove_block()
            
        # Set as the nested block
        self.nested_block = block
        
        # Update block's parent
        block.set_parent_slot(self)
        
        # Hide text input and show the block
        if hasattr(self, 'text_edit'):
            self.text_edit.setVisible(False)
        elif hasattr(self, 'line_edit'):
            self.line_edit.setVisible(False)
            
        # Add to layout
        if hasattr(self, 'layout'):
            self.layout.addWidget(block)
            
        # Resize to fit the block
        self.updateGeometry()
        self.adjustSize()
        
        # Notify that content has changed
        self.contentChanged.emit()
        
        # Update parent block's value with new nested block's output
        if hasattr(self, 'parent_block') and self.parent_block:
            self.valueChanged.emit(self.input_name, self.get_value())
    
    def remove_block(self) -> Optional['CodeBlock']:
        """Remove the nested block from this slot"""
        if self.nested_block:
            block = self.nested_block
            self.layout.removeWidget(block)
            block.set_parent_slot(None)
            self.nested_block = None
            self.placeholder_label.setVisible(True)
            
            # Update layout constraints
            self.updateGeometry()
            
            # Update the parent
            self.valueChanged.emit(self.input_name, self.default_value)
            self.contentChanged.emit()
            
            # Make sure the parent layout updates
            self.parent().updateGeometry()
            
            return block
        return None
    
    def can_accept_block(self, block) -> bool:
        """Check if this slot can accept the given block"""
        if block.block_type == self.parent_block_type:
            # Prevent self-nesting
            return False
        
        # Check with the settings manager
        return settings.is_nesting_allowed(self.parent_block_type, self.input_name, block.block_type)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events for block drop"""
        if event.mimeData().hasFormat("application/x-codeblockeditor-block"):
            # Get the block type from mime data
            mime_data = event.mimeData().data("application/x-codeblockeditor-block").data()
            block_data = json.loads(mime_data.decode('utf-8'))
            
            # Check if we can accept this type of block
            if settings.is_nesting_allowed(self.parent_block_type, self.input_name, block_data.get("block_type", "")):
                # Highlight the slot with a thicker border
                theme = settings.get_current_theme()
                accent_color = theme.get("accent_color", "#3498db")
                self.setStyleSheet(f"""
                    BlockInputSlot {{
                        background-color: rgba(52, 152, 219, 0.15);
                        border: 3px dashed {accent_color};
                        border-radius: 4px;
                    }}
                """)
                event.acceptProposedAction()
                return
        
        # Reject the drag if not acceptable
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events"""
        # Restore the original style
        self.update_style()
        event.accept()
    
    def dropEvent(self, event):
        """Handle drop events to add blocks"""
        if event.mimeData().hasFormat("application/x-codeblockeditor-block"):
            # Get the block data from mime data
            mime_data = event.mimeData().data("application/x-codeblockeditor-block").data()
            block_data = json.loads(mime_data.decode('utf-8'))
            
            # Emit a signal for the parent/workspace to handle the actual block creation/movement
            # This avoids circular imports and lets the workspace handle block management
            if block_data.get("new_block", False):
                # This is a new block from the palette
                self.blockDropped.emit(self, block_data, "new")
            else:
                # This is an existing block being moved
                self.blockDropped.emit(self, block_data, "existing")
            
            # Reset style
            self.update_style()
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def to_json(self) -> Dict[str, Any]:
        """Serialize to JSON"""
        data = {
            "input_name": self.input_name,
            "default_value": self.default_value
        }
        
        if self.nested_block:
            data["nested_block"] = self.nested_block.to_json()
        
        return data
    
    @classmethod
    def from_json(cls, data: Dict[str, Any], parent=None, parent_block_type: str = ""):
        """Deserialize from JSON"""
        slot = cls(
            parent=parent,
            input_name=data.get("input_name", ""),
            default_value=data.get("default_value", ""),
            parent_block_type=parent_block_type
        )
        
        # If there's a nested block, add it
        # Note: This would actually be handled by the workspace when loading
        
        return slot


class CodeBlock(QFrame):
    """
    Visual block representing a Python code construct.
    Supports nesting, drag and drop, and code generation.
    """
    moved = pyqtSignal(QPoint)
    deleted = pyqtSignal(object)
    inputChanged = pyqtSignal()
    selected = pyqtSignal(object)
    slotDropReceived = pyqtSignal(object, object, str)  # Forward slot drop to workspace
    
    def __init__(self, parent=None, block_type: str = "", block_data: Dict[str, Any] = None):
        super().__init__(parent)
        self.block_type = block_type
        self.parent_slot = None
        self.inputs = {}  # Dict of input name -> input widget
        self.input_values = {}  # Dict of input name -> value
        self.child_blocks = []  # List of child blocks for blocks with children (if/while/etc)
        self.else_blocks = []  # For blocks with else clause
        self.is_selected = False
        self.drag_start_position = None
        self.can_be_freely_positioned = True  # Allow free positioning by default
        
        # Load block definition from settings
        self.block_definition = block_data or settings.get_block_definition(block_type) or {}
        
        # Set properties from definition
        self.output_enabled = self.block_definition.get("output_enabled", False)
        self.output_value = self.block_definition.get("output_value", "")
        self.has_children = self.block_definition.get("has_children", False)
        self.has_else = self.block_definition.get("has_else_children", False)
        self.code_template = self.block_definition.get("code_template", "")
        self.can_import_blocks = self.block_definition.get("can_import_blocks", False)
        self.can_be_nested = self.block_definition.get("can_be_nested", True)
        self.direct_code_enabled = self.block_definition.get("direct_code_enabled", False)
        
        # Get color from block definition
        color_def = self.block_definition.get("color", [100, 100, 100])
        if isinstance(color_def, list) and len(color_def) >= 3:
            self.block_color = QColor(*color_def)
        else:
            self.block_color = QColor(100, 100, 100)
        
        # Enable autosizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(180)
        self.setMaximumWidth(450)  # Increase maximum width for better content display
        
        # Setup UI
        self.init_ui()
        self.setup_inputs()
        
        # Update size based on content
        self.updateGeometry()
        self.adjustSize()  # Explicitly adjust size to fit content
    
    def init_ui(self):
        """Initialize the block UI"""
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(6)
        
        # Header section - using flexible layout
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)
        
        # Block title
        self.title_label = QLabel(self.block_type)
        self.title_label.setStyleSheet("""
            font-weight: bold; 
            color: white; 
            font-size: 12pt;
            padding: 2px;
        """)
        self.title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.title_label.setWordWrap(True)  # Allow title to wrap if too long
        self.header_layout.addWidget(self.title_label)
        
        # Add move up/down buttons if this is a child block
        self.up_button = QPushButton("▲")
        self.up_button.setFixedSize(24, 24)
        self.up_button.setStyleSheet("background-color: rgba(255, 255, 255, 150); border-radius: 12px;")
        self.up_button.clicked.connect(self.move_up)
        self.up_button.setToolTip("Move block up")
        self.up_button.setVisible(False)  # Only show for child blocks
        self.header_layout.addWidget(self.up_button)
        
        self.down_button = QPushButton("▼")
        self.down_button.setFixedSize(24, 24)
        self.down_button.setStyleSheet("background-color: rgba(255, 255, 255, 150); border-radius: 12px;")
        self.down_button.clicked.connect(self.move_down)
        self.down_button.setToolTip("Move block down")
        self.down_button.setVisible(False)  # Only show for child blocks
        self.header_layout.addWidget(self.down_button)
        
        # Add collapse/expand button for blocks with children
        if self.has_children or self.has_else:
            self.collapse_button = QPushButton("−")
            self.collapse_button.setFixedSize(24, 24)
            self.collapse_button.setStyleSheet("background-color: rgba(255, 255, 255, 150); border-radius: 12px;")
            self.collapse_button.clicked.connect(self.toggle_collapse)
            self.collapse_button.setToolTip("Collapse/Expand")
            self.header_layout.addWidget(self.collapse_button)
            self.is_collapsed = False
        
        # Add stretch to push content to the left
        self.header_layout.addStretch(1)
        
        self.layout.addLayout(self.header_layout)
        
        # Direct code entry option if enabled
        self.direct_code_widget = None
        if self.direct_code_enabled:
            self.setup_direct_code_editor()
            
        # Children container for blocks that can contain other blocks
        if self.has_children:
            # Add a divider line
            divider = QFrame(self)
            divider.setFrameShape(QFrame.HLine)
            divider.setFrameShadow(QFrame.Sunken)
            divider.setStyleSheet("background-color: rgba(255, 255, 255, 100);")
            divider.setMaximumHeight(1)
            self.layout.addWidget(divider)
            
            self.children_container = QVBoxLayout()
            self.children_container.setContentsMargins(20, 8, 0, 0)
            self.children_container.setSpacing(4)
            self.layout.addLayout(self.children_container)
        
        # Else container for blocks that have an else clause
        if self.has_else:
            # Add a divider line
            divider = QFrame(self)
            divider.setFrameShape(QFrame.HLine)
            divider.setFrameShadow(QFrame.Sunken)
            divider.setStyleSheet("background-color: rgba(255, 255, 255, 100);")
            divider.setMaximumHeight(1)
            self.layout.addWidget(divider)
            
            self.else_label = QLabel("else:")
            self.else_label.setStyleSheet("""
                font-weight: bold; 
                color: white; 
                font-size: 11pt;
            """)
            self.layout.addWidget(self.else_label)
            
            self.else_container = QVBoxLayout()
            self.else_container.setContentsMargins(20, 8, 0, 0)
            self.else_container.setSpacing(4)
            self.layout.addLayout(self.else_container)
            
    def setup_direct_code_editor(self):
        """Set up a direct code editor for the block"""
        # Create a widget for direct code editing
        self.direct_code_widget = QWidget(self)
        direct_code_layout = QVBoxLayout(self.direct_code_widget)
        direct_code_layout.setContentsMargins(0, 5, 0, 5)
        
        # Add a text editor for code
        self.code_editor = QLineEdit(self)
        self.code_editor.setPlaceholderText("Enter Python code directly...")
        self.code_editor.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid rgba(0, 0, 0, 100);
                border-radius: 4px;
                padding: 4px 6px;
                min-height: 24px;
                font-family: monospace;
            }
        """)
        
        # Toggle button to switch between block and direct code modes
        self.toggle_code_button = QPushButton("Switch to Direct Code")
        self.toggle_code_button.setCheckable(True)
        self.toggle_code_button.clicked.connect(self.toggle_code_mode)
        
        direct_code_layout.addWidget(self.code_editor)
        direct_code_layout.addWidget(self.toggle_code_button)
        
        # Add to main layout but hide initially
        self.layout.addWidget(self.direct_code_widget)
        self.direct_code_widget.setVisible(False)

    def toggle_code_mode(self):
        """Toggle between block mode and direct code mode"""
        is_direct_code = self.toggle_code_button.isChecked()
        
        # Show or hide appropriate widgets based on mode
        for name, widget in self.inputs.items():
            widget.setVisible(not is_direct_code)
            
        # Toggle button text
        if is_direct_code:
            self.toggle_code_button.setText("Switch to Block Mode")
            # Generate and set code from current block state
            self.code_editor.setText(self.generate_code(0).strip())
        else:
            self.toggle_code_button.setText("Switch to Direct Code")
            # Here we would need to parse the code back to block format
            # That's complex to implement and would require a parser
        
        # Update block size
        self.updateGeometry()
        self.adjustSize()
        self.update()

    def toggle_collapse(self):
        """Toggle the collapsed state of a block with children"""
        if not hasattr(self, 'is_collapsed'):
            return
            
        self.is_collapsed = not self.is_collapsed
        
        # Update button text
        if self.is_collapsed:
            self.collapse_button.setText("+")
        else:
            self.collapse_button.setText("−")
        
        # Hide or show children
        if hasattr(self, 'children_container'):
            for i in range(self.children_container.count()):
                item = self.children_container.itemAt(i)
                if item and item.widget():
                    item.widget().setVisible(not self.is_collapsed)
        
        # Hide or show else container
        if hasattr(self, 'else_container'):
            if hasattr(self, 'else_label'):
                self.else_label.setVisible(not self.is_collapsed)
            for i in range(self.else_container.count()):
                item = self.else_container.itemAt(i)
                if item and item.widget():
                    item.widget().setVisible(not self.is_collapsed)
        
        # Update block size
        self.updateGeometry()
        self.adjustSize()
        self.update()
        
        # Update parent container if necessary
        if self.parent():
            self.parent().updateGeometry()

    def move_up(self):
        """Move this block up in its parent container"""
        parent = self.parent()
        if not parent:
            return
            
        # Find the parent that has this block in its list (could be a CodeBlock with children)
        if isinstance(parent, CodeBlock):
            # Check if this is in the child_blocks list
            if self in parent.child_blocks:
                index = parent.child_blocks.index(self)
                if index > 0:
                    # Swap positions with the block above
                    parent.children_container.removeWidget(self)
                    parent.child_blocks.remove(self)
                    parent.children_container.insertWidget(index - 1, self)
                    parent.child_blocks.insert(index - 1, self)
                    parent.inputChanged.emit()
            # Check if this is in the else_blocks list
            elif self in parent.else_blocks:
                index = parent.else_blocks.index(self)
                if index > 0:
                    # Swap positions with the block above
                    parent.else_container.removeWidget(self)
                    parent.else_blocks.remove(self)
                    parent.else_container.insertWidget(index - 1, self)
                    parent.else_blocks.insert(index - 1, self)
                    parent.inputChanged.emit()

    def move_down(self):
        """Move this block down in its parent container"""
        parent = self.parent()
        if not parent:
            return
            
        # Find the parent that has this block in its list (could be a CodeBlock with children)
        if isinstance(parent, CodeBlock):
            # Check if this is in the child_blocks list
            if self in parent.child_blocks:
                index = parent.child_blocks.index(self)
                if index < len(parent.child_blocks) - 1:
                    # Swap positions with the block below
                    parent.children_container.removeWidget(self)
                    parent.child_blocks.remove(self)
                    parent.children_container.insertWidget(index + 1, self)
                    parent.child_blocks.insert(index + 1, self)
                    parent.inputChanged.emit()
            # Check if this is in the else_blocks list
            elif self in parent.else_blocks:
                index = parent.else_blocks.index(self)
                if index < len(parent.else_blocks) - 1:
                    # Swap positions with the block below
                    parent.else_container.removeWidget(self)
                    parent.else_blocks.remove(self)
                    parent.else_container.insertWidget(index + 1, self)
                    parent.else_blocks.insert(index + 1, self)
                    parent.inputChanged.emit()

    def set_parent_slot(self, slot: Optional[BlockInputSlot]):
        """Set the parent slot for this block"""
        self.parent_slot = slot
        
        # Show or hide up/down buttons based on whether this is a child block
        has_block_parent = isinstance(self.parent(), CodeBlock)
        self.up_button.setVisible(has_block_parent)
        self.down_button.setVisible(has_block_parent)
    
    def setup_inputs(self):
        """Setup input widgets based on block definition"""
        # Clear old inputs
        if hasattr(self, 'inputs'):
            for input_name, widget in self.inputs.items():
                widget.deleteLater()
        
        # Initialize dictionaries for inputs and values
        self.inputs = {}
        self.input_values = {}
        
        # Get inputs from block definition
        inputs_def = self.block_definition.get('inputs', [])
        
        # Create a responsive form layout for inputs
        form_layout = QFormLayout()
        form_layout.setContentsMargins(5, 5, 5, 5)
        form_layout.setSpacing(8)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)  # Allow fields to grow
        form_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)  # Wrap long rows
        self.layout.addLayout(form_layout)
        
        # Create widgets for each input
        for input_def in inputs_def:
            input_name = input_def.get('name', 'input')
            input_type = input_def.get('type', 'text')
            default_value = input_def.get('default', '')
            
            if input_type == 'text':
                # Text input
                widget = QLineEdit(self)
                widget.setText(default_value)
                widget.setStyleSheet("""
                    QLineEdit {
                        background-color: rgba(255, 255, 255, 200);
                        border: 1px solid rgba(0, 0, 0, 100);
                        border-radius: 4px;
                        padding: 4px 6px;
                        min-height: 24px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #3498db;
                        background-color: white;
                    }
                """)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                widget.textChanged.connect(lambda text, name=input_name: self.on_input_changed(name, text))
                # Set minimum width to ensure text is visible
                widget.setMinimumWidth(150)
                
                # Calculate initial width based on default value
                if default_value:
                    text_width = widget.fontMetrics().horizontalAdvance(default_value) + 60
                    widget.setMinimumWidth(max(150, text_width))
                
            elif input_type == 'choice':
                # Dropdown choice
                widget = QComboBox(self)
                widget.setStyleSheet("""
                    QComboBox {
                        background-color: rgba(255, 255, 255, 200);
                        border: 1px solid rgba(0, 0, 0, 100);
                        border-radius: 4px;
                        padding: 2px 18px 2px 6px;
                        min-height: 24px;
                    }
                    QComboBox::drop-down {
                        subcontrol-origin: padding;
                        subcontrol-position: top right;
                        width: 18px;
                        border-left-width: 1px;
                        border-left-color: darkgray;
                        border-left-style: solid;
                        border-top-right-radius: 3px;
                        border-bottom-right-radius: 3px;
                    }
                """)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                choices = input_def.get('choices', [])
                widget.addItems(choices)
                if default_value in choices:
                    widget.setCurrentText(default_value)
                widget.currentTextChanged.connect(lambda text, name=input_name: self.on_input_changed(name, text))
                # Set minimum width to ensure dropdown text is visible
                widget.setMinimumWidth(150)
                
            elif input_type == 'slot':
                # Input slot for nested blocks
                widget = BlockInputSlot(self, input_name, f"Drop block here", self.block_type, default_value)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                widget.valueChanged.connect(self.on_slot_value_changed)
                widget.contentChanged.connect(self.inputChanged)
                widget.blockDropped.connect(self.forward_slot_drop)
                # Set minimum width for slot
                widget.setMinimumWidth(180)
                
            else:
                # Default to text input
                widget = QLineEdit(self)
                widget.setText(default_value)
                widget.setStyleSheet("""
                    QLineEdit {
                        background-color: rgba(255, 255, 255, 200);
                        border: 1px solid rgba(0, 0, 0, 100);
                        border-radius: 4px;
                        padding: 4px 6px;
                        min-height: 24px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #3498db;
                        background-color: white;
                    }
                """)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                widget.textChanged.connect(lambda text, name=input_name: self.on_input_changed(name, text))
                # Set minimum width to ensure text is visible
                widget.setMinimumWidth(150)
                
                # Calculate initial width based on default value
                if default_value:
                    text_width = widget.fontMetrics().horizontalAdvance(default_value) + 60
                    widget.setMinimumWidth(max(150, text_width))
            
            # Set initial value
            self.input_values[input_name] = default_value
            
            # Create label with consistent styling
            label = QLabel(input_name + ":", self)
            label.setStyleSheet("color: white; font-weight: bold; padding: 2px;")
            label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            label.setWordWrap(True)  # Allow label to wrap
            
            # Add to inputs dictionary and layout
            self.inputs[input_name] = widget
            form_layout.addRow(label, widget)
            
        # After adding all inputs, give the block a chance to resize to fit content
        self.updateGeometry()
        self.adjustSize()
    
    def on_input_changed(self, input_name: str, value: str):
        """Handle changes to input fields"""
        self.input_values[input_name] = value
        self.inputChanged.emit()
        
        # Update size when input content changes
        if input_name in self.inputs:
            widget = self.inputs[input_name]
            if isinstance(widget, QLineEdit):
                # Adjust the width based on text content
                text_width = widget.fontMetrics().horizontalAdvance(value) + 60
                widget.setMinimumWidth(max(150, text_width))
        
        # Update the block size
        self.updateGeometry()
        self.adjustSize()
        self.update()
    
    def on_slot_value_changed(self, input_name: str, value: str):
        """Handle changes to input slots"""
        self.input_values[input_name] = value
        self.inputChanged.emit()
    
    def add_child_block(self, block, is_else: bool = False):
        """Add a child block to this block's children container"""
        if not self.has_children and not (is_else and self.has_else):
            return False
            
        if is_else and self.has_else:
            self.else_blocks.append(block)
            self.else_container.addWidget(block)
        else:
            self.child_blocks.append(block)
            self.children_container.addWidget(block)
        
        return True
    
    def remove_child_block(self, block) -> bool:
        """Remove a child block from this block"""
        if block in self.child_blocks:
            self.child_blocks.remove(block)
            self.children_container.removeWidget(block)
            return True
        elif block in self.else_blocks:
            self.else_blocks.remove(block)
            self.else_container.removeWidget(block)
            return True
        return False
    
    def get_input_value(self, input_name: str) -> str:
        """Get the value of a specific input"""
        # Check if the input widget exists
        if input_name not in self.inputs:
            return ""
            
        # Get the input widget
        input_widget = self.inputs[input_name]
        
        # Extract value based on widget type
        try:
            if isinstance(input_widget, QLineEdit):
                return input_widget.text()
            elif isinstance(input_widget, QComboBox):
                return input_widget.currentText()
            elif isinstance(input_widget, BlockInputSlot):
                return input_widget.get_value()
            else:
                # Default fallback
                logger.warning(f"Unknown input widget type for {input_name}: {type(input_widget)}")
                if hasattr(input_widget, 'text'):
                    return input_widget.text()
                elif hasattr(input_widget, 'get_value'):
                    return input_widget.get_value()
                else:
                    return self.input_values.get(input_name, "")
        except Exception as e:
            logger.error(f"Error getting value for input {input_name}: {str(e)}")
            return f"<error: {str(e)}>"
    
    def get_output_value(self) -> str:
        """Get the output value for this block when nested"""
        if not self.output_enabled:
            return ""
            
        try:
            # Use output_value from definition or generate from template
            if self.output_value:
                return self._process_template(self.output_value)
            return self._process_template(self.code_template)
        except Exception as e:
            logger.error(f"Error getting output value for block {self.block_type}: {str(e)}")
            return f"<error: {str(e)}>"
    
    def _process_template(self, template: str) -> str:
        """Process a template string, replacing {input_name} with input values"""
        try:
            # Create a dictionary of input values using get_input_value
            input_values = {}
            for input_name in self.inputs:
                input_values[input_name] = self.get_input_value(input_name)
            
            # Create outputs dictionary properly
            output_values = {}
            # Filter input_values for any that start with 'output_'
            for key, value in self.input_values.items():
                if key.startswith('output_'):
                    output_values[key] = value
            
            # Create a template context with both inputs and outputs using DotDict
            template_context = {
                'inputs': DotDict(input_values),
                'outputs': DotDict(output_values)
            }
            
            # Process the template
            return safely_format_template(template, template_context)
        except Exception as e:
            logger.error(f"Error processing template for block {self.block_type}: {str(e)}")
            return f"<error: {str(e)}>"
    
    def generate_code(self, indentation_level=0):
        """
        Generate Python code based on the block's template and properties.
        
        Args:
            indentation_level: The level of indentation for the generated code
            
        Returns:
            A string containing the generated Python code
        """
        try:
            # Create consistent indentation string
            indent = "    " * indentation_level
            result = ""
            
            # Special handling for Print and Input blocks (more user-friendly)
            special_handling_blocks = ["Print", "Input"]
            
            # Try to get input values with error handling
            input_values = {}
            
            # Get values from input widgets
            for input_name, input_widget in self.inputs.items():
                try:
                    # Handle different types of input widgets based on their actual type
                    if isinstance(input_widget, QLineEdit):
                        value = input_widget.text()
                    elif isinstance(input_widget, QComboBox):
                        value = input_widget.currentText()
                    elif hasattr(input_widget, 'get_value'):
                        # For custom widgets with get_value method
                        value = input_widget.get_value()
                    elif hasattr(input_widget, 'text'):
                        # Fallback for other widgets with text method
                        value = input_widget.text()
                    else:
                        # Default value if we can't determine the widget type
                        logger.warning(f"Unknown input widget type for {input_name}: {type(input_widget)}")
                        value = str(input_widget.objectName()) if hasattr(input_widget, 'objectName') else ""
                        
                    # Special handling for Print and Input blocks
                    if self.block_type in special_handling_blocks:
                        # For Print blocks, fix message formatting
                        if self.block_type == "Print" and input_name == "message":
                            # Use utility function to determine if quoting is needed
                            if not is_variable_reference(value) and not value.startswith('"') and not value.startswith("'"):
                                value = f'"{value}"'
                                
                        # For Input blocks, ensure prompt has quotes
                        elif self.block_type == "Input" and input_name == "prompt":
                            value = apply_safe_quote_rules(value, "string")
                    
                    input_values[input_name] = value
                except Exception as e:
                    logger.error(f"Error getting value for input {input_name}: {str(e)}")
                    input_values[input_name] = f"\"<error: {str(e)}>\""
            
            # Handle direct code blocks differently
            if hasattr(self, 'direct_code_enabled') and self.direct_code_enabled:
                # For direct code, just output the code directly with indentation
                code_input = input_values.get('code', '')
                
                # Handle multi-line direct code
                for line in code_input.splitlines():
                    if line.strip():  # Skip empty lines
                        result += indent + line + '\n'
                    else:
                        result += '\n'  # Preserve empty lines
            else:
                # Process template with input values
                try:
                    template = self.code_template
                    
                    # Create template context with inputs and outputs
                    output_values = {}
                    if hasattr(self, 'outputs'):
                        for output_name, output_widget in self.outputs.items():
                            if isinstance(output_widget, QLineEdit):
                                output_values[output_name] = output_widget.text()
                            elif isinstance(output_widget, QComboBox):
                                output_values[output_name] = output_widget.currentText()
                            elif hasattr(output_widget, 'get_value'):
                                output_values[output_name] = output_widget.get_value()
                            elif hasattr(output_widget, 'text'):
                                output_values[output_name] = output_widget.text()
                            else:
                                output_values[output_name] = ""
                    
                    # Create the context for template formatting
                    template_context = {
                        'inputs': DotDict(input_values),
                        'outputs': DotDict(output_values)
                    }
                    
                    # Process the template safely
                    processed_template = safely_format_template(template, template_context)
                    
                    # Add indentation to each line
                    lines = processed_template.splitlines()
                    for line in lines:
                        result += indent + line + '\n'
                        
                except Exception as e:
                    logger.error(f"Error processing template for block {self.block_type}: {str(e)}")
                    result = indent + format_error_message(e, self.block_type) + '\n'
            
            # Process child blocks if this block has children
            try:
                if hasattr(self, 'has_children') and self.has_children:
                    # Add child blocks with increased indentation
                    if hasattr(self, 'child_blocks') and self.child_blocks:
                        for child in self.child_blocks:
                            child_code = child.generate_code(indentation_level + 1)
                            result += child_code
                    else:
                        # If no child blocks, add a pass statement
                        result += indent + "    pass\n"
                        
                    # Add else block if present
                    if hasattr(self, 'has_else') and self.has_else and hasattr(self, 'else_template'):
                        result += indent + self.else_template + '\n'
                        
                        # Add else child blocks with increased indentation
                        if hasattr(self, 'else_blocks') and self.else_blocks:
                            for child in self.else_blocks:
                                child_code = child.generate_code(indentation_level + 1)
                                result += child_code
                        else:
                            # If no else blocks, add a pass statement
                            result += indent + "    pass\n"
            except Exception as e:
                logger.error(f"Error processing child blocks for {self.block_type}: {str(e)}")
                result += indent + "    # Error processing child blocks\n"
                result += indent + "    pass\n"
            
            # If this is a top-level block, make sure there's no indentation
            if indentation_level == 0:
                if result.startswith("    "):
                    result = result.replace("    ", "", 1)
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in generate_code for block {self.block_type}: {str(e)}")
            return f"# {format_error_message(e, self.block_type)}\n"
    
    def mousePressEvent(self, event):
        """Handle mouse press events for dragging and selection"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.selected.emit(self)
            self.set_selected(True)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging"""
        if not (event.buttons() & Qt.LeftButton) or not self.drag_start_position:
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # Start drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Serialize basic block data to JSON for drop handling
        block_data = {
            "block_type": self.block_type,
            "id": id(self),  # Use object ID to identify this block
            "new_block": False  # This is an existing block, not a new one
        }
        mime_data.setData("application/x-codeblockeditor-block", json.dumps(block_data).encode('utf-8'))
        
        drag.setMimeData(mime_data)
        
        # Create a semi-transparent version of the block for dragging
        pixmap = self.grab()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 180))
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Execute the drag - use CopyAction for slots, MoveAction for workspace
        if self.parent_slot:
            result = drag.exec_(Qt.CopyAction)
        else:
            result = drag.exec_(Qt.MoveAction)
    
    def set_selected(self, selected: bool):
        """Set the selected state of this block"""
        self.is_selected = selected
        # Update appearance
        self.update()
    
    def contextMenuEvent(self, event):
        """Show context menu for block operations"""
        menu = QMenu(self)
        
        # Basic operations
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.deleted.emit(self))
        menu.addAction(delete_action)
        
        duplicate_action = QAction("Duplicate", self)
        # duplicate_action.triggered.connect(self.duplicate)
        menu.addAction(duplicate_action)
        
        # Copy/paste operations
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_to_clipboard)
        menu.addAction(copy_action)
        
        # Direct code toggle if enabled
        if self.direct_code_enabled:
            menu.addSeparator()
            if hasattr(self, 'direct_code_widget') and self.direct_code_widget.isVisible():
                code_toggle_action = QAction("Switch to Block Mode", self)
            else:
                code_toggle_action = QAction("Switch to Direct Code", self)
            code_toggle_action.triggered.connect(self.toggle_code_mode)
            menu.addAction(code_toggle_action)
        
        # Import/export actions if supported
        if self.can_import_blocks:
            menu.addSeparator()
            import_action = QAction("Import Blocks...", self)
            # import_action.triggered.connect(self.import_blocks)
            menu.addAction(import_action)
            
            export_action = QAction("Export Block...", self)
            # export_action.triggered.connect(self.export_block)
            menu.addAction(export_action)
        
        menu.exec_(event.globalPos())
    
    def copy_to_clipboard(self):
        """Copy this block's data to clipboard"""
        block_json = json.dumps(self.to_json(), indent=2)
        clipboard = QApplication.clipboard()
        clipboard.setText(block_json)
        
        # Show a brief message to confirm copy
        msg = QMessageBox()
        msg.setWindowTitle("Block Copied")
        msg.setText("Block copied to clipboard as JSON data.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
    
    def paintEvent(self, event):
        """Custom paint event to draw the block with gradient background and selection highlight"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Block shape
        block_rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        path = QPainterPath()
        
        # Use block_rounding setting from app settings
        rounding = settings.get_app_setting("blocks", "block_rounding", default=8)
        
        path.addRoundedRect(block_rect, rounding, rounding)
        
        # Draw drop shadow first (if enabled)
        if settings.get_app_setting("blocks", "block_shadows", default=True):
            shadow_path = QPainterPath()
            shadow_rect = QRectF(block_rect).adjusted(1, 1, 1, 1)
            shadow_path.addRoundedRect(shadow_rect, rounding, rounding)
            
            # Draw the shadow underneath
            painter.save()
            painter.translate(2, 2)
            painter.fillPath(shadow_path, QColor(0, 0, 0, 40))
            painter.restore()
        
        # Gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        base_color = self.block_color
        lighter_color = QColor(base_color.lighter(115))
        darker_color = QColor(base_color.darker(110))
        
        gradient.setColorAt(0, lighter_color)
        gradient.setColorAt(1, darker_color)
        
        # Draw the block background
        painter.fillPath(path, gradient)
        
        # Draw selection border if selected
        if self.is_selected:
            # More prominent selection border
            selection_color = QColor("#ffffff")
            pen = QPen(selection_color, 2.5, Qt.DashLine)
            pen.setDashOffset(4)  # Offset the dash pattern
            painter.setPen(pen)
            painter.drawPath(path)
            
            # Add a glow effect
            glow_path = QPainterPath()
            glow_rect = QRectF(block_rect).adjusted(-2, -2, 2, 2)
            glow_path.addRoundedRect(glow_rect, rounding + 2, rounding + 2)
            
            glow_color = QColor(255, 255, 255, 40)
            painter.fillPath(glow_path, glow_color)
        else:
            # Draw regular border - slightly darker than the base color
            border_color = QColor(base_color.darker(130))
            painter.setPen(QPen(border_color, 1.5))
            painter.drawPath(path)
        
        # Let the normal rendering continue for child widgets
        super().paintEvent(event)
    
    def to_json(self) -> Dict[str, Any]:
        """Serialize the block to JSON"""
        data = {
            "block_type": self.block_type,
            "inputs": {}
        }
        
        # Save input values
        for input_name, input_widget in self.inputs.items():
            if isinstance(input_widget, BlockInputSlot) and input_widget.nested_block:
                # Save nested block
                data["inputs"][input_name] = {
                    "type": "slot",
                    "nested_block": input_widget.nested_block.to_json()
                }
            else:
                data["inputs"][input_name] = {
                    "type": "value",
                    "value": self.input_values.get(input_name, "")
                }
        
        # Save child blocks
        if self.has_children and self.child_blocks:
            data["child_blocks"] = [block.to_json() for block in self.child_blocks]
        
        # Save else blocks
        if self.has_else and self.else_blocks:
            data["else_blocks"] = [block.to_json() for block in self.else_blocks]
        
        return data
    
    @classmethod
    def from_json(cls, data: Dict[str, Any], parent=None):
        """Deserialize a block from JSON"""
        block_type = data.get("block_type", "")
        block = cls(parent=parent, block_type=block_type)
        
        # Load input values
        inputs_data = data.get("inputs", {})
        for input_name, input_data in inputs_data.items():
            if input_name in block.inputs:
                input_type = input_data.get("type", "value")
                
                if input_type == "value":
                    value = input_data.get("value", "")
                    if isinstance(block.inputs[input_name], QLineEdit):
                        block.inputs[input_name].setText(value)
                    elif isinstance(block.inputs[input_name], QComboBox):
                        block.inputs[input_name].setCurrentText(value)
                    block.input_values[input_name] = value
                
                # Nested blocks would be handled by the workspace when loading
        
        return block

    def forward_slot_drop(self, slot, block_data, drop_type):
        """Forward slot drop signals to the workspace"""
        self.slotDropReceived.emit(slot, block_data, drop_type) 

    def sizeHint(self) -> QSize:
        """Return the recommended size for the block based on its content"""
        # Start with minimum dimensions
        width = 200  # Minimum width
        height = self.layout.sizeHint().height() + 20  # Basic height + padding
        
        # Adjust width based on title length
        title_width = self.title_label.sizeHint().width() + 60  # Title + padding
        width = max(width, title_width)
        
        # Adjust width based on input content
        for name, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                # For text inputs, calculate width based on content
                text = widget.text()
                if text:
                    text_width = widget.fontMetrics().horizontalAdvance(text) + 80
                    width = max(width, text_width)
            elif isinstance(widget, QComboBox):
                # For combo boxes, calculate width based on current selection
                text = widget.currentText()
                if text:
                    text_width = widget.fontMetrics().horizontalAdvance(text) + 100  # Extra space for dropdown arrow
                    width = max(width, text_width)
            elif isinstance(widget, BlockInputSlot):
                # For slots with nested blocks, account for their width
                if widget.nested_block:
                    slot_width = widget.nested_block.sizeHint().width() + 40
                    width = max(width, slot_width)
        
        # Adjust width based on any child blocks (for if/loop blocks)
        if hasattr(self, 'child_blocks') and self.child_blocks:
            for child in self.child_blocks:
                child_width = child.sizeHint().width() + 40  # Child width + indentation
                width = max(width, child_width)
        
        # Ensure width is between min and max
        width = max(200, min(width, 450))  # Increase max width to 450
        
        return QSize(width, height)
    
    def minimumSizeHint(self) -> QSize:
        """Return the minimum size needed for the block"""
        # Always ensure the block has enough space for title and controls
        width = 200
        height = 70  # Minimum height for basic block
        
        # Add space for inputs
        if self.inputs:
            height += len(self.inputs) * 30
        
        return QSize(width, height)
    
    def resizeEvent(self, event):
        """Handle resize events to update layout"""
        super().resizeEvent(event)
        
        # Update layout when block is resized
        self.layout.invalidate()
        self.layout.activate()
        
        # Force layout update for child widgets
        for name, widget in self.inputs.items():
            if hasattr(widget, 'updateGeometry'):
                widget.updateGeometry()
        
        # Ensure proper appearance after resize
        self.update() 

    def get_debug_info(self) -> str:
        """Get debug information about this block for logging purposes"""
        info = f"Block type: {self.block_type}, ID: {id(self)}"
        if hasattr(self, 'has_children'):
            info += f", has_children: {self.has_children}"
        if hasattr(self, 'child_blocks'):
            info += f", child_blocks: {len(self.child_blocks) if self.child_blocks else 0}"
        if hasattr(self, 'has_else'):
            info += f", has_else: {self.has_else}"
        if hasattr(self, 'else_blocks'):
            info += f", else_blocks: {len(self.else_blocks) if self.else_blocks else 0}"
        if hasattr(self, 'parent_slot'):
            info += f", in_slot: {self.parent_slot is not None}"
        return info 

    def validate_connection(self, target_block: 'CodeBlock') -> Tuple[bool, str]:
        """
        Validate whether a connection between this block and another block is valid.
        This method will be extended in the future to use deep learning for smarter validation.
        
        Args:
            target_block: The block to validate connection with
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Basic validation based on block type compatibility
        if self.block_type == "VariableAssign":
            # Variable assignments can accept most value types
            if target_block.block_type in ["Print", "Input", "If", "For", "While"]:
                return False, f"{target_block.block_type} is not a valid value for variable assignment"
            return True, "Valid value for variable assignment"
            
        elif self.block_type == "Print":
            # Print can accept almost any value
            return True, "Valid value for printing"
            
        elif self.block_type == "Input":
            # Input prompt should be a string
            if target_block.block_type not in ["StringValue", "VariableValue"]:
                return False, f"{target_block.block_type} is not a valid prompt for input"
            return True, "Valid prompt for input"
            
        elif self.block_type == "If":
            # Condition should be a boolean expression or value
            if target_block.block_type in ["Print", "Input"]:
                return False, f"{target_block.block_type} cannot be used as a condition"
            return True, "Valid condition for If statement"
            
        # Default case - allow connection
        return True, "Connection is valid"
    
    def get_connection_recommendation(self, available_blocks: List[str]) -> List[str]:
        """
        Get recommended blocks that can connect to this block.
        This is a placeholder for future deep learning-based recommendations.
        
        Args:
            available_blocks: List of available block types
            
        Returns:
            List of recommended block types to connect
        """
        # Basic recommendations based on block type
        if self.block_type == "VariableAssign":
            return [b for b in available_blocks if b in [
                "StringValue", "NumberValue", "BooleanValue", "VariableValue",
                "Add", "Subtract", "Multiply", "Divide", "Input"
            ]]
            
        elif self.block_type == "Print":
            return [b for b in available_blocks if b in [
                "StringValue", "NumberValue", "BooleanValue", "VariableValue", 
                "Input", "Add", "Subtract", "Multiply", "Divide"
            ]]
            
        elif self.block_type == "If":
            return [b for b in available_blocks if b in [
                "BooleanValue", "VariableValue", "Equal", "NotEqual", 
                "LessThan", "GreaterThan", "And", "Or", "Not"
            ]]
            
        # Default - recommend common blocks
        return [b for b in available_blocks if b in [
            "StringValue", "NumberValue", "BooleanValue", "VariableValue"
        ]] 