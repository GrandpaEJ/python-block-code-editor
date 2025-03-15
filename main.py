#!/usr/bin/env python3
import sys
import os
import logging
import json
import time
from typing import Dict, Any, Optional

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QFileDialog,
                           QSplitter, QMessageBox, QStatusBar, QToolBar,
                           QVBoxLayout, QHBoxLayout, QWidget, QLabel, QShortcut)

from settings_loader import settings
from block_palette import BlockPalette
from workspace_widget import WorkspaceWidget
from output_panel import OutputPanel
from code_tree import CodeTree
from utils import ensure_directory_exists, format_code

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

class MainWindow(QMainWindow):
    """
    Main application window for the Python Block Code Editor.
    Assembles all components and manages the overall application flow.
    """
    def __init__(self):
        super().__init__()
        
        # State management
        self.current_file_path = None
        self.code_changed_since_save = False
        
        # Initialize UI
        self.init_ui()
        
        # Setup autosave if enabled
        self.setup_autosave()
        
        # Setup settings check timer
        self.setup_settings_check_timer()
    
    def init_ui(self):
        """Initialize the main window UI"""
        # Set window properties
        self.setWindowTitle(settings.get_app_setting("application", "name", default="Python Block Code Editor"))
        self.resize(1200, 800)
        
        # Create menus
        self.create_menus()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Create block palette
        self.block_palette = BlockPalette()
        self.main_splitter.addWidget(self.block_palette)
        
        # Create code tree (new component)
        self.code_tree = CodeTree()
        self.code_tree.blockSelected.connect(self.on_tree_block_selected)
        self.main_splitter.addWidget(self.code_tree)
        
        # Create right side container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create workspace and output splitter
        self.workspace_output_splitter = QSplitter(Qt.Vertical)
        right_layout.addWidget(self.workspace_output_splitter)
        
        # Create workspace
        self.workspace = WorkspaceWidget()
        self.workspace.codeChanged.connect(self.on_code_changed)
        self.workspace_output_splitter.addWidget(self.workspace)
        
        # Create output panel
        self.output_panel = OutputPanel()
        self.workspace_output_splitter.addWidget(self.output_panel)
        
        # Add right container to main splitter
        self.main_splitter.addWidget(right_container)
        
        # Configure splitter sizes (left section smaller, right section larger)
        self.main_splitter.setSizes([200, 200, 800])
        self.workspace_output_splitter.setSizes([600, 200])
        
        # Set style from current theme
        self.update_style()
        
        # Set up shortcuts
        self.setup_shortcuts()
        
        # Show the window
        self.show()
    
    def create_menus(self):
        """Create the application menu bar"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # New
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_new)
        file_menu.addAction(new_action)
        
        # Open
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open)
        file_menu.addAction(open_action)
        
        # Save
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.on_save)
        file_menu.addAction(self.save_action)
        
        # Save As
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.on_save_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = self.menuBar().addMenu("&Edit")
        
        # Clear workspace
        clear_action = QAction("&Clear Workspace", self)
        clear_action.triggered.connect(self.on_clear_workspace)
        edit_menu.addAction(clear_action)
        
        # Run menu
        run_menu = self.menuBar().addMenu("&Run")
        
        # Run code
        run_action = QAction("&Run", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.on_run)
        run_menu.addAction(run_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        # Toggle theme
        theme_action = QAction("Toggle &Theme", self)
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the main toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # Add toolbar actions
        # New
        new_action = QAction("New", self)
        new_action.triggered.connect(self.on_new)
        self.toolbar.addAction(new_action)
        
        # Open
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.on_open)
        self.toolbar.addAction(open_action)
        
        # Save
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.on_save)
        self.toolbar.addAction(save_action)
        
        self.toolbar.addSeparator()
        
        # Run
        run_action = QAction("Run", self)
        run_action.triggered.connect(self.on_run)
        self.toolbar.addAction(run_action)
        
        self.toolbar.addSeparator()
        
        # Clear workspace
        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self.on_clear_workspace)
        self.toolbar.addAction(clear_action)
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Register the shortcuts from settings
        shortcut_settings = settings.get_app_setting("shortcuts", default={})
        
        for action_name, shortcut_key in shortcut_settings.items():
            if action_name == "run":
                shortcut = QShortcut(QKeySequence(shortcut_key), self)
                shortcut.activated.connect(self.on_run)
            elif action_name == "save":
                shortcut = QShortcut(QKeySequence(shortcut_key), self)
                shortcut.activated.connect(self.on_save)
            elif action_name == "load":
                shortcut = QShortcut(QKeySequence(shortcut_key), self)
                shortcut.activated.connect(self.on_open)
            elif action_name == "new":
                shortcut = QShortcut(QKeySequence(shortcut_key), self)
                shortcut.activated.connect(self.on_new)
            elif action_name == "toggle_palette":
                shortcut = QShortcut(QKeySequence(shortcut_key), self)
                shortcut.activated.connect(self.toggle_palette)
            elif action_name == "toggle_output":
                shortcut = QShortcut(QKeySequence(shortcut_key), self)
                shortcut.activated.connect(self.toggle_output)
    
    def update_style(self):
        """Update the application style based on the current theme"""
        theme = settings.get_current_theme()
        
        # Set the application style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme.get("background_color", "#f5f5f5")};
                color: {theme.get("text_color", "#333333")};
            }}
            QMenuBar {{
                background-color: {theme.get("panel_color", "#ffffff")};
                color: {theme.get("text_color", "#333333")};
                border-bottom: 1px solid {theme.get("border_color", "#dddddd")};
            }}
            QMenuBar::item:selected {{
                background-color: {theme.get("accent_color", "#3498db")};
                color: white;
            }}
            QMenu {{
                background-color: {theme.get("panel_color", "#ffffff")};
                color: {theme.get("text_color", "#333333")};
                border: 1px solid {theme.get("border_color", "#dddddd")};
            }}
            QMenu::item:selected {{
                background-color: {theme.get("accent_color", "#3498db")};
                color: white;
            }}
            QToolBar {{
                background-color: {theme.get("panel_color", "#ffffff")};
                border-bottom: 1px solid {theme.get("border_color", "#dddddd")};
            }}
            QStatusBar {{
                background-color: {theme.get("panel_color", "#ffffff")};
                color: {theme.get("text_color", "#333333")};
                border-top: 1px solid {theme.get("border_color", "#dddddd")};
            }}
            QSplitter::handle {{
                background-color: {theme.get("border_color", "#dddddd")};
            }}
        """)
        
        # Update the style of child widgets
        if hasattr(self, "workspace"):
            self.workspace.update_style()
        if hasattr(self, "block_palette"):
            self.block_palette.update_style()
        if hasattr(self, "output_panel"):
            self.output_panel.update_style()
    
    def setup_autosave(self):
        """Set up autosave if enabled in settings"""
        autosave_interval = settings.get_app_setting("application", "auto_save_interval", default=0)
        
        if autosave_interval > 0:
            self.autosave_timer = QTimer(self)
            self.autosave_timer.timeout.connect(self.on_autosave)
            self.autosave_timer.start(autosave_interval * 1000)  # Convert to milliseconds
    
    def setup_settings_check_timer(self):
        """Set up timer to check for settings file changes"""
        # Check for settings changes every 5 seconds
        self.settings_check_timer = QTimer(self)
        self.settings_check_timer.timeout.connect(self.check_settings_changes)
        self.settings_check_timer.start(5000)
    
    def check_settings_changes(self):
        """Check if settings files have changed and reload if needed"""
        if settings.check_for_changes():
            # Update UI components that depend on settings
            self.update_style()
            if hasattr(self, "block_palette"):
                self.block_palette.reload_blocks()
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_theme = settings.get_app_setting("ui", "theme", default="light")
        
        # Toggle theme
        new_theme = "dark" if current_theme == "light" else "light"
        
        # This is just a temporary change for the session
        # A more complete implementation would update the settings file
        settings.app_settings["ui"]["theme"] = new_theme
        
        # Update UI
        self.update_style()
    
    def toggle_palette(self):
        """Toggle the visibility of the block palette"""
        palette_visible = not self.block_palette.isVisible()
        self.block_palette.setVisible(palette_visible)
    
    def toggle_output(self):
        """Toggle the visibility of the output panel"""
        output_visible = not self.output_panel.isVisible()
        self.output_panel.setVisible(output_visible)
    
    def on_code_changed(self, code: str):
        """Handle code changed event"""
        self.code_changed_since_save = True
        
        # Update the output panel with the new code
        self.output_panel.set_code_preview(code)
        
        # Update the code tree
        self.update_code_tree()
        
        # Update window title to show unsaved changes
        self.update_window_title()
    
    def update_code_tree(self):
        """Update the code tree to reflect current workspace blocks"""
        # Pass the blocks from workspace to code tree for rendering
        if hasattr(self.workspace, 'blocks'):
            # Log for debugging
            logger.info(f"Updating code tree with {len(self.workspace.blocks)} blocks")
            
            # Count top-level blocks (not in slots)
            top_level_blocks = [b for b in self.workspace.blocks if not hasattr(b, 'parent_slot') or not b.parent_slot]
            logger.info(f"Top-level blocks: {len(top_level_blocks)}")
            
            # Log block details for debugging
            for i, block in enumerate(self.workspace.blocks):
                if hasattr(block, 'get_debug_info'):
                    logger.debug(f"Block {i}: {block.get_debug_info()}")
                else:
                    logger.debug(f"Block {i}: {block.block_type} (in slot: {hasattr(block, 'parent_slot') and block.parent_slot is not None})")
            
            # Update the tree with all blocks for now, we'll filter in the tree component
            self.code_tree.update_from_blocks(self.workspace.blocks)
            
            # Force immediate update
            self.code_tree.repaint()
    
    def on_tree_block_selected(self, block_id: int):
        """Handle block selected from tree view"""
        # Find the block in the workspace
        for block in self.workspace.blocks:
            if id(block) == block_id:
                # Scroll to the block
                self.workspace.scroll_to_block(block)
                # Select the block
                self.workspace.select_block(block)
                break
    
    def on_new(self):
        """Create a new project"""
        if self.check_unsaved_changes():
            self.workspace.clear_workspace()
            self.current_file_path = None
            self.code_changed_since_save = False
            self.update_window_title()
            self.statusBar.showMessage("New project created")
    
    def on_open(self):
        """Open a project file"""
        if not self.check_unsaved_changes():
            return
        
        # Get default directory from settings
        default_dir = settings.get_app_setting("application", "default_save_path", default="./projects")
        ensure_directory_exists(default_dir)
        
        # Show file dialog
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", default_dir,
            "Python Block Code Projects (*.pbcp);;All Files (*)", options=options)
        
        if file_path:
            self.load_project(file_path)
    
    def on_save(self):
        """Save the current project"""
        if self.current_file_path:
            self.save_project(self.current_file_path)
        else:
            self.on_save_as()
    
    def on_save_as(self):
        """Save the project to a new file"""
        # Get default directory from settings
        default_dir = settings.get_app_setting("application", "default_save_path", default="./projects")
        ensure_directory_exists(default_dir)
        
        # Show file dialog
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", default_dir,
            "Python Block Code Projects (*.pbcp);;All Files (*)", options=options)
        
        if file_path:
            # Add extension if not present
            if not file_path.endswith(".pbcp"):
                file_path += ".pbcp"
            
            self.save_project(file_path)
    
    def on_autosave(self):
        """Handle autosave timer event"""
        if self.code_changed_since_save and self.current_file_path:
            self.save_project(self.current_file_path)
            logger.info(f"Autosaved project to {self.current_file_path}")
    
    def on_run(self):
        """Run the generated Python code with comprehensive error handling"""
        # Get the current code
        code = self.output_panel.get_code_preview()
        
        if not code.strip():
            self.statusBar.showMessage("No code to run")
            return
        
        try:
            # Clear previous output
            self.output_panel.clear_execution_output()
            
            # Add a heading for the execution
            self.output_panel.set_execution_output("Executing code...\n\n")
            
            # Clean the code - ensure no invisible whitespace or BOM markers
            cleaned_code = ""
            for line in code.splitlines():
                # Only keep lines with actual content
                if line.strip():
                    # Remove any leading whitespace that might cause indentation issues
                    cleaned_line = line.lstrip()
                    cleaned_code += cleaned_line + "\n"
                else:
                    # Preserve empty lines for structure
                    cleaned_code += "\n"
            
            # Debug output - show exactly what we're executing
            logger.debug(f"Code to be executed (showing characters):")
            for i, char in enumerate(cleaned_code[:100]):  # First 100 chars for brevity
                logger.debug(f"Char {i}: {repr(char)}")
            
            # Capture stdout and stderr
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            # Set timeout from settings
            timeout = settings.get_app_setting("execution", "timeout_seconds", default=5)
            
            # Use a safety wrapper to prevent dangerous operations in executed code
            safety_checks = [
                "import os",
                "import sys",
                "import subprocess",
                "open(",
                "__import__",
                "eval(",
                "exec(",
                "globals()",
                "locals()",
                "os.system",
                "os.popen"
            ]
            
            # Check code for potentially unsafe operations
            has_unsafe_code = any(check in cleaned_code for check in safety_checks)
            if has_unsafe_code:
                logger.warning("Potentially unsafe code detected")
                warning_msg = "⚠️ Warning: Code contains potentially unsafe operations. Running in restricted mode.\n\n"
                self.output_panel.set_execution_output(warning_msg)
                
                # Create a safer execution environment
                safe_globals = {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'range': range,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'input': lambda prompt: prompt  # Mock input to avoid hanging
                }
            else:
                # Standard execution environment
                safe_globals = {
                    'input': lambda prompt: prompt  # Mock input to avoid hanging
                }
                
            # Run the code with timeout
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            start_time = time.time()
            
            try:
                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                    # Execute with timeout using simple approach
                    exec_locals = {}
                    exec(cleaned_code, safe_globals, exec_locals)
                    
                    # Add any variables defined to the output for reference
                    variables = {k: v for k, v in exec_locals.items() 
                                if not k.startswith('_') and k != 'builtins'}
            except SyntaxError as se:
                # Provide helpful feedback for syntax errors
                line_num = se.lineno if hasattr(se, 'lineno') else '?'
                col_num = se.offset if hasattr(se, 'offset') else '?'
                error_msg = f"❌ Syntax Error at line {line_num}, column {col_num}: {str(se)}\n"
                
                # Highlight the error line
                if hasattr(se, 'lineno') and se.lineno is not None:
                    lines = cleaned_code.splitlines()
                    if 1 <= se.lineno <= len(lines):
                        error_line = lines[se.lineno - 1]
                        error_msg += f"\nError in this line:\n{error_line}\n"
                        if hasattr(se, 'offset') and se.offset:
                            error_msg += " " * (se.offset - 1) + "^\n"
                
                self.output_panel.set_execution_output(error_msg)
                self.statusBar.showMessage(f"Syntax error at line {line_num}")
                return
            except IndentationError as ie:
                # Special handling for indentation errors
                line_num = ie.lineno if hasattr(ie, 'lineno') else '?'
                error_msg = f"❌ Indentation Error at line {line_num}: {str(ie)}\n"
                
                # Highlight the error line
                if hasattr(ie, 'lineno') and ie.lineno is not None:
                    lines = cleaned_code.splitlines()
                    if 1 <= ie.lineno <= len(lines):
                        error_line = lines[ie.lineno - 1]
                        error_msg += f"\nError in this line:\n{error_line}\n"
                
                self.output_panel.set_execution_output(error_msg)
                self.statusBar.showMessage(f"Indentation error at line {line_num}")
                return
            except Exception as e:
                # Handle other execution errors
                error_msg = f"❌ Error executing code: {str(e)}\n"
                self.output_panel.set_execution_output(error_msg)
                self.statusBar.showMessage("Error executing code")
                return
            
            execution_time = time.time() - start_time
            
            # Get output and errors
            output = output_buffer.getvalue()
            errors = error_buffer.getvalue()
            
            # Prepare the complete output
            result = ""
            if output:
                result += "Output:\n"
                result += output + "\n"
            
            if errors:
                result += "Errors:\n"
                result += errors + "\n"
            
            # Add variables section to show what was defined
            if 'variables' in locals() and variables:
                result += "\nVariables:\n"
                for var_name, var_value in variables.items():
                    # Format the value for display, showing type information
                    value_str = repr(var_value)
                    if len(value_str) > 100:
                        value_str = value_str[:97] + "..."
                    var_type = type(var_value).__name__
                    result += f"{var_name} ({var_type}): {value_str}\n"
            
            # Add execution time if enabled in settings
            if settings.get_app_setting("execution", "show_execution_time", default=True):
                result += f"\nExecution time: {execution_time:.2f} seconds"
            
            # Display the result
            self.output_panel.set_execution_output(result)
            
            # Status message
            self.statusBar.showMessage(f"Code executed successfully in {execution_time:.2f} seconds")
            
        except Exception as e:
            # Handle execution errors
            error_message = f"❌ Error executing code: {str(e)}"
            self.output_panel.set_execution_output(error_message)
            self.statusBar.showMessage("Error executing code")
            logger.error(error_message)
            
            # Add more detailed error information for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def on_clear_workspace(self):
        """Clear the workspace"""
        if self.check_unsaved_changes():
            reply = QMessageBox.question(
                self, "Clear Workspace",
                "Are you sure you want to clear the workspace? All blocks will be removed.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.workspace.clear_workspace()
                self.statusBar.showMessage("Workspace cleared")
    
    def on_about(self):
        """Show about dialog"""
        app_name = settings.get_app_setting("application", "name", default="Python Block Code Editor")
        app_version = settings.get_app_setting("application", "version", default="1.0.0")
        
        QMessageBox.about(
            self, f"About {app_name}",
            f"<h2>{app_name} v{app_version}</h2>"
            f"<p>A visual programming environment for Python.</p>"
            f"<p>Create Python programs by dragging and dropping code blocks.</p>"
            f"<p>Developed as an educational tool and programming aid.</p>"
        )
    
    def save_project(self, file_path: str) -> bool:
        """
        Save the current project to a file.
        
        Args:
            file_path: Path to save the project to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create the project data
            project_data = {
                "version": settings.get_app_setting("application", "version", default="1.0.0"),
                "timestamp": time.time(),
                "workspace": self.workspace.save_workspace()
            }
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2)
            
            # Update state
            self.current_file_path = file_path
            self.code_changed_since_save = False
            self.update_window_title()
            
            # Status message
            self.statusBar.showMessage(f"Project saved to {file_path}")
            
            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Error Saving Project",
                f"Failed to save project: {str(e)}"
            )
            logger.error(f"Error saving project to {file_path}: {e}")
            return False
    
    def load_project(self, file_path: str) -> bool:
        """
        Load a project from a file.
        
        Args:
            file_path: Path to load the project from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # Check version compatibility
            file_version = project_data.get("version", "1.0.0")
            app_version = settings.get_app_setting("application", "version", default="1.0.0")
            
            # For now just log a warning if versions don't match
            if file_version != app_version:
                logger.warning(f"Loading project with version {file_version} in app version {app_version}")
            
            # Load the workspace
            workspace_data = project_data.get("workspace", {})
            if not self.workspace.load_workspace(workspace_data):
                raise Exception("Failed to load workspace data")
            
            # Update state
            self.current_file_path = file_path
            self.code_changed_since_save = False
            self.update_window_title()
            
            # Status message
            self.statusBar.showMessage(f"Project loaded from {file_path}")
            
            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Project",
                f"Failed to load project: {str(e)}"
            )
            logger.error(f"Error loading project from {file_path}: {e}")
            return False
    
    def update_window_title(self):
        """Update the window title based on current file and save state"""
        app_name = settings.get_app_setting("application", "name", default="Python Block Code Editor")
        
        if self.current_file_path:
            file_name = os.path.basename(self.current_file_path)
            if self.code_changed_since_save:
                self.setWindowTitle(f"{file_name} * - {app_name}")
            else:
                self.setWindowTitle(f"{file_name} - {app_name}")
        else:
            if self.code_changed_since_save:
                self.setWindowTitle(f"Untitled * - {app_name}")
            else:
                self.setWindowTitle(f"Untitled - {app_name}")
    
    def check_unsaved_changes(self) -> bool:
        """
        Check if there are unsaved changes and prompt the user.
        
        Returns:
            True to continue, False to cancel
        """
        if self.code_changed_since_save:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                return self.on_save()
            elif reply == QMessageBox.Cancel:
                return False
        
        return True
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.check_unsaved_changes():
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point for the application"""
    # Create the application
    app = QApplication(sys.argv)
    app.setApplicationName("Python Block Code Editor")
    
    # Create and show the main window
    window = MainWindow()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 