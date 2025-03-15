# Python Block Code Editor by GrandpaEJ

## Introduction

Python Block Code Editor is a user-friendly visual programming environment for Python made with PyQt5. Made by GrandpaEJ

A visual programming environment for Python that allows you to create Python programs by dragging and dropping code blocks, similar to block-based programming environments like Scratch or Blockly, but specifically designed for Python.

## Features

- **Visual Block Programming**: Create Python programs by dragging and connecting visual blocks
- **Nestable Blocks**: Blocks can be nested inside other blocks (with intelligent validation)
- **Rich Block Palette**: Multiple categories of blocks for various programming constructs
- **Real-time Code Preview**: See the Python code generated from your blocks in real-time
- **Code Execution**: Run your block-based programs directly within the application
- **Project Management**: Save and load your block projects
- **Customizable**: JSON-based block definitions and application settings
- **Code Suggestions**: Simple machine learning for code suggestions (requires NumPy)

## Project Structure

```
python-block-code-editor/
├── main.py                   # Main application entry point
├── settings_loader.py        # Settings and configuration loader
├── block_models.py           # Block and input slot models
├── block_palette.py          # Block palette panel and items
├── workspace_widget.py       # Workspace for arranging blocks
├── output_panel.py           # Code preview and execution output panel
├── utils.py                  # Utility functions and ML features
├── app_settings.json         # Application settings and customization
├── block_definitions.json    # Block definitions and properties
├── block_capabilities.json   # Block nesting rules and capabilities
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/GrandpaEJ/python-block-code-editor.git
   cd python-block-code-editor
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

## Usage

1. **Create Blocks**: Drag blocks from the palette on the left to the workspace.
2. **Connect Blocks**: Blocks will automatically connect when placed below each other.
3. **Nest Blocks**: Some blocks (like if/else, loops) allow other blocks to be nested inside them.
4. **Edit Block Inputs**: Fill in the input fields or slots in each block.
5. **Preview Code**: The generated Python code is displayed in the right panel.
6. **Run Code**: Click the "Run" button to execute the generated Python code.
7. **Save/Load**: Use the toolbar buttons to save or load your projects.

## Customization

The application is highly customizable through JSON configuration files:

- **app_settings.json**: Application settings, theming, and UI preferences
- **block_definitions.json**: Block types, appearances, and code templates
- **block_capabilities.json**: Rules for which blocks can be nested where

## Block Types

The editor includes blocks for:

- **Basic**: Print, Variable, Input, Comment
- **Values**: Various data types (String, Number, Boolean, List, Dict)
- **Math**: Mathematical operations
- **Logic**: Comparisons and boolean operations
- **Control Flow**: If/Else, While, For loops
- **Functions**: Define and call functions
- **Data Structures**: List and dictionary operations

## Development

To extend the editor with new blocks:

1. Add new block definitions to `block_definitions.json`
2. Update the nesting rules in `block_capabilities.json` if needed
3. Add any new categories or modify existing ones

## Requirements

- Python 3.6+
- PyQt5 5.15.0+
- NumPy 1.19.0+ (optional, for code suggestions)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

Inspired by block-based programming environments like Scratch, Blockly, and similar visual programming tools. 