# Contributing to Python Block Code Editor

Thank you for your interest in contributing to the Python Block Code Editor! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Environment Setup](#environment-setup)
  - [Project Structure](#project-structure)
- [Development Process](#development-process)
  - [Branching Strategy](#branching-strategy)
  - [Coding Standards](#coding-standards)
  - [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Adding New Block Types](#adding-new-block-types)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all contributors. Please be respectful and considerate of others when participating in this project.

## Getting Started

### Environment Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/py_block_code.git
   cd py_block_code
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application to verify everything is working:
   ```bash
   python main.py
   ```

### Project Structure

- **main.py** - Application entry point and main window implementation
- **block_models.py** - Core models for code blocks and input slots
- **workspace_widget.py** - Workspace where blocks are arranged and connected
- **block_palette.py** - Palette of available block types
- **code_tree.py** - Tree view of code structure
- **output_panel.py** - Panel for displaying generated code and output
- **settings_loader.py** - Loads and manages settings
- **utils.py** - Utility functions used throughout the application
- **block_definitions.json** - Defines available block types and their properties
- **block_capabilities.json** - Defines which blocks can connect to which
- **app_settings.json** - Application settings

## Development Process

### Branching Strategy

1. Create a new branch for each feature or bug fix:
   ```bash
   git checkout -b feature/my-new-feature
   # or
   git checkout -b bugfix/issue-description
   ```

2. Make your changes, commit them with clear and descriptive messages.

3. Push your branch to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```

4. Create a pull request from your branch to the main repository.

### Coding Standards

- Follow PEP 8 for Python code style.
- Use descriptive variable and function names.
- Include docstrings for all classes and methods.
- Keep functions and methods short and focused on a single task.
- Comment complex sections of code to explain their purpose.
- Use type hints where appropriate.

### Testing

- Add appropriate tests for new functionality.
- Ensure all tests pass before submitting a pull request.
- Run tests using:
  ```bash
  python -m pytest
  ```

## Pull Request Process

1. Update the README.md with details of changes if applicable.
2. Update documentation as needed.
3. Ensure your code passes all tests.
4. Submit the pull request with a clear description of the changes.
5. Address any feedback during code review.

## Adding New Block Types

To add a new block type to the application:

1. Add a new entry to `block_definitions.json` following the existing format.
2. Update `block_capabilities.json` to define how the new block can connect with existing blocks.
3. If the block requires special handling, update the relevant code in `block_models.py`.
4. Add appropriate tests for the new block type.
5. Update documentation to include the new block type.

Example of a block definition:

```json
{
  "BlockName": {
    "name": "BlockName",
    "category": "Category",
    "color": [100, 150, 200],
    "inputs": [
      {
        "name": "input_name",
        "type": "text",
        "default": "default_value"
      }
    ],
    "code_template": "python_code_template_{inputs.input_name}",
    "output_enabled": true,
    "output_value": "{inputs.input_name}",
    "has_children": false,
    "documentation": "Description of what this block does"
  }
}
```

## Documentation

- Update the documentation when adding new features or making significant changes.
- Include examples of how to use new features.
- Keep the README.md file up to date.

## Troubleshooting

If you encounter any issues while setting up or developing, please:

1. Check the existing issues to see if your problem has been reported.
2. If not, create a new issue with a detailed description of the problem, including:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment information (OS, Python version, etc.)

---

Thank you for contributing to the Python Block Code Editor project! Your contributions help make this tool better for everyone. 