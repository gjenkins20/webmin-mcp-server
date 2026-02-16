# Webmin MCP Server

An MCP (Model Context Protocol) server that provides Claude with tools to
manage Linux systems via Webmin's web-based administration interface.

## Features

- **System Information**: Query Webmin version and server details
- More features coming soon...

## Requirements

- Python 3.11+
- A running Webmin instance (typically on port 10000)
- Webmin credentials with appropriate permissions

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/webmin-mcp-server.git
cd webmin-mcp-server

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

Set the following environment variables:

```bash
export WEBMIN_HOST="your-webmin-server.com"
export WEBMIN_PORT="10000"
export WEBMIN_USERNAME="admin"
export WEBMIN_PASSWORD="your-password"
export WEBMIN_USE_HTTPS="true"
export WEBMIN_VERIFY_SSL="true"  # Set to false for self-signed certs
```

Or create a `.env` file (see `.env.example`).

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "webmin": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/webmin-mcp-server",
      "env": {
        "WEBMIN_HOST": "your-webmin-server.com",
        "WEBMIN_USERNAME": "admin",
        "WEBMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

### Standalone

```bash
python -m src.server
```

## Available Tools

### `get_webmin_version`

Get the version of the connected Webmin server.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "version": "2.105",
    "hostname": "server.example.com"
  }
}
```

## Development

### Running Tests

```bash
pytest
```

### Linting

```bash
ruff check src tests
ruff format src tests
```

### Type Checking

```bash
mypy src
```

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
│   ├── task_tracker.md   # Project task tracking
│   ├── webmin_api_map.md # Webmin API documentation
│   └── qa_review.md      # QA review log
└── agents/               # Agent team prompts
```

## License

MIT
