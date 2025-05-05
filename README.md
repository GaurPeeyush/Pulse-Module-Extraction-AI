
# Pulse - AI-Powered Documentation Analyzer

## Overview

Pulse is a powerful tool designed to extract structured information from help documentation websites. It automatically identifies modules, submodules, and generates detailed descriptions by analyzing the content and structure of documentation pages.

![Screenshot 2025-05-05 at 10 09 35 PM](https://github.com/user-attachments/assets/9b6d7128-8550-42b6-a50a-a6ace53f2079)

## Features

- **Intelligent Web Crawling**: Navigates documentation websites while respecting site structure
- **Smart Content Extraction**: Identifies and extracts relevant content while preserving structure
- **Advanced Structure Recognition**: Extracts headings, tables, lists, and code blocks with their relationships
- **AI-Powered Analysis**: Uses OpenAI's language models to identify modules and submodules
- **Hierarchical Organization**: Maintains relationships between content sections
- **Multiple Interfaces**: Access via Streamlit web app or command-line interface
- **Structured Output**: Generates clean JSON output for further processing

## Project Structure

```
pulse/
├── app/
│   └── app.py            # Streamlit user interface
├── scripts/
│   └── cli.py            # Command-line interface
├── utils/
│   ├── crawler.py        # Web crawling functionality
│   └── extractor.py      # Module extraction with OpenAI
├── requirements.txt      # Dependencies
└── .env.example          # Example environment variables
```

## Technologies Used

- **Python 3.8+**: Core programming language
- **BeautifulSoup4**: HTML parsing and content extraction
- **Requests**: HTTP requests to fetch web pages
- **Trafilatura**: Advanced content extraction
- **HTML2Text**: Structured text conversion
- **OpenAI API**: AI-powered module extraction
- **Streamlit**: Web interface framework
- **Dotenv**: Environment variable management

## Installation

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/pulse.git
cd pulse
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp .env.example .env
```

5. Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Streamlit Web App

1. Start the Streamlit app:

```bash
cd pulse
streamlit run app/app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Enter the URL(s) of the documentation site you want to analyze

4. Configure the optional settings:
   - Maximum pages to crawl
   - Delay between requests
   - AI model (GPT-3.5-Turbo or GPT-4)

5. Click "Extract Modules" to start the process

6. View the results in the interactive tabs:
   - Interactive View: Expandable modules and submodules
   - JSON Output: Raw JSON data with download option
   - Site Structure: Hierarchical view of the crawled pages
   - Content Structure: Extracted structural elements

### Command Line Interface

The CLI offers more flexibility for batch processing and integration with other tools.

Basic usage:

```bash
python pulse/scripts/cli.py --urls https://docs.example.com --output results.json
```

Advanced options:

```bash
python pulse/scripts/cli.py \
  --urls https://docs.example.com https://help.example.com \
  --output extracted_modules.json \
  --max-pages 150 \
  --delay 0.7 \
  --model gpt-4 \
  --save-structure \
  --save-raw-content
```

Available options:

| Option | Description |
|--------|-------------|
| `--urls` | URLs of documentation websites to process (required) |
| `--output` | Output file path for JSON results (default: extracted_modules.json) |
| `--max-pages` | Maximum number of pages to crawl per URL (default: 100) |
| `--delay` | Delay between requests in seconds (default: 0.5) |
| `--model` | OpenAI model to use (gpt-3.5-turbo or gpt-4) |
| `--save-structure` | Also save the site structure to a separate file |
| `--save-raw-content` | Save the raw extracted content to a separate file |
| `--api-key` | OpenAI API key (if not set in environment variable) |

## Output Format

Pulse generates a structured JSON output containing modules and their submodules:

```json
[
  {
    "module": "Authentication",
    "Description": "Detailed description of the authentication module...",
    "Submodules": {
      "Login": "Description of the login functionality...",
      "Registration": "Description of the registration process...",
      "Password Reset": "Details about password recovery..."
    }
  },
  {
    "module": "User Management",
    "Description": "Overview of user management capabilities...",
    "Submodules": {
      "Roles and Permissions": "Description of role-based access...",
      "User Profiles": "Information about user profile features..."
    }
  }
]
```

## Example Usage Scenarios

### Analyzing Product Documentation

```bash
python pulse/scripts/cli.py --urls https://docs.product.com/api-reference --max-pages 200
```

### Extracting Help Center Content

```bash
python pulse/scripts/cli.py --urls https://help.service.com --model gpt-4 --save-structure
```

### Processing Multiple Documentation Sources

```bash
python pulse/scripts/cli.py --urls https://dev.example.com/docs https://support.example.com
```

## Performance Considerations

- **Rate Limiting**: Respect website rate limits by adjusting the `--delay` parameter
- **Model Selection**: GPT-3.5-Turbo is faster and cheaper, while GPT-4 may provide more accurate results
- **Page Limits**: Set appropriate `--max-pages` to control crawling scope
- **Memory Usage**: Large documentation sites may require significant memory

## Troubleshooting

### Common Issues

1. **OpenAI API Key Issues**
   - Ensure your API key is correct and has sufficient credits
   - Check that the key is properly set in the .env file

2. **Crawling Problems**
   - Some sites may block automated crawling
   - Try increasing the delay between requests
   - Check if the site requires authentication

3. **Content Extraction Issues**
   - Some sites may have unusual document structures
   - Check the raw content output to verify extraction quality

### Logs

Check the log file `module_extractor.log` for detailed information about the extraction process.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for providing the powerful language models
- The Streamlit team for the excellent web app framework
- All open-source projects that made this tool possible

---

Built with ❤️ by Peeyush Gaur
