# Contributing to Webmin MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/webmin-mcp-server.git
   cd webmin-mcp-server
   ```
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- A Webmin server for testing (optional but recommended)

### Running Tests

```bash
pytest
```

### Code Quality

Before submitting, ensure your code passes linting and type checks:

```bash
ruff check src tests
ruff format src tests
mypy src
```

## How to Contribute

### Reporting Bugs

- Check existing issues first to avoid duplicates
- Use a clear, descriptive title
- Include steps to reproduce the issue
- Include your environment details (Python version, OS, Webmin version)

### Suggesting Features

- Open an issue describing the feature
- Explain the use case and why it would be valuable
- If proposing a new Webmin API integration, reference the relevant Webmin module

### Submitting Pull Requests

1. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style guidelines

3. Add tests for new functionality

4. Ensure all tests pass:
   ```bash
   pytest
   ```

5. Commit with a clear message:
   ```bash
   git commit -m "Add feature: description of change"
   ```

6. Push and open a pull request

### Code Style

- Follow existing code patterns in the codebase
- Use type hints for all function parameters and return values
- Keep functions focused and single-purpose
- Add docstrings for public functions

### Adding New Tools

When adding new MCP tools:

1. Add the tool function in the appropriate file under `src/tools/`
2. Follow the existing pattern for tool registration
3. Include proper error handling
4. Add safety tier classification (read, safe, moderate, dangerous)
5. Update `docs/webmin_api_map.md` with the new endpoint documentation
6. Add tests in `tests/`

## Project Structure

```
webmin-mcp-server/
├── src/
│   ├── server.py         # MCP server setup
│   ├── webmin_client.py  # Webmin API client
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic models
│   └── tools/            # MCP tool implementations
├── tests/                # Test suite
├── docs/                 # Documentation
└── pyproject.toml        # Project configuration
```

## Questions?

Open an issue for any questions about contributing.
