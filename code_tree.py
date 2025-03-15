import logging
from typing import Dict, List, Any, Optional

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QBrush
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, 
                           QLabel, QFrame, QHBoxLayout, QSizePolicy, QMenu, QAction)

from settings_loader import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('code_tree')

class CodeTreeItem(QTreeWidgetItem):
    """
    Tree item representing a code block or code structure element.
    """
    def __init__(self, parent, block_type: str, block_id: int = None, 
                 color: List[int] = None, is_container: bool = False,
                 code_snippet: str = ""):
        super().__init__(parent)
        self.block_type = block_type
        self.block_id = block_id  # Reference to the actual block's ID
        self.is_container = is_container
        self.code_snippet = code_snippet
        
        # Set display text
        self.setText(0, block_type)
        
        # Set tooltip with code snippet
        if code_snippet:
            self.setToolTip(0, code_snippet)
        
        # Set color indicator
        if color and len(color) >= 3:
            self.setForeground(0, QColor(*color))
            
            # Create colored icon
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor(*color)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(2, 2, 12, 12, 3, 3)
            painter.end()
            
            self.setIcon(0, QIcon(pixmap))
        
        # Indicate if this is a container block like if/for/while
        if is_container:
            font = self.font(0)
            font.setBold(True)
            self.setFont(0, font)


class CodeTree(QWidget):
    """
    Tree view for navigating and managing code block structure.
    Provides a hierarchical view of the blocks in the workspace.
    """
    blockSelected = pyqtSignal(int)  # Signal when a block is selected in the tree
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocks_map = {}  # Maps block IDs to tree items
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QFrame()
        header.setFrameShape(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Code Structure")
        title.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title)
        
        # Add header to main layout
        layout.addWidget(header)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # Apply style
        theme = settings.get_current_theme()
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {theme.get('panel_color', '#ffffff')};
                border: none;
            }}
            QTreeWidget::item {{
                padding: 4px 0;
            }}
            QTreeWidget::item:selected {{
                background-color: {theme.get('selection_color', '#3498db')};
                color: white;
            }}
        """)
        
        layout.addWidget(self.tree)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumWidth(200)
    
    def update_from_blocks(self, blocks: List[Any], workspace_blocks: List[Any] = None):
        """
        Update the tree from the list of blocks in the workspace.
        
        Args:
            blocks: List of top-level blocks
            workspace_blocks: Optional list of all blocks in the workspace (for reference)
        """
        # Clear existing items
        self.tree.clear()
        self.blocks_map.clear()
        
        # Log the update
        logger.info(f"Updating code tree with {len(blocks)} blocks")
        
        # Add top-level blocks
        top_level_added = 0
        for block in blocks:
            # Only add top-level blocks (not in slots)
            is_top_level = True
            if hasattr(block, 'parent_slot') and block.parent_slot is not None:
                is_top_level = False
            
            if is_top_level:
                try:
                    self.add_block_to_tree(block)
                    top_level_added += 1
                except Exception as e:
                    logger.error(f"Error adding block to tree: {e}")
        
        logger.info(f"Added {top_level_added} top-level blocks to code tree")
        
        # Expand all items
        self.tree.expandAll()
    
    def add_block_to_tree(self, block, parent_item: Optional[QTreeWidgetItem] = None):
        """
        Add a block to the tree view recursively.
        
        Args:
            block: The block to add
            parent_item: Optional parent tree item
        
        Returns:
            The created tree item
        """
        # Get block properties
        block_type = block.block_type
        block_id = id(block)
        
        # Get block color (support multiple formats)
        color = None
        if hasattr(block, 'block_color'):
            color = [
                block.block_color.red(),
                block.block_color.green(),
                block.block_color.blue()
            ]
        elif hasattr(block, 'color'):
            # Direct color property
            color = block.color
        
        # Generate a code snippet for the tooltip
        code_snippet = ""
        if hasattr(block, 'generate_code'):
            try:
                code_snippet = block.generate_code(0).strip()
                # Limit length for tooltip
                if len(code_snippet) > 100:
                    code_snippet = code_snippet[:97] + "..."
            except Exception as e:
                logger.error(f"Error generating code snippet: {e}")
                code_snippet = f"{block_type} (code generation error)"
        
        # Check if this is a container block
        is_container = False
        # Check different ways a block might indicate it has children
        if hasattr(block, 'has_children'):
            is_container = block.has_children
        elif hasattr(block, 'child_blocks') and block.child_blocks:
            is_container = True
        elif hasattr(block, 'else_blocks') and block.else_blocks:
            is_container = True
        
        # Log what we're adding to help debug
        logger.debug(f"Adding block to tree: {block_type} (ID: {block_id})")
        
        # Create the tree item
        if parent_item:
            item = CodeTreeItem(parent_item, block_type, block_id, color, is_container, code_snippet)
        else:
            item = CodeTreeItem(self.tree, block_type, block_id, color, is_container, code_snippet)
        
        # Store in the map for lookup
        self.blocks_map[block_id] = item
        
        # Add any slots with nested blocks
        if hasattr(block, 'inputs'):
            for input_name, input_widget in block.inputs.items():
                # Check different ways of having nested blocks in inputs
                nested_block = None
                if hasattr(input_widget, 'nested_block'):
                    nested_block = input_widget.nested_block
                elif hasattr(input_widget, 'block'):
                    nested_block = input_widget.block
                
                if nested_block:
                    nested_item = CodeTreeItem(item, f"{input_name}:", None)
                    nested_item.setForeground(0, QColor(100, 100, 100))  # Subdued color
                    self.add_block_to_tree(nested_block, nested_item)
        
        # Add child blocks
        if hasattr(block, 'child_blocks') and block.child_blocks:
            for child_block in block.child_blocks:
                self.add_block_to_tree(child_block, item)
        
        # Add else blocks
        if hasattr(block, 'else_blocks') and block.else_blocks:
            else_item = CodeTreeItem(item, "else:", None)
            else_item.setForeground(0, QColor(100, 100, 100))  # Subdued color
            
            for else_block in block.else_blocks:
                self.add_block_to_tree(else_block, else_item)
        
        return item
    
    def on_item_clicked(self, item, column):
        """Handle item clicked in the tree"""
        if isinstance(item, CodeTreeItem) and item.block_id is not None:
            # Emit signal with the block ID
            self.blockSelected.emit(item.block_id)
    
    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.tree.itemAt(position)
        if item is None:
            return
            
        menu = QMenu()
        if isinstance(item, CodeTreeItem) and item.block_id is not None:
            # Add actions for blocks
            focus_action = QAction("Focus Block", self)
            focus_action.triggered.connect(lambda: self.focus_block(item.block_id))
            menu.addAction(focus_action)
            
            # More options if it's a container
            if item.is_container:
                expand_action = QAction("Expand All", self)
                expand_action.triggered.connect(lambda: self.expand_item(item))
                menu.addAction(expand_action)
                
                collapse_action = QAction("Collapse All", self)
                collapse_action.triggered.connect(lambda: self.collapse_item(item))
                menu.addAction(collapse_action)
        
        # Only show menu if it has actions
        if not menu.isEmpty():
            menu.exec_(self.tree.viewport().mapToGlobal(position))
    
    def focus_block(self, block_id):
        """Focus on a specific block"""
        self.blockSelected.emit(block_id)
    
    def expand_item(self, item):
        """Expand an item and all its children"""
        self._set_expanded_recursive(item, True)
    
    def collapse_item(self, item):
        """Collapse an item and all its children"""
        self._set_expanded_recursive(item, False)
    
    def _set_expanded_recursive(self, item, expanded):
        """Set expanded state recursively"""
        item.setExpanded(expanded)
        for i in range(item.childCount()):
            self._set_expanded_recursive(item.child(i), expanded)
    
    def select_block_by_id(self, block_id):
        """Select a block in the tree by its ID"""
        if block_id in self.blocks_map:
            item = self.blocks_map[block_id]
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)
    
    def refresh(self):
        """Refresh the tree from the current workspace"""
        # This method should be called when the workspace changes
        # It would re-fetch blocks from the workspace and update the tree
        pass 