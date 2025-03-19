# Mouser Part Finder

A CLI tool that helps find the best electronic components from Mouser Electronics using AI-powered part selection.

## Features

- Search Mouser's catalog using natural language queries
- AI-powered part selection using Claude
- Context-aware recommendations (e.g., specific microcontroller compatibility)
- Clean, scriptable output format
- Detailed verbose mode for debugging

## Installation

1. Clone the repository:
```bash
git clone https://github.com/LastZactionHero/part_finder.git
cd part_finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```bash
MOUSER_API_KEY=your_mouser_api_key
CLAUDE_API_KEY=your_claude_api_key
```

## Usage

Basic usage:
```bash
python mouser_search.py --query "500ohm 0805 resistor"
```

With context for better part selection:
```bash
python mouser_search.py --query "16mhz smd crystal oscillator" --context "Atmega32u4 oscillator"
```

Verbose mode for detailed information:
```bash
python mouser_search.py --query "500ohm 0805 resistor" -v
```

### Command Line Arguments

- `-q, --query`: Search query (required)
- `-c, --context`: Context for part selection (optional)
- `-v, --verbose`: Print detailed information about the part selection

## Output

By default, the tool outputs just the Mouser part number, making it easy to use in scripts or pipe to other commands.

Example output:
```
71-PTN0805Y5000BST1
```

With verbose mode (`-v`), you'll see:
- Claude's reasoning for part selection
- Detailed part information
- Price and availability

## Development

The tool uses:
- Python 3.x
- Mouser API for part search
- Claude API for intelligent part selection
- python-dotenv for environment variable management

## License

MIT License - feel free to use this tool for your own projects.
