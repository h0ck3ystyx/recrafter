# Recrafter

A powerful Python web crawler designed to facilitate website migration to Crafter CMS by downloading and analyzing website content, structure, and assets.

## Features

- **Intelligent Crawling**: Configurable depth, domain restrictions, and rate limiting
- **Asset Management**: Downloads HTML, CSS, JavaScript, images, and other assets
- **Content Analysis**: Extracts metadata, content sections, and reusable components
- **Structured Storage**: Organizes data in machine-readable JSON/YAML format
- **CMS Integration**: Generates content models and templates for Crafter CMS
- **Command Line Interface**: Easy to use in automation pipelines

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd recrafter
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

Basic crawling:
```bash
python -m recrafter crawl --start-url https://example.com --output-dir ./output
```

Advanced crawling with configuration:
```bash
python -m recrafter crawl --start-url https://example.com --max-depth 5 --delay 2 --output-dir ./output
```

## Configuration

Create a `config.yaml` file for advanced settings:

```yaml
crawler:
  max_depth: 3
  delay: 1.0
  max_concurrent: 5
  user_agent: "Recrafter/1.0"
  
storage:
  output_dir: "./crawl_output"
  save_assets: true
  clean_html: false
  
analysis:
  extract_components: true
  generate_sitemap: true
  create_content_models: true
```

## Usage Examples

### Basic Crawling
```bash
# Crawl a website with default settings
python -m recrafter crawl --start-url https://example.com

# Specify output directory
python -m recrafter crawl --start-url https://example.com --output-dir ./my_site_data
```

### Advanced Crawling
```bash
# Deep crawl with custom settings
python -m recrafter crawl \
  --start-url https://example.com \
  --max-depth 5 \
  --delay 2.0 \
  --max-concurrent 10 \
  --output-dir ./deep_crawl
```

### Analysis and Export
```bash
# Analyze crawled data
python -m recrafter analyze --input-dir ./crawl_output

# Export for CMS
python -m recrafter export --input-dir ./crawl_output --format cms
```

## Output Structure

The crawler generates a structured output directory:

```
output/
├── pages/
│   ├── index.html
│   ├── about.html
│   └── contact.html
├── assets/
│   ├── images/
│   ├── css/
│   └── js/
├── metadata/
│   ├── sitemap.json
│   ├── content_models.json
│   └── page_analysis.json
└── logs/
    └── crawl.log
```

## API Reference

### Core Commands

- `crawl`: Main crawling command
- `analyze`: Analyze crawled data
- `export`: Export data in various formats
- `validate`: Validate downloaded content

### Configuration Options

- `--start-url`: Starting URL for crawling
- `--output-dir`: Output directory for files
- `--max-depth`: Maximum crawl depth
- `--delay`: Delay between requests
- `--max-concurrent`: Maximum concurrent requests
- `--user-agent`: Custom user agent string
- `--config`: Configuration file path

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
The project follows PEP 8 guidelines. Use a linter like `flake8` or `black` for code formatting.

### Architecture

The application is built with a modular architecture:

- **Crawler Engine**: Handles web crawling and asset downloading
- **Storage Layer**: Manages file storage and organization
- **Analysis Engine**: Extracts content and generates metadata
- **Export System**: Creates CMS-ready output formats
- **CLI Interface**: Command-line user interface

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Review the test examples

