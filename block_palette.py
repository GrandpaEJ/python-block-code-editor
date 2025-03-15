import json
import logging
from typing import Dict, List, Any, Optional

from PyQt5.QtCore import Qt, QMimeData, QSize, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QDrag, QFont, QLinearGradient, QPainterPath, QBrush, QPen
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
                           QHBoxLayout, QSizePolicy, QApplication, QGroupBox)

from settings_loader import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('block_palette')

class BlockPaletteItem(QFrame):
    """
    A draggable item representing a block type in the palette.
    """
    def __init__(self, parent=None, block_type: str = "", block_data: Dict[str, Any] = None):
        super().__init__(parent)
        self.block_type = block_type
        self.block_data = block_data or {}
        self.drag_start_position = None
        
        # Get color from block data
        color_def = self.block_data.get("color", [100, 100, 100])
        if isinstance(color_def, list) and len(color_def) >= 3:
            self.color = QColor(*color_def)
        else:
            self.color = QColor(100, 100, 100)
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI for the palette item"""
        self.setMinimumHeight(30)
        self.setMaximumHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.OpenHandCursor)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        
        # Label with adaptive text
        label = QLabel(self.block_type)
        label.setStyleSheet("color: white; font-weight: bold;")
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        label.setWordWrap(True)  # Allow wrapping for long names
        layout.addWidget(label)
        
        # Show what type of inputs, if any
        inputs = self.block_data.get("inputs", [])
        if inputs:
            input_names = [input_def.get("name", "") for input_def in inputs]
            input_text = ", ".join(input_names)
            input_label = QLabel(f"({input_text})")
            input_label.setStyleSheet("color: rgba(255, 255, 255, 180); font-style: italic;")
            input_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            input_label.setWordWrap(True)  # Allow wrapping
            layout.addWidget(input_label)
        
        # Add stretches to keep content left-aligned
        layout.addStretch()
    
    def sizeHint(self) -> QSize:
        """Default size for the palette item that adapts to content"""
        width = self.parent().width() if self.parent() else 200
        return QSize(width, 30)
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self.drag_start_position = event.pos()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for dragging"""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.OpenHandCursor)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move to start drag operation"""
        if not (event.buttons() & Qt.LeftButton) or not self.drag_start_position:
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # Start drag
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Prepare data for the drag operation
        block_data = {
            "block_type": self.block_type,
            "new_block": True,  # Flag to indicate this is a new block to be created
            "category": self.block_data.get("category", ""),
            "color": self.block_data.get("color", [100, 100, 100])
        }
        mime_data.setData("application/x-codeblockeditor-block", json.dumps(block_data).encode('utf-8'))
        
        drag.setMimeData(mime_data)
        
        # Create a preview image for dragging
        pixmap = self.grab()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 180))
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Reset cursor before starting drag
        self.setCursor(Qt.OpenHandCursor)
        
        # Execute the drag - use CopyAction since we're creating a new block
        result = drag.exec_(Qt.CopyAction)
    
    def paintEvent(self, event):
        """Custom paint for visual appearance"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rounded rectangle path
        rect = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        path = QPainterPath()
        
        # Use block_rounding setting
        rounding = settings.get_app_setting("blocks", "block_rounding", default=5)
        path.addRoundedRect(rect, rounding, rounding)
        
        # Gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        base_color = self.color
        lighter_color = QColor(base_color)
        lighter_color.setAlpha(230)
        
        gradient.setColorAt(0, lighter_color)
        gradient.setColorAt(1, base_color)
        
        # Fill with gradient
        painter.fillPath(path, gradient)
        
        # Draw border
        painter.setPen(QPen(base_color.darker(120), 1))
        painter.drawPath(path)
        
        # Let the normal rendering continue for the content
        super().paintEvent(event)


class BlockCategory(QGroupBox):
    """
    A collapsible category of blocks in the palette.
    """
    def __init__(self, parent=None, category_name: str = "", blocks: Dict[str, Dict[str, Any]] = None):
        super().__init__(parent)
        self.category_name = category_name
        self.blocks = blocks or {}
        
        # Make it responsive
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Initialize UI
        self.init_ui()
        
        # Add blocks to the category
        self.add_blocks()
    
    def init_ui(self):
        """Initialize the category UI"""
        self.setTitle(self.category_name)
        self.setCheckable(True)
        self.setChecked(self.is_expanded())
        
        # Check for category expansion setting
        self.setChecked(settings.get_app_setting(
            "blocks", "categories_expanded", self.category_name, default=True))
        
        # Connect the toggled signal to update settings
        self.toggled.connect(self.on_toggle)
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 15, 5, 5)
        self.layout.setSpacing(5)
    
    def is_expanded(self) -> bool:
        """Check if this category should be expanded by default"""
        # Get from settings
        return settings.get_app_setting(
            "blocks", "categories_expanded", self.category_name, default=True)
    
    def on_toggle(self, checked: bool):
        """Handle category expansion toggling"""
        # Update the visibility of child widgets
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.setVisible(checked)
                
        # Update settings
        settings.set_app_setting("blocks", "categories_expanded", self.category_name, checked)
    
    def add_blocks(self):
        """Add block items to this category"""
        for block_type, block_data in self.blocks.items():
            item = BlockPaletteItem(self, block_type, block_data)
            self.layout.addWidget(item)
            
            # Set initial visibility based on expanded state
            item.setVisible(self.isChecked())
        
        # Add a stretch at the end to keep items at the top
        self.layout.addStretch()


class BlockPalette(QScrollArea):
    """
    A panel containing all available block types organized by categories.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = {}  # Dict of category name -> BlockCategory widget
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI for the block palette"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set width based on settings with min/max constraints
        palette_width = settings.get_app_setting("ui", "block_palette_width", default=250)
        self.setMinimumWidth(palette_width)
        self.setMaximumWidth(400)  # Allow some flexibility but cap the maximum width
        
        # Main container widget
        self.container = QWidget(self)
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setWidget(self.container)
        
        # Layout
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # Set style from current theme
        self.update_style()
        
        # Header label
        self.header = QLabel("Block Palette")
        self.header.setAlignment(Qt.AlignCenter)
        font = self.header.font()
        font.setPointSize(12)
        font.setBold(True)
        self.header.setFont(font)
        self.layout.addWidget(self.header)
        
        # Load blocks from settings
        self.load_blocks()
    
    def update_style(self):
        """Update the palette style from theme settings"""
        theme = settings.get_current_theme()
        panel_color = theme.get("panel_color", "#ffffff")
        text_color = theme.get("text_color", "#333333")
        border_color = theme.get("border_color", "#dddddd")
        
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {panel_color};
                border: 1px solid {border_color};
                border-radius: 0px;
            }}
            QLabel {{
                color: {text_color};
            }}
            QGroupBox {{
                background-color: {panel_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }}
        """)
        
    def resizeEvent(self, event):
        """Handle resize events to update layout"""
        super().resizeEvent(event)
        
        # Update child layouts if needed
        if hasattr(self, 'container'):
            self.container.updateGeometry()
            
    def load_blocks(self):
        """Load and organize blocks from settings"""
        # Get all block definitions
        block_definitions = settings.get_all_block_definitions()
        
        # Organize blocks by category
        categorized_blocks = {}
        
        for block_type, block_data in block_definitions.items():
            # Get the category from block data, default to "Basic"
            category = block_data.get("category", "Basic")
            
            if category not in categorized_blocks:
                categorized_blocks[category] = {}
            
            categorized_blocks[category][block_type] = block_data
        
        # Get ordered categories from settings
        default_categories = settings.get_app_setting("blocks", "categories", default=[
            "Basic", "Values", "Variables", "Math", "Logic", "Control", "Functions", "Data", "Advanced"
        ])
        
        # Create category widgets in the specified order
        for category in default_categories:
            if category in categorized_blocks:
                category_widget = BlockCategory(self.container, category, categorized_blocks[category])
                self.layout.addWidget(category_widget)
                self.categories[category] = category_widget
        
        # Add any remaining categories not in the default list
        for category, blocks in categorized_blocks.items():
            if category not in default_categories:
                category_widget = BlockCategory(self.container, category, blocks)
                self.layout.addWidget(category_widget)
                self.categories[category] = category_widget
        
        # Add stretch at the end to keep categories at the top
        self.layout.addStretch()
    
    def reload_blocks(self):
        """Reload blocks from settings (e.g., if block definitions changed)"""
        # Clear existing categories
        while self.layout.count() > 0:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Reload the header
        self.header = QLabel("Block Palette")
        self.header.setAlignment(Qt.AlignCenter)
        font = self.header.font()
        font.setPointSize(12)
        font.setBold(True)
        self.header.setFont(font)
        self.layout.addWidget(self.header)
        
        # Reload blocks
        self.load_blocks()