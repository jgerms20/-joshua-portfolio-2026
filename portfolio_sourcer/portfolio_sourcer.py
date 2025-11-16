#!/usr/bin/env python3
"""
Portfolio Internet Sourcer Agent
Main orchestrator that ties all components together
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from portfolio_sourcer.discovery import DiscoveryEngine
from portfolio_sourcer.verification import VerificationSystem
from portfolio_sourcer.link_validator import LinkValidator
from portfolio_sourcer.portfolio_parser import PortfolioParser
from portfolio_sourcer.report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portfolio_sourcer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PortfolioSourcer:
    """Main orchestrator for portfolio sourcing and validation"""
    
    def __init__(self, config_path: str = None):
        """Initialize portfolio sourcer with configuration"""
        if config_path is None:
            # Try config in portfolio_sourcer/config first, then root
            config_paths = [
                Path(__file__).parent / "config" / "sourcer_config.json",
                Path(__file__).parent.parent / "sourcer_config.json",
                Path(__file__).parent.parent / "portfolio_sourcer" / "config" / "sourcer_config.json"
            ]
            for path in config_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path is None:
            raise FileNotFoundError(
                f"Configuration file not found. Searched: {[str(p) for p in config_paths]}"
            )
        
        self.config = self._load_config(config_path)
        portfolio_file = self.config.get("portfolio_file", "index.html")
        # Resolve portfolio file path relative to project root
        if not Path(portfolio_file).is_absolute():
            # Try relative to config file location, then project root
            config_dir = Path(config_path).parent
            project_root = config_dir.parent.parent if "portfolio_sourcer" in str(config_dir) else config_dir.parent
            portfolio_path = project_root / portfolio_file
            if portfolio_path.exists():
                self.portfolio_file = str(portfolio_path)
            else:
                self.portfolio_file = portfolio_file
        else:
            self.portfolio_file = portfolio_file
        
        # Initialize components
        self.discovery = DiscoveryEngine(self.config)
        self.verification = VerificationSystem(self.config)
        self.link_validator = LinkValidator(self.portfolio_file)
        self.portfolio_parser = PortfolioParser(self.portfolio_file)
        self.report_generator = ReportGenerator()
        
        logger.info("Portfolio Sourcer initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            raise
    
    def run_full_scan(self, search_api=None) -> Dict:
        """
        Run complete portfolio sourcing and validation scan
        Args:
            search_api: Optional search API function for web searches
        Returns:
            Report dictionary
        """
        logger.info("=" * 60)
        logger.info("Starting Full Portfolio Scan")
        logger.info("=" * 60)
        
        # Step 1: Discover projects
        logger.info("Step 1: Discovering projects...")
        discovered_projects = self.discovery.discover_projects(search_api=search_api)
        
        # Step 2: Verify attribution
        logger.info("Step 2: Verifying attribution...")
        verified_projects = self.verification.verify_multiple_projects(discovered_projects)
        
        # Step 3: Validate existing links
        logger.info("Step 3: Validating portfolio links...")
        validation_results = self.link_validator.validate_all()
        
        # Step 4: Parse portfolio structure
        logger.info("Step 4: Parsing portfolio structure...")
        portfolio_structure = self.portfolio_parser.get_portfolio_structure()
        
        # Step 5: Compare discovered vs existing
        logger.info("Step 5: Comparing with existing projects...")
        new_projects = self.portfolio_parser.compare_with_discovered(verified_projects)
        
        # Step 6: Generate report
        logger.info("Step 6: Generating report...")
        report = self.report_generator.generate_report(
            verified_projects=verified_projects,
            validation_results=validation_results,
            portfolio_structure=portfolio_structure,
            new_projects=new_projects
        )
        
        # Step 7: Save report
        report_path = self.report_generator.save_report(report)
        
        # Print summary
        summary_text = self.report_generator.generate_summary_text(report)
        print(summary_text)
        
        logger.info("=" * 60)
        logger.info("Scan Complete")
        logger.info("=" * 60)
        logger.info(f"Report saved to: {report_path}")
        
        return report
    
    def validate_links_only(self) -> Dict:
        """Run link validation only (faster for quick checks)"""
        logger.info("Running link validation only...")
        validation_results = self.link_validator.validate_all()
        
        report = {
            "timestamp": self.report_generator.generate_report({}, validation_results).get("timestamp"),
            "validation_results": validation_results,
            "summary": {
                "broken_links_count": len(validation_results.get("broken_links", [])),
                "broken_images_count": len(validation_results.get("broken_images", [])),
                "broken_videos_count": len(validation_results.get("broken_videos", []))
            }
        }
        
        return report


def main():
    """Main entry point"""
    try:
        sourcer = PortfolioSourcer()
        report = sourcer.run_full_scan()
        
        # Exit with error code if there are issues
        summary = report.get("summary", {})
        total_issues = summary.get("total_issues", 0)
        
        sys.exit(0 if total_issues == 0 else 1)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

