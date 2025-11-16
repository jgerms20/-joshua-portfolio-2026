#!/usr/bin/env python3
"""
Enhanced Portfolio Internet Sourcer Agent
Uses web search API integration for comprehensive project discovery
"""

import json
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, quote_plus
import time
from bs4 import BeautifulSoup
import logging
import os

# Import base sourcer
from portfolio_sourcer import PortfolioSourcer

logger = logging.getLogger(__name__)


class EnhancedPortfolioSourcer(PortfolioSourcer):
    """Enhanced version with actual web search integration"""
    
    def __init__(self, config_path: str = "sourcer_config.json"):
        super().__init__(config_path)
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "")
        self.google_cx = os.getenv("GOOGLE_SEARCH_CX", "")
        self.bing_api_key = os.getenv("BING_SEARCH_API_KEY", "")
        
    def _perform_search(self, query: str) -> List[Dict]:
        """Perform actual web search using available APIs"""
        results = []
        
        # Try Google Custom Search API
        if self.google_api_key and self.google_cx:
            try:
                google_results = self._google_search(query)
                results.extend(google_results)
            except Exception as e:
                logger.error(f"Google search failed: {e}")
        
        # Try Bing Search API
        if self.bing_api_key:
            try:
                bing_results = self._bing_search(query)
                results.extend(bing_results)
            except Exception as e:
                logger.error(f"Bing search failed: {e}")
        
        # Fallback: Use web_search tool if available
        if not results:
            logger.warning("No search APIs configured. Using fallback methods.")
            # Could integrate with web_search MCP tool here
        
        return results
    
    def _google_search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search using Google Custom Search API"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": query,
            "num": num_results
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "google"
            })
        
        return results
    
    def _bing_search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search using Bing Web Search API"""
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": self.bing_api_key
        }
        params = {
            "q": query,
            "count": num_results,
            "textDecorations": False,
            "textFormat": "Raw"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "source": "bing"
            })
        
        return results
    
    def search_linkedin_profile(self) -> List[Dict]:
        """Search LinkedIn profile for project mentions"""
        linkedin_url = self.config.get("linkedin_url", "")
        if not linkedin_url:
            return []
        
        logger.info(f"Searching LinkedIn profile: {linkedin_url}")
        
        # Note: LinkedIn requires authentication or scraping
        # This is a placeholder for LinkedIn API integration
        # In production, use LinkedIn API or authenticated scraping
        
        projects = []
        
        # Search for mentions of LinkedIn profile in articles/posts
        queries = [
            f'site:linkedin.com "{self.config.get("name", "Joshua German")}"',
            f'site:linkedin.com/in/joshuamgerman',
        ]
        
        for query in queries:
            results = self._perform_search(query)
            projects.extend(self._extract_projects_from_results(results, query))
        
        return projects
    
    def search_industry_publications(self) -> List[Dict]:
        """Search industry publications for credits"""
        sources = self.config.get("search_sources", [])
        projects = []
        
        for source in sources:
            for name in self.verification_names[:3]:
                query = f'site:{source} "{name}"'
                logger.info(f"Searching {source} for {name}")
                results = self._perform_search(query)
                projects.extend(self._extract_projects_from_results(results, query))
                time.sleep(1)  # Rate limiting
        
        return projects
    
    def search_web_for_projects(self) -> List[Dict]:
        """Enhanced search with multiple strategies"""
        logger.info("Starting enhanced web search for projects...")
        all_projects = []
        
        # Strategy 1: General web search
        general_projects = super().search_web_for_projects()
        all_projects.extend(general_projects)
        
        # Strategy 2: LinkedIn profile search
        linkedin_projects = self.search_linkedin_profile()
        all_projects.extend(linkedin_projects)
        
        # Strategy 3: Industry publications
        publication_projects = self.search_industry_publications()
        all_projects.extend(publication_projects)
        
        # Deduplicate
        unique_projects = self._deduplicate_projects(all_projects)
        logger.info(f"Total unique projects discovered: {len(unique_projects)}")
        
        return unique_projects
    
    def check_youtube_videos(self) -> Dict[str, bool]:
        """Check if YouTube videos in portfolio are still accessible"""
        logger.info("Validating YouTube videos...")
        
        portfolio_file = self.config.get("portfolio_file", "index.html")
        video_status = {}
        
        try:
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Find all YouTube embed URLs
            youtube_pattern = r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
            matches = re.findall(youtube_pattern, html_content)
            
            for video_id in matches:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                embed_url = f"https://www.youtube.com/embed/{video_id}"
                
                # Check if video is accessible
                is_valid = self._check_youtube_video_exists(video_id)
                video_status[video_id] = {
                    "valid": is_valid,
                    "watch_url": video_url,
                    "embed_url": embed_url
                }
                
                if not is_valid:
                    logger.warning(f"YouTube video {video_id} may be unavailable")
        
        except Exception as e:
            logger.error(f"Error checking YouTube videos: {e}")
        
        return video_status
    
    def _check_youtube_video_exists(self, video_id: str) -> bool:
        """Check if YouTube video exists and is accessible"""
        try:
            # Use YouTube oEmbed API or direct check
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = requests.get(oembed_url, timeout=10)
            
            if response.status_code == 200:
                return True
            
            # Fallback: Check video page directly
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.head(video_url, timeout=10, allow_redirects=True)
            return response.status_code < 400
            
        except Exception as e:
            logger.debug(f"YouTube check failed for {video_id}: {e}")
            return False
    
    def generate_portfolio_update_suggestions(self, verified_projects: List[Dict]) -> List[Dict]:
        """Generate suggestions for adding new projects to portfolio"""
        suggestions = []
        
        # Compare discovered projects with known projects
        known_project_names = {p.get("name", "").lower() for p in self.config.get("known_projects", [])}
        
        for project in verified_projects:
            project_title = project.get("title", "").lower()
            
            # Check if this is a new project
            is_new = True
            for known_name in known_project_names:
                if known_name in project_title or project_title in known_name:
                    is_new = False
                    break
            
            if is_new:
                suggestions.append({
                    "project": project,
                    "action": "add",
                    "reason": "New verified project discovered",
                    "suggested_section": self._suggest_portfolio_section(project)
                })
        
        return suggestions
    
    def _suggest_portfolio_section(self, project: Dict) -> str:
        """Suggest which portfolio section a project should go in"""
        title = project.get("title", "").lower()
        snippet = project.get("snippet", "").lower()
        
        if any(brand in title or brand in snippet for brand in ["levi", "sephora", "doordash", "bmw", "califia", "directv", "samuel adams"]):
            return "campaigns"
        elif "podcast" in title or "podcast" in snippet:
            return "podcast"
        elif "writing" in title or "article" in snippet:
            return "writing"
        elif "ai" in title or "tool" in snippet:
            return "ai-projects"
        else:
            return "campaigns"  # Default
    
    def run_full_scan(self):
        """Run enhanced full scan"""
        logger.info("=" * 60)
        logger.info("Starting Enhanced Full Portfolio Scan")
        logger.info("=" * 60)
        
        # Run base scan
        report = super().run_full_scan()
        
        # Additional checks
        logger.info("Running additional validations...")
        
        # Check YouTube videos
        youtube_status = self.check_youtube_videos()
        report["youtube_video_status"] = youtube_status
        
        # Generate update suggestions
        verified_projects = report.get("verified_projects", [])
        suggestions = self.generate_portfolio_update_suggestions(verified_projects)
        report["update_suggestions"] = suggestions
        
        logger.info("=" * 60)
        logger.info("Enhanced Scan Complete")
        logger.info("=" * 60)
        
        return report


def main():
    """Main entry point for enhanced sourcer"""
    sourcer = EnhancedPortfolioSourcer()
    report = sourcer.run_full_scan()
    
    print("\n" + "=" * 60)
    print("ENHANCED PORTFOLIO SOURCER REPORT")
    print("=" * 60)
    print(f"\nVerified Projects Found: {len(report.get('verified_projects', []))}")
    print(f"Broken Links: {len(report.get('broken_links', []))}")
    print(f"Broken Images: {len(report.get('broken_images', []))}")
    
    youtube_status = report.get("youtube_video_status", {})
    invalid_videos = [vid for vid, status in youtube_status.items() if not status.get("valid", True)]
    if invalid_videos:
        print(f"Invalid YouTube Videos: {len(invalid_videos)}")
    
    suggestions = report.get("update_suggestions", [])
    if suggestions:
        print(f"\nNew Projects to Consider Adding: {len(suggestions)}")
        for sug in suggestions[:5]:  # Show first 5
            print(f"  - {sug['project'].get('title', 'Unknown')}")
    
    print(f"\nRecommendations:")
    for rec in report.get('recommendations', []):
        print(f"  - {rec}")
    print("\nFull report saved to portfolio_updates/ directory")


if __name__ == "__main__":
    main()

