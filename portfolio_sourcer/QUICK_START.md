# Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

### Run Full Scan
```bash
python -m portfolio_sourcer.portfolio_sourcer
```

### Run with Script
```bash
./run_sourcer.sh
```

### Link Validation Only (Python)
```python
from portfolio_sourcer.portfolio_sourcer import PortfolioSourcer

sourcer = PortfolioSourcer()
report = sourcer.validate_links_only()
print(report)
```

## Configuration

Edit `portfolio_sourcer/config/sourcer_config.json`:
- `verification_names`: Name variations to search for
- `verification_threshold`: Minimum score for verification (default: 3)
- `known_projects`: Existing projects (for comparison)
- `known_agencies`: Agencies to verify against
- `known_brands`: Brands to verify against
- `search_sources`: Industry publications to search

## Output

Reports are saved to `portfolio_updates/update_report_YYYYMMDD_HHMMSS.json`

## Scheduling

Add to crontab for weekly scans:
```bash
0 2 * * 1 cd /path/to/portfolio && ./run_sourcer.sh
```

