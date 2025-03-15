import json
import os
import logging
from PyQt5.QtGui import QColor
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('settings_loader')

class SettingsLoader:
    """
    Handles loading and management of application settings from JSON configuration files.
    Supports hot-reloading of settings and provides defaults if settings are missing.
    """
    
    def __init__(self, 
                 app_settings_file: str = 'app_settings.json',
                 block_defs_file: str = 'block_definitions.json',
                 block_caps_file: str = 'block_capabilities.json'):
        """
        Initialize the settings loader with paths to configuration files.
        
        Args:
            app_settings_file: Path to application settings JSON file
            block_defs_file: Path to block definitions JSON file
            block_caps_file: Path to block capabilities JSON file
        """
        self.app_settings_file = app_settings_file
        self.block_defs_file = block_defs_file
        self.block_caps_file = block_caps_file
        
        # Initialize settings containers
        self.app_settings = {}
        self.block_definitions = {}
        self.block_capabilities = {}
        
        # Track file modification times to detect changes
        self.last_modified = {
            app_settings_file: 0,
            block_defs_file: 0,
            block_caps_file: 0
        }
        
        # Load all settings
        self.reload_all()
    
    def reload_all(self) -> None:
        """Reload all settings from their respective files."""
        self.app_settings = self._load_json_file(self.app_settings_file, self._default_app_settings())
        self.block_definitions = self._load_json_file(self.block_defs_file, {})
        self.block_capabilities = self._load_json_file(self.block_caps_file, {"nesting_rules": {}})
    
    def check_for_changes(self) -> bool:
        """
        Check if any configuration files have been modified since last load.
        
        Returns:
            bool: True if any files have changed, False otherwise
        """
        changed = False
        
        for file_path in self.last_modified:
            if os.path.exists(file_path):
                current_mtime = os.path.getmtime(file_path)
                if current_mtime > self.last_modified[file_path]:
                    self.last_modified[file_path] = current_mtime
                    changed = True
        
        if changed:
            self.reload_all()
            logger.info("Settings reloaded due to file changes")
        
        return changed
    
    def get_app_setting(self, *keys: str, default: Any = None) -> Any:
        """
        Retrieve an application setting by navigating through nested dictionaries.
        
        Args:
            *keys: A sequence of keys to navigate the nested dictionaries
            default: Default value to return if setting is not found
            
        Returns:
            The requested setting value or the default if not found
        """
        return self._get_nested_setting(self.app_settings, keys, default)
    
    def get_block_definition(self, block_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the definition for a specific block type.
        
        Args:
            block_type: The type identifier of the block
            
        Returns:
            The block definition dictionary or None if not found
        """
        return self.block_definitions.get(block_type)
    
    def get_all_block_definitions(self) -> Dict[str, Any]:
        """
        Get all block definitions.
        
        Returns:
            Dictionary of all block definitions
        """
        return self.block_definitions
    
    def get_nesting_rules(self, block_type: str, input_name: str) -> Dict[str, list]:
        """
        Get nesting rules for a specific block type and input.
        
        Args:
            block_type: The type of block to get rules for
            input_name: The name of the input slot
            
        Returns:
            Dictionary with 'allowed' and 'denied' lists of block types
        """
        rules = self.block_capabilities.get("nesting_rules", {})
        block_rules = rules.get(block_type, {})
        input_rules = block_rules.get(input_name, {})
        
        return {
            "allowed": input_rules.get("allowed", []),
            "denied": input_rules.get("denied", [])
        }
    
    def is_nesting_allowed(self, parent_block_type: str, parent_input: str, child_block_type: str) -> bool:
        """
        Check if a child block can be nested in a parent block's input.
        
        Args:
            parent_block_type: The type of the parent block
            parent_input: The input slot name in the parent block
            child_block_type: The type of the child block
            
        Returns:
            True if nesting is allowed, False otherwise
        """
        rules = self.get_nesting_rules(parent_block_type, parent_input)
        
        # If the child block type is explicitly denied, return False
        if child_block_type in rules["denied"]:
            return False
        
        # If the allowed list is empty (anything allowed) or contains the child block type, return True
        if not rules["allowed"] or child_block_type in rules["allowed"]:
            return True
            
        return False
    
    def get_current_theme(self) -> Dict[str, str]:
        """
        Get the current theme settings.
        
        Returns:
            Dictionary containing theme color and style settings
        """
        theme_name = self.get_app_setting("ui", "theme", default="light")
        themes = self.get_app_setting("ui", "themes", default={})
        
        return themes.get(theme_name, self._default_theme())
    
    def _load_json_file(self, file_path: str, default: Any = None) -> Any:
        """
        Load a JSON file with error handling.
        
        Args:
            file_path: Path to the JSON file
            default: Default value to return if loading fails
            
        Returns:
            Parsed JSON content or default value if loading fails
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.last_modified[file_path] = os.path.getmtime(file_path)
                return data
            else:
                logger.warning(f"Settings file not found: {file_path}")
                return default if default is not None else {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in settings file: {file_path}")
            return default if default is not None else {}
        except Exception as e:
            logger.error(f"Error loading settings file {file_path}: {str(e)}")
            return default if default is not None else {}
    
    def _get_nested_setting(self, settings_dict: Dict[str, Any], keys: tuple, default: Any = None) -> Any:
        """
        Navigate through nested dictionary to find a specific setting.
        
        Args:
            settings_dict: Dictionary to navigate
            keys: Tuple of keys forming the path to the desired setting
            default: Default value to return if setting not found
            
        Returns:
            The setting value or default if not found
        """
        current = settings_dict
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def _default_app_settings(self) -> Dict[str, Any]:
        """
        Provide default application settings in case the settings file is missing.
        
        Returns:
            Dictionary of default application settings
        """
        return {
            "application": {
                "name": "Python Block Code Editor",
                "version": "1.0.0"
            },
            "ui": {
                "theme": "light",
                "themes": {
                    "light": self._default_theme(),
                    "dark": {
                        "background_color": "#2c3e50",
                        "text_color": "#ecf0f1",
                        "accent_color": "#3498db",
                        "panel_color": "#34495e",
                        "border_color": "#7f8c8d"
                    }
                },
                "font_family": "Consolas, 'Courier New', monospace",
                "font_size": 12
            },
            "editor": {
                "indentation_size": 4,
                "auto_indent": True
            },
            "blocks": {
                "snap_to_grid": True,
                "grid_size": 10
            },
            "execution": {
                "timeout_seconds": 5,
                "max_output_lines": 500,
                "clear_output_on_run": True
            }
        }
    
    def _default_theme(self) -> Dict[str, str]:
        """
        Provide default theme colors.
        
        Returns:
            Dictionary of default theme colors
        """
        return {
            "background_color": "#f5f5f5",
            "text_color": "#333333",
            "accent_color": "#3498db",
            "success_color": "#2ecc71",
            "warning_color": "#f39c12",
            "error_color": "#e74c3c",
            "highlight_color": "#9b59b6",
            "panel_color": "#ffffff",
            "border_color": "#dddddd"
        }


# Create a singleton instance
settings = SettingsLoader() 