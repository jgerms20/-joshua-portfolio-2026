# Portfolio Internet Sourcer Agent

An autonomous Python agent that scours the internet to discover, verify, and maintain Joshua German's portfolio projects. This agent automatically:

- **Discovers** new projects credited to Joshua German across the web
- **Triple-verifies** attribution using multiple verification methods
- **Validates** all links, images, and videos in the portfolio
- **Reports** broken links and suggests new projects to add
- **Keeps** the portfolio current and relevant

## Features

### Comprehensive Discovery
- Searches LinkedIn, industry publications (AdWeek, Campaign Live, Shoot Online, etc.)
- Scans for projects across known agencies (TBWA\Chiat\Day, Wieden+Kennedy, GS&P)
- Monitors brand campaigns (Levi's, Sephora, DoorDash, BMW, etc.)

### Triple Verification System
The agent uses multiple verification methods to ensure attribution:
1. **Name Mentions**: Counts occurrences of "Joshua German" variations on pages
2. **Agency Associations**: Verifies connections to known agencies
3. **LinkedIn Verification**: Cross-references with LinkedIn profile
4. **Brand Associations**: Confirms projects match known brand work
5. **Portfolio Cross-reference**: Checks for mentions on portfolio site

Projects must meet a minimum verification threshold (default: 3 points) to be considered verified.

### Link Validation
- Validates all external links in the portfolio
- Checks YouTube and Vimeo video embeds
- Verifies image URLs are accessible
- Reports broken links with specific locations

### Automated Reporting
- Generates detailed JSON reports with timestamps
- Provides actionable recommendations
- Tracks verification scores and evidence
- Suggests portfolio sections for new projects

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Set up search API keys for enhanced functionality:
```bash
export GOOGLE_SEARCH_API_KEY="your-google-api-key"
export GOOGLE_SEARCH_CX="your-google-cx"
export BING_SEARCH_API_KEY="your-bing-api-key"
```

## Usage

### Basic Usage
```bash
python -m portfolio_sourcer.portfolio_sourcer
```

### Automated Scheduling
Set up a cron job to run weekly:
```bash
# Edit crontab
crontab -e

# Add weekly scan (every Monday at 2 AM)
0 2 * * 1 cd /path/to/portfolio && ./run_sourcer.sh
```

Or use the provided runner script:
```bash
chmod +x run_sourcer.sh
./run_sourcer.sh
```

### Link Validation Only
For quick link checks without full discovery:
```python
from portfolio_sourcer.portfolio_sourcer import PortfolioSourcer

sourcer = PortfolioSourcer()
report = sourcer.validate_links_only()
```

## Configuration

Edit `portfolio_sourcer/config/sourcer_config.json` to customize:
- Your name variations for verification
- Known projects and brands
- Verification threshold
- Portfolio file path
- Search sources

### Configuration Structure

```json
{
  "name": "Joshua German",
  "verification_names": ["Joshua German", "Joshua M. German", ...],
  "linkedin_url": "https://linkedin.com/in/joshuamgerman",
  "portfolio_file": "index.html",
  "portfolio_url": "https://jgerms20.github.io/-joshua-portfolio-09.02.2025/",
  "verification_threshold": 3,
  "known_projects": [...],
  "known_agencies": [...],
  "known_brands": [...],
  "search_sources": [...]
}
```

## Output

Reports are saved to `portfolio_updates/` directory with timestamps:
```
portfolio_updates/
  └── update_report_20250115_143022.json
```

Each report contains:
- **verified_projects**: Newly discovered verified projects
- **validation_results**: Broken links, images, and videos
- **new_projects**: Projects not currently in portfolio
- **recommendations**: Actionable recommendations
- **portfolio_structure**: Current portfolio structure information

## Verification Process

1. **Discovery**: Agent searches web using multiple queries
2. **Extraction**: Extracts project information from search results
3. **Verification**: Triple-checks attribution using:
   - Page content analysis
   - Agency association matching
   - LinkedIn profile cross-reference
   - Brand association verification
   - Portfolio site mentions
4. **Scoring**: Assigns verification score (minimum 3 required)
5. **Reporting**: Generates detailed report with evidence

## Example Output

```
============================================================
PORTFOLIO SOURCER REPORT
============================================================

Verified Projects Found: 2
New Projects Discovered: 1
Broken Links: 3
Broken Images: 1
Broken Videos: 0
Total Issues: 4

Recommendations:
  - Fix 3 broken link(s). Check URLs for updates or replacements.
  - Replace 1 broken image(s). Verify image URLs or upload new images.
  - Consider adding 1 newly discovered verified project(s) to portfolio.
    - 'New Campaign Name' (verification score: 4)

============================================================
Full report saved to: portfolio_updates/
============================================================
```

## Architecture

The agent is built with modular components:

- **discovery.py**: Web search and discovery logic
- **verification.py**: Attribution verification system
- **link_validator.py**: Link/image/video validation
- **portfolio_parser.py**: HTML parsing and analysis
- **report_generator.py**: Report generation
- **portfolio_sourcer.py**: Main orchestrator

## Troubleshooting

### No search results
- Ensure search API keys are configured (for enhanced version)
- Check internet connection
- Review search query generation in logs

### High false positives
- Increase `verification_threshold` in config
- Add more specific verification keywords
- Review verification evidence in reports

### Rate limiting
- Increase delays between searches
- Use fewer search queries
- Consider API rate limits

### Import errors
- Ensure you're running from the project root directory
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify Python path includes the project directory

## Dependencies

- `requests` - HTTP requests for link validation and content fetching
- `beautifulsoup4` - HTML parsing
- `lxml` - Fast HTML parser backend

## Future Enhancements

- LinkedIn API integration for profile scraping
- Automated portfolio HTML updates
- Image replacement suggestions
- Social media monitoring
- Email notifications for new discoveries
- Webhook integration for CI/CD

## License

MIT License - Feel free to adapt for your own portfolio!

