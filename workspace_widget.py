import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from PyQt5.QtCore import Qt, QMimeData, QPoint, QRect, QRectF, QSize, pyqtSignal, QEvent
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QDrag, QPixmap, QPainterPath
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QFrame,
                           QMenu, QAction, QApplication, QSizePolicy, QScrollBar)

from block_models import CodeBlock, BlockInputSlot
from settings_loader import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('workspace_widget')

class WorkspaceWidget(QScrollArea):
    """
    The main workspace widget where code blocks are arranged and connected.
    Supports drag-and-drop, saving/loading, and generating Python code.
    """
    codeChanged = pyqtSignal(str)  # Emitted when code blocks change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Block management
        self.blocks = []  # All blocks in the workspace
        self.selected_blocks = set()  # Currently selected blocks
        self.clipboard = []  # Blocks copied to clipboard
        self.snap_to_grid = settings.get_app_setting("blocks", "snap_to_grid", default=True)
        self.grid_size = settings.get_app_setting("blocks", "grid_size", default=10)
        self.show_alignment_guides = settings.get_app_setting("blocks", "show_alignment_guides", default=True)
        
        # Setup UI
        self.init_ui()
        
        # Track window resize events
        self.installEventFilter(self)
        
        # Set keyboard shortcuts
        self.setup_shortcuts()
    
    def init_ui(self):
        """Initialize the workspace UI"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAcceptDrops(True)
        
        # Main container widget
        self.container = WorkspaceContainer(self)
        self.setWidget(self.container)
        
        # Set style from current theme
        self.update_style()
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts for workspace actions"""
        # Copy shortcut
        self.copy_shortcut = QAction("Copy", self)
        self.copy_shortcut.setShortcut("Ctrl+C")
        self.copy_shortcut.triggered.connect(self.copy_selected_blocks)
        self.addAction(self.copy_shortcut)
        
        # Paste shortcut
        self.paste_shortcut = QAction("Paste", self)
        self.paste_shortcut.setShortcut("Ctrl+V")
        self.paste_shortcut.triggered.connect(self.paste_blocks)
        self.addAction(self.paste_shortcut)
        
        # Delete shortcut
        self.delete_shortcut = QAction("Delete", self)
        self.delete_shortcut.setShortcut("Delete")
        self.delete_shortcut.triggered.connect(self.delete_selected_blocks)
        self.addAction(self.delete_shortcut)
        
        # Select all shortcut
        self.select_all_shortcut = QAction("Select All", self)
        self.select_all_shortcut.setShortcut("Ctrl+A")
        self.select_all_shortcut.triggered.connect(self.select_all_blocks)
        self.addAction(self.select_all_shortcut)
        
        # Duplicate shortcut
        self.duplicate_shortcut = QAction("Duplicate", self)
        self.duplicate_shortcut.setShortcut("Ctrl+D")
        self.duplicate_shortcut.triggered.connect(self.duplicate_selected_blocks)
        self.addAction(self.duplicate_shortcut)
    
    def copy_selected_blocks(self):
        """Copy selected blocks to clipboard"""
        if not self.selected_blocks:
            return
            
        # Store the blocks in the clipboard
        self.clipboard = list(self.selected_blocks)
        
        # Also serialize to system clipboard
        block_data = [block.to_json() for block in self.selected_blocks]
        json_data = json.dumps(block_data, indent=2)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(json_data)
    
    def paste_blocks(self):
        """Paste blocks from clipboard"""
        # Check if we have blocks in our internal clipboard
        if self.clipboard:
            # Calculate paste position - offset from original to avoid direct overlap
            offset = 20
            for block in self.clipboard:
                # Create a new block from the clipboard block type
                new_block = self.add_block(block.block_type)
                if new_block:
                    # Position the new block with an offset from original
                    original_pos = block.pos()
                    new_block.move(original_pos.x() + offset, original_pos.y() + offset)
                    offset += 10  # Cascade blocks when pasting multiple
            
            # Update code
            self.update_code()
    
    def delete_selected_blocks(self):
        """Delete all selected blocks"""
        if not self.selected_blocks:
            return
            
        # Make a copy of the list since we'll be modifying it during iteration
        blocks_to_remove = list(self.selected_blocks)
        
        for block in blocks_to_remove:
            self.remove_block(block)
            
        self.selected_blocks.clear()
        
        # Update the generated code
        self.update_code()
    
    def select_all_blocks(self):
        """Select all blocks in workspace"""
        self.selected_blocks.clear()
        
        for block in self.blocks:
            if not block.parent_slot:  # Only select top-level blocks
                block.set_selected(True)
                self.selected_blocks.add(block)
    
    def duplicate_selected_blocks(self):
        """Duplicate selected blocks"""
        if not self.selected_blocks:
            return
            
        # Store current selection
        current_selection = list(self.selected_blocks)
        self.selected_blocks.clear()
        
        # Duplicate each block
        offset = 20
        for block in current_selection:
            # Create a new block of the same type
            new_block = self.add_block(block.block_type)
            if new_block:
                # Position the new block with an offset from original
                original_pos = block.pos()
                new_block.move(original_pos.x() + offset, original_pos.y() + offset)
                offset += 10  # Cascade blocks when duplicating multiple
                
                # Select the new block
                new_block.set_selected(True)
                self.selected_blocks.add(new_block)
        
        # Unselect original blocks
        for block in current_selection:
            block.set_selected(False)
        
        # Update code
        self.update_code()
    
    def eventFilter(self, obj, event):
        """Filter events to catch resize events"""
        if obj == self and event.type() == QEvent.Resize:
            # Adjust container size to be at least the viewport size
            viewport_size = self.viewport().size()
            container_size = self.container.size()
            
            new_width = max(container_size.width(), viewport_size.width())
            new_height = max(container_size.height(), viewport_size.height())
            
            if new_width > container_size.width() or new_height > container_size.height():
                self.container.setMinimumSize(new_width, new_height)
        
        return super().eventFilter(obj, event)
    
    def update_style(self):
        """Update the workspace style from theme settings"""
        theme = settings.get_current_theme()
        background_color = theme.get("background_color", "#f5f5f5")
        border_color = theme.get("border_color", "#dddddd")
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {background_color};
                border: 1px solid {border_color};
                border-radius: 0px;
            }}
        """)
    
    def add_block(self, block_type: str, position: QPoint = None) -> Optional[CodeBlock]:
        """
        Add a new block to the workspace.
        
        Args:
            block_type: The type of block to add
            position: Optional position to place the block
            
        Returns:
            The created block instance or None if creation failed
        """
        # Get block definition from settings
        block_definition = settings.get_block_definition(block_type)
        if not block_definition:
            logger.error(f"Block definition not found for type: {block_type}")
            return None
        
        # Create the block
        block = CodeBlock(self.container, block_type, block_definition)
        
        # Connect signals
        block.moved.connect(self.on_block_moved)
        block.deleted.connect(self.on_block_deleted)
        block.inputChanged.connect(self.on_block_changed)
        block.selected.connect(self.on_block_selected)
        block.slotDropReceived.connect(self.handle_slot_drop)
        
        # Add to workspace
        self.blocks.append(block)
        block.show()
        
        # Position the block
        if position:
            snap_to_grid = settings.get_app_setting("blocks", "snap_to_grid", default=True)
            grid_size = settings.get_app_setting("blocks", "grid_size", default=10)
            
            if snap_to_grid:
                # Snap to grid
                x = int(position.x() / grid_size) * grid_size
                y = int(position.y() / grid_size) * grid_size
                position = QPoint(x, y)
            
            block.move(position)
        
        # Update the generated code
        self.update_code()
        
        return block
    
    def add_block_to_slot(self, block: CodeBlock, slot: BlockInputSlot) -> bool:
        """
        Add a block to an input slot.
        
        Args:
            block: The block to add
            slot: The slot to add the block to
            
        Returns:
            True if successful, False otherwise
        """
        if not slot.can_accept_block(block):
            return False
        
        # If the block is already in the workspace and not in a slot,
        # we need to update its parent
        if block in self.blocks and not block.parent_slot:
            self.blocks.remove(block)
        
        # Add to slot
        slot.add_block(block)
        
        # Update the generated code
        self.update_code()
        
        return True
    
    def remove_block(self, block: CodeBlock) -> bool:
        """
        Remove a block from the workspace.
        
        Args:
            block: The block to remove
            
        Returns:
            True if successful, False otherwise
        """
        # If the block is in a slot, remove it from the slot
        if block.parent_slot:
            block.parent_slot.remove_block()
        
        # Remove from workspace
        if block in self.blocks:
            self.blocks.remove(block)
            block.deleteLater()
            
            # Update the generated code
            self.update_code()
            
            return True
        
        return False
    
    def clear_workspace(self):
        """Remove all blocks from the workspace"""
        # Make a copy of the list since we'll be modifying it
        blocks_to_remove = self.blocks.copy()
        
        for block in blocks_to_remove:
            self.remove_block(block)
        
        self.blocks.clear()
        self.selected_blocks.clear()
        
        # Update the generated code
        self.update_code()
    
    def on_block_moved(self, position: QPoint):
        """Handle block moved signal"""
        # Update the generated code
        self.update_code()
    
    def on_block_deleted(self, block: CodeBlock):
        """Handle block deleted signal"""
        self.remove_block(block)
    
    def on_block_changed(self):
        """Handle block input changed signal"""
        # Update the generated code
        self.update_code()
    
    def on_block_selected(self, block: CodeBlock):
        """Handle block selected signal"""
        # Deselect other blocks if not holding Ctrl
        if not QApplication.keyboardModifiers() & Qt.ControlModifier:
            for b in self.selected_blocks:
                if b != block:
                    b.set_selected(False)
            self.selected_blocks = {block}
        else:
            # Toggle selection with Ctrl
            if block in self.selected_blocks:
                self.selected_blocks.remove(block)
                block.set_selected(False)
            else:
                self.selected_blocks.add(block)
    
    def update_code(self):
        """Generate and emit the Python code from the current blocks"""
        code = ""
        
        # Sort blocks by vertical position
        sorted_blocks = sorted(self.blocks, key=lambda b: b.pos().y())
        
        # Generate code only for top-level blocks (not in slots)
        for block in sorted_blocks:
            # Skip blocks that are in slots (they'll be processed by their parent)
            if not block.parent_slot:
                block_code = block.generate_code()
                if block_code:
                    # Process each line to ensure proper formatting
                    lines = block_code.strip().split('\n')
                    processed_lines = []
                    
                    # For the first line, remove any indentation
                    if lines and lines[0].strip():
                        processed_lines.append(lines[0].lstrip())
                    
                    # For subsequent lines, keep original indentation relative to first line
                    if len(lines) > 1:
                        for line in lines[1:]:
                            if line.strip():  # Skip empty lines
                                processed_lines.append(line)
                            else:
                                processed_lines.append('')  # Keep empty lines but don't process
                    
                    # Join lines back together with normalized line endings
                    processed_code = '\n'.join(processed_lines)
                    
                    # Add the processed block code to the overall code
                    if processed_code:
                        code += processed_code + "\n"
        
        # Ensure the code has consistent line endings and no trailing whitespace
        final_code = ""
        for line in code.splitlines():
            # Remove trailing whitespace from each line
            final_code += line.rstrip() + "\n"
        
        # Log the generated code for debugging
        logger.debug(f"Generated code:\n{final_code}")
        logger.debug(f"Code character analysis:")
        for i, char in enumerate(final_code[:100]):  # First 100 chars for brevity
            logger.debug(f"Char {i}: {repr(char)}")
        
        # Emit the generated code
        self.codeChanged.emit(final_code)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events"""
        if event.mimeData().hasFormat("application/x-codeblockeditor-block"):
            # Show visual feedback
            self.container.setStyleSheet("background-color: rgba(52, 152, 219, 0.1); border: 2px dashed rgba(52, 152, 219, 0.4);")
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events"""
        if event.mimeData().hasFormat("application/x-codeblockeditor-block"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events"""
        # Reset visual feedback
        self.container.setStyleSheet("")
        event.accept()
    
    def dropEvent(self, event):
        """Handle drop events"""
        if event.mimeData().hasFormat("application/x-codeblockeditor-block"):
            # Get the data from the drag
            mime_data = event.mimeData().data("application/x-codeblockeditor-block").data()
            block_data = json.loads(mime_data.decode('utf-8'))
            
            # Get the position relative to the container
            drop_position = self.container.mapFrom(self, event.pos())
            
            # Apply grid snapping if enabled
            if self.snap_to_grid:
                grid_size = self.grid_size
                x = int(drop_position.x() / grid_size) * grid_size
                y = int(drop_position.y() / grid_size) * grid_size
                drop_position = QPoint(x, y)
            
            # Check if this is a new block or an existing one being moved
            if block_data.get("new_block", False):
                # Create a new block
                block_type = block_data.get("block_type", "")
                if block_type:
                    self.add_block(block_type, drop_position)
            else:
                # Existing block being moved
                block_id = block_data.get("id")
                if block_id:
                    # Find the block with this ID
                    moved_block = None
                    for block in self.blocks:
                        if id(block) == block_id:
                            moved_block = block
                            break
                    
                    if moved_block:
                        # Move the block to the new position
                        moved_block.move(drop_position)
                        
                        # Notify about the move
                        moved_block.moved.emit(drop_position)
                        
                        # Handle block reordering based on Y position
                        self.reorder_blocks_after_move(moved_block)
            
            # Reset visual feedback
            self.container.setStyleSheet("")
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def reorder_blocks_after_move(self, moved_block):
        """
        Reorder blocks based on their vertical position after a block has been moved.
        
        Args:
            moved_block: The block that was just moved
        """
        # Skip if the block is in a slot or has a parent
        if moved_block.parent_slot or not isinstance(moved_block.parent(), WorkspaceContainer):
            return
            
        # Sort blocks by Y position
        self.blocks.sort(key=lambda b: b.y() if not b.parent_slot else float('inf'))
        
        # Update the code after reordering
        self.update_code()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Delete selected blocks
        if event.key() == Qt.Key_Delete and self.selected_blocks:
            blocks_to_remove = list(self.selected_blocks)
            for block in blocks_to_remove:
                self.remove_block(block)
            self.selected_blocks.clear()
        
        # Copy selected blocks
        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            self.clipboard = list(self.selected_blocks)
        
        # Paste blocks
        elif event.key() == Qt.Key_V and event.modifiers() & Qt.ControlModifier:
            # Implement block duplication and pasting
            pass
        
        super().keyPressEvent(event)
    
    def save_workspace(self) -> Dict[str, Any]:
        """
        Save the workspace to a dictionary.
        
        Returns:
            Dictionary representation of the workspace
        """
        data = {
            "blocks": []
        }
        
        # Save only top-level blocks (not in slots)
        for block in self.blocks:
            if not block.parent_slot:
                block_data = block.to_json()
                # Add position
                block_data["position"] = {
                    "x": block.pos().x(),
                    "y": block.pos().y()
                }
                data["blocks"].append(block_data)
        
        return data
    
    def load_workspace(self, data: Dict[str, Any]) -> bool:
        """
        Load the workspace from a dictionary.
        
        Args:
            data: Dictionary representation of the workspace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear existing workspace
            self.clear_workspace()
            
            # Load blocks
            for block_data in data.get("blocks", []):
                block_type = block_data.get("block_type", "")
                position_data = block_data.get("position", {})
                position = QPoint(position_data.get("x", 0), position_data.get("y", 0))
                
                # Create the block
                block = self.add_block(block_type, position)
                
                # Set input values and nested blocks
                # This would be a more complex implementation in practice
                
            # Update the generated code
            self.update_code()
            
            return True
        except Exception as e:
            logger.error(f"Error loading workspace: {e}")
            return False

    def handle_slot_drop(self, slot, block_data, drop_type):
        """
        Handle drops in input slots.
        
        Args:
            slot: The BlockInputSlot that received the drop
            block_data: Data about the dropped block
            drop_type: 'new' for blocks from palette, 'existing' for moved blocks
        """
        if drop_type == "new":
            # This is a new block from the palette
            block_type = block_data.get("block_type", "")
            if block_type:
                # Create a new block
                block = self.add_block(block_type)
                if block:
                    # If successfully created, remove from main workspace tracking
                    # and add to the slot
                    self.blocks.remove(block)
                    slot.add_block(block)
                    self.update_code()
        
        elif drop_type == "existing":
            # This is an existing block being moved
            block_id = block_data.get("id")
            
            # Find the block with this ID
            for block in self.blocks:
                if id(block) == block_id:
                    # Add the block to this slot
                    if self.add_block_to_slot(block, slot):
                        self.update_code()
                    break

    def contextMenuEvent(self, event):
        """Show context menu for workspace operations"""
        menu = QMenu(self)
        
        # Global actions
        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.paste_blocks)
        menu.addAction(paste_action)
        
        # Workspace view options
        view_menu = menu.addMenu("View Options")
        
        # Toggle grid snap
        snap_action = QAction("Snap to Grid", self)
        snap_action.setCheckable(True)
        snap_action.setChecked(self.snap_to_grid)
        snap_action.triggered.connect(self.toggle_snap_to_grid)
        view_menu.addAction(snap_action)
        
        # Toggle alignment guides
        guides_action = QAction("Show Alignment Guides", self)
        guides_action.setCheckable(True)
        guides_action.setChecked(self.show_alignment_guides)
        guides_action.triggered.connect(self.toggle_alignment_guides)
        view_menu.addAction(guides_action)
        
        # Save/load actions
        menu.addSeparator()
        save_action = QAction("Save Workspace...", self)
        # save_action.triggered.connect(self.save_workspace_dialog)
        menu.addAction(save_action)
        
        load_action = QAction("Load Workspace...", self)
        # load_action.triggered.connect(self.load_workspace_dialog)
        menu.addAction(load_action)
        
        # Import actions
        menu.addSeparator()
        import_action = QAction("Import Blocks...", self)
        # import_action.triggered.connect(self.import_blocks_dialog)
        menu.addAction(import_action)
        
        menu.exec_(event.globalPos())
    
    def toggle_snap_to_grid(self, checked):
        """Toggle snap to grid setting"""
        self.snap_to_grid = checked
        settings.set_app_setting("blocks", "snap_to_grid", checked)
        
        # Update the container to reflect the change
        self.container.update()
    
    def toggle_alignment_guides(self, checked):
        """Toggle alignment guides setting"""
        self.show_alignment_guides = checked
        settings.set_app_setting("blocks", "show_alignment_guides", checked)
        
        # Update the container to reflect the change
        self.container.update()

    def scroll_to_block(self, block):
        """
        Scroll the workspace to make the specified block visible.
        
        Args:
            block: The block to scroll to
        """
        if not block or not block in self.blocks:
            return
            
        # Calculate block position relative to the viewport
        block_pos = block.mapTo(self.container, QPoint(0, 0))
        block_rect = QRect(block_pos, block.size())
        
        # Adjust scrollbars to make the block visible
        h_scroll = self.horizontalScrollBar()
        v_scroll = self.verticalScrollBar()
        
        # Check if block is out of view
        viewport_rect = self.viewport().rect()
        
        # Calculate new scroll positions if needed
        if block_rect.left() < viewport_rect.left():
            h_scroll.setValue(h_scroll.value() + block_rect.left() - viewport_rect.left() - 20)
        elif block_rect.right() > viewport_rect.right():
            h_scroll.setValue(h_scroll.value() + block_rect.right() - viewport_rect.right() + 20)
            
        if block_rect.top() < viewport_rect.top():
            v_scroll.setValue(v_scroll.value() + block_rect.top() - viewport_rect.top() - 20)
        elif block_rect.bottom() > viewport_rect.bottom():
            v_scroll.setValue(v_scroll.value() + block_rect.bottom() - viewport_rect.bottom() + 20)
    
    def select_block(self, block):
        """
        Select a specific block in the workspace.
        
        Args:
            block: The block to select
        """
        if not block or not block in self.blocks:
            return
            
        # Deselect all other blocks
        for b in self.selected_blocks:
            if b != block:
                b.set_selected(False)
                
        # Select the specified block
        block.set_selected(True)
        self.selected_blocks = {block}
        
        # Ensure the block is visible
        self.scroll_to_block(block)

class WorkspaceContainer(QWidget):
    """
    Container widget for the workspace that holds blocks and handles drawing
    grid lines and other workspace visuals.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Initial size should be large enough for scrolling
        self.setMinimumSize(2000, 2000)
        
        # Make the container adapt to content
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Setup the layout - use FlowLayout for more flexible block positioning
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(0)
        
        # Track blocks for auto-sizing
        self.blocks_positions = {}  # Store positions of blocks
        
        # Allow dropping
        self.setAcceptDrops(True)
    
    def resizeEvent(self, event):
        """Handle resize events to ensure proper sizing"""
        super().resizeEvent(event)
        
        # Check if we need to expand the container based on block positions
        self.updateContainerSize()
    
    def updateContainerSize(self):
        """Update container size based on block positions"""
        if not hasattr(self, 'parent') or not self.parent() or not hasattr(self.parent(), 'blocks'):
            return
            
        blocks = self.parent().blocks
        if not blocks:
            return
            
        # Find the furthest block
        max_x = 0
        max_y = 0
        
        for block in blocks:
            pos = block.pos()
            size = block.size()
            max_x = max(max_x, pos.x() + size.width())
            max_y = max(max_y, pos.y() + size.height())
        
        # Add some padding
        max_x += 100
        max_y += 100
        
        # Update minimum size if needed
        current_size = self.size()
        if max_x > current_size.width() or max_y > current_size.height():
            self.setMinimumSize(max(2000, max_x), max(2000, max_y))
    
    def paintEvent(self, event):
        """Custom paint event to draw grid and other workspace visuals"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)  # No antialiasing for crisp grid
        
        # Fill background
        theme = settings.get_current_theme()
        background_color = theme.get("background_color", "#f5f5f5")
        painter.fillRect(self.rect(), QColor(background_color))
        
        # Check if grid should be shown
        snap_to_grid = settings.get_app_setting("blocks", "snap_to_grid", default=True)
        if not snap_to_grid:
            return
        
        # Get grid size from settings
        grid_size = settings.get_app_setting("blocks", "grid_size", default=20)
        
        # Get theme colors
        border_color = theme.get("border_color", "#dddddd")
        grid_color = QColor(border_color)
        grid_color.setAlpha(30)  # Semi-transparent
        
        # Create a pen for the grid
        grid_pen = QPen(grid_color, 1, Qt.DotLine)
        painter.setPen(grid_pen)
        
        # Get the visible rect (either the whole workspace or just what's visible)
        visible_rect = self.rect()
        if isinstance(self.parent(), QScrollArea):
            # If parent is a scroll area, get the viewport rect
            viewport = self.parent().viewport().rect()
            scroll_pos = self.parent().horizontalScrollBar().value(), self.parent().verticalScrollBar().value()
            visible_rect = QRect(scroll_pos[0], scroll_pos[1], viewport.width(), viewport.height())
        
        # Draw the minor grid lines
        start_y = (visible_rect.top() // grid_size) * grid_size
        end_y = ((visible_rect.bottom() // grid_size) + 1) * grid_size
        
        start_x = (visible_rect.left() // grid_size) * grid_size
        end_x = ((visible_rect.right() // grid_size) + 1) * grid_size
        
        for y in range(start_y, end_y, grid_size):
            painter.drawLine(visible_rect.left(), y, visible_rect.right(), y)
        
        for x in range(start_x, end_x, grid_size):
            painter.drawLine(x, visible_rect.top(), x, visible_rect.bottom())
        
        # Draw major grid lines (every 5 minor lines)
        major_grid_color = QColor(border_color)
        major_grid_color.setAlpha(60)
        major_grid_pen = QPen(major_grid_color, 1, Qt.SolidLine)
        painter.setPen(major_grid_pen)
        
        major_size = grid_size * 5
        start_y = (visible_rect.top() // major_size) * major_size
        end_y = ((visible_rect.bottom() // major_size) + 1) * major_size
        
        start_x = (visible_rect.left() // major_size) * major_size
        end_x = ((visible_rect.right() // major_size) + 1) * major_size
        
        for y in range(start_y, end_y, major_size):
            painter.drawLine(visible_rect.left(), y, visible_rect.right(), y)
        
        for x in range(start_x, end_x, major_size):
            painter.drawLine(x, visible_rect.top(), x, visible_rect.bottom())
    
    def dragEnterEvent(self, event):
        """Forward drag enter events to parent workspace"""
        if self.parent():
            self.parent().dragEnterEvent(event)
        else:
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        """Forward drag move events to parent workspace"""
        if self.parent():
            self.parent().dragMoveEvent(event)
        else:
            super().dragMoveEvent(event)
    
    def dropEvent(self, event):
        """Forward drop events to parent workspace"""
        if self.parent():
            self.parent().dropEvent(event)
        else:
            super().dropEvent(event) 