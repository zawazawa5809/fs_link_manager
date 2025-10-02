# FS Link Manager

Windows file/folder link organizer with drag-and-drop support.

## Features

- Drag and drop files/folders from Windows Explorer
- Search by name, path, or tags
- List and grid view modes
- Light and dark theme support
- Import/export links as JSON
- Windows Explorer integration

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fs_link_manager.git
cd fs_link_manager

# Install dependencies with uv
uv pip install PySide6
```

## Usage

```bash
# Run the application
uv run python run.py
```

## Project Structure

```
fs_link_manager/
├── src/                 # Source code
│   ├── core/           # Core functionality
│   ├── ui/             # User interface
│   └── themes/         # Theme management
├── tests/              # Unit tests
├── data/               # Database storage
├── logs/               # Application logs
└── docs/               # Documentation
```

## Development

```bash
# Run tests
uv run python run_tests.py
```

## License

MIT