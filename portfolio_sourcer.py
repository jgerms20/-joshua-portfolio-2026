#!/usr/bin/env python3
"""
Portfolio Internet Sourcer Agent
Autonomously discovers, verifies, and updates Joshua German's portfolio projects
by scouring the internet for verified credits and validating all links/media.
"""

import json
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
import time
from bs4 import BeautifulSoup
import logging

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
    """Main agent for sourcing and verifying portfolio projects"""
    
    def __init__(self, config_path: str = "sourcer_config.json"):
        """Initialize the sourcer with configuration"""
        self.config = self._load_config(config_path)
        self.verified_projects: Dict = {}
        self.broken_links: List[Dict] = []
        self.new_discoveries: List[Dict] = []
        
        # Verification keywords for Joshua German
        self.verification_names = [
            "Joshua German",
            "Joshua M. German",
            "Joshua McKenzie German",
            "Josh German",
            "J. German"
        ]
        
        # Known agencies and platforms
        self.known_agencies = [
            "TBWA\\Chiat\\Day",
            "TBWA Chiat Day",
            "Wieden+Kennedy",
            "Goodby, Silverstein & Partners",
            "GS&P"
        ]
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return {
                "name": "Joshua German",
                "linkedin_url": "https://linkedin.com/in/joshuamgerman",
                "portfolio_file": "index.html",
                "known_projects": [],
                "search_engines": ["google", "bing"],
                "verification_threshold": 3  # Minimum verification points needed
            }
    
    def search_web_for_projects(self) -> List[Dict]:
        """
        Search the web for projects credited to Joshua German
        Uses multiple search strategies for comprehensive coverage
        """
        logger.info("Starting web search for projects...")
        discovered_projects = []
        
        search_queries = self._generate_search_queries()
        
        for query in search_queries:
            logger.info(f"Searching: {query}")
            try:
                # Use web_search tool via MCP or direct API calls
                results = self._perform_search(query)
                projects = self._extract_projects_from_results(results, query)
                discovered_projects.extend(projects)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error searching for '{query}': {e}")
        
        # Deduplicate projects
        unique_projects = self._deduplicate_projects(discovered_projects)
        logger.info(f"Discovered {len(unique_projects)} unique potential projects")
        
        return unique_projects
    
    def _generate_search_queries(self) -> List[str]:
        """Generate comprehensive search queries"""
        queries = []
        
        # Name-based searches
        for name in self.verification_names:
            queries.extend([
                f'"{name}" advertising campaign',
                f'"{name}" strategy',
                f'"{name}" TBWA',
                f'"{name}" Wieden+Kennedy',
                f'"{name}" Goodby Silverstein',
                f'"{name}" portfolio',
                f'"{name}" credits',
            ])
        
        # Brand-specific searches
        known_brands = ["Levi's", "Sephora", "DoorDash", "BMW", "Califia", "DIRECTV", "Samuel Adams"]
        for brand in known_brands:
            for name in self.verification_names[:3]:  # Use top 3 name variations
                queries.append(f'"{name}" {brand}')
        
        # LinkedIn and portfolio site searches
        queries.extend([
            f'"{self.verification_names[0]}" LinkedIn',
            f'site:linkedin.com "{self.verification_names[0]}"',
            f'site:adweek.com "{self.verification_names[0]}"',
            f'site:campaignlive.com "{self.verification_names[0]}"',
            f'site:shootonline.com "{self.verification_names[0]}"',
        ])
        
        return queries
    
    def _perform_search(self, query: str) -> List[Dict]:
        """
        Perform web search - placeholder for actual search implementation
        In production, this would use Google Custom Search API, Bing API, or web scraping
        """
        # This is a placeholder - actual implementation would use search APIs
        # For now, return empty results structure
        return []
    
    def _extract_projects_from_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Extract project information from search results"""
        projects = []
        
        for result in results:
            try:
                project = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "source": query,
                    "discovered_at": datetime.now().isoformat()
                }
                projects.append(project)
            except Exception as e:
                logger.error(f"Error extracting project from result: {e}")
        
        return projects
    
    def _deduplicate_projects(self, projects: List[Dict]) -> List[Dict]:
        """Remove duplicate projects based on URL and title similarity"""
        seen_urls = set()
        seen_titles = set()
        unique = []
        
        for project in projects:
            url = project.get("url", "").lower()
            title = project.get("title", "").lower()
            
            # Normalize URL
            normalized_url = self._normalize_url(url)
            
            if normalized_url and normalized_url not in seen_urls:
                if title not in seen_titles or self._calculate_similarity(title, list(seen_titles)) < 0.8:
                    seen_urls.add(normalized_url)
                    seen_titles.add(title)
                    unique.append(project)
        
        return unique
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        if not url:
            return ""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    
    def _calculate_similarity(self, text: str, texts: List[str]) -> float:
        """Calculate similarity between text and list of texts"""
        if not texts:
            return 0.0
        # Simple word overlap similarity
        words = set(text.split())
        max_sim = 0.0
        for t in texts:
            t_words = set(t.split())
            if words or t_words:
                sim = len(words & t_words) / len(words | t_words)
                max_sim = max(max_sim, sim)
        return max_sim
    
    def verify_attribution(self, project: Dict) -> Tuple[bool, int, List[str]]:
        """
        Triple verification system for Joshua German attribution
        Returns: (is_verified, verification_score, evidence_sources)
        """
        url = project.get("url", "")
        if not url:
            return False, 0, []
        
        logger.info(f"Verifying attribution for: {project.get('title', 'Unknown')}")
        
        verification_score = 0
        evidence_sources = []
        
        try:
            # Method 1: Check page content for name mentions
            content = self._fetch_page_content(url)
            if content:
                name_mentions = self._count_name_mentions(content)
                if name_mentions > 0:
                    verification_score += name_mentions
                    evidence_sources.append(f"Name mentioned {name_mentions} time(s) on page")
            
            # Method 2: Check for agency associations
            agency_matches = self._check_agency_associations(content or "")
            if agency_matches:
                verification_score += len(agency_matches)
                evidence_sources.append(f"Associated with agencies: {', '.join(agency_matches)}")
            
            # Method 3: Check LinkedIn profile for project mention
            linkedin_match = self._check_linkedin_mention(project)
            if linkedin_match:
                verification_score += 2
                evidence_sources.append("Mentioned on LinkedIn profile")
            
            # Method 4: Check for known brand associations
            brand_match = self._check_brand_association(project, content or "")
            if brand_match:
                verification_score += 1
                evidence_sources.append(f"Associated with known brand: {brand_match}")
            
            # Method 5: Check for portfolio site mentions
            portfolio_match = self._check_portfolio_mention(url, content or "")
            if portfolio_match:
                verification_score += 1
                evidence_sources.append("Mentioned on portfolio site")
            
        except Exception as e:
            logger.error(f"Error verifying attribution: {e}")
        
        threshold = self.config.get("verification_threshold", 3)
        is_verified = verification_score >= threshold
        
        if is_verified:
            logger.info(f"✓ Verified (score: {verification_score}): {project.get('title', 'Unknown')}")
        else:
            logger.warning(f"✗ Not verified (score: {verification_score}): {project.get('title', 'Unknown')}")
        
        return is_verified, verification_score, evidence_sources
    
    def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and parse page content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            return soup.get_text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _count_name_mentions(self, content: str) -> int:
        """Count how many times Joshua German's name appears in content"""
        count = 0
        content_lower = content.lower()
        
        for name in self.verification_names:
            # Case-insensitive search
            pattern = re.compile(re.escape(name.lower()), re.IGNORECASE)
            matches = pattern.findall(content)
            count += len(matches)
        
        return count
    
    def _check_agency_associations(self, content: str) -> List[str]:
        """Check if content mentions known agencies"""
        found_agencies = []
        content_lower = content.lower()
        
        for agency in self.known_agencies:
            if agency.lower() in content_lower:
                found_agencies.append(agency)
        
        return found_agencies
    
    def _check_linkedin_mention(self, project: Dict) -> bool:
        """Check if project is mentioned on LinkedIn profile"""
        # This would require LinkedIn API access or scraping
        # For now, return False - implement with proper LinkedIn integration
        return False
    
    def _check_brand_association(self, project: Dict, content: str) -> Optional[str]:
        """Check if project is associated with known brands"""
        known_brands = ["Levi's", "Sephora", "DoorDash", "BMW", "Califia", "DIRECTV", "Samuel Adams"]
        content_lower = content.lower()
        
        for brand in known_brands:
            if brand.lower() in content_lower:
                return brand
        
        return None
    
    def _check_portfolio_mention(self, url: str, content: str) -> bool:
        """Check if URL/content references portfolio site"""
        portfolio_domains = [
            "jgerms20.github.io",
            "joshuagerman.com",
            "joshua-german.com"
        ]
        
        for domain in portfolio_domains:
            if domain in url.lower():
                return True
        
        return False
    
    def validate_links(self, portfolio_file: str = None) -> Dict[str, List[Dict]]:
        """
        Validate all links and images in the portfolio
        Returns dictionary with broken_links and broken_images
        """
        if portfolio_file is None:
            portfolio_file = self.config.get("portfolio_file", "index.html")
        
        logger.info(f"Validating links in {portfolio_file}...")
        
        broken_links = []
        broken_images = []
        
        try:
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if self._is_external_link(href):
                    if not self._check_link_valid(href):
                        broken_links.append({
                            "url": href,
                            "element": str(link)[:100],
                            "type": "link"
                        })
            
            # Check all images
            for img in soup.find_all('img', src=True):
                src = img['src']
                if self._is_external_link(src):
                    if not self._check_link_valid(src):
                        broken_images.append({
                            "url": src,
                            "alt": img.get('alt', ''),
                            "type": "image"
                        })
            
            # Check iframes (YouTube, Vimeo, etc.)
            for iframe in soup.find_all('iframe', src=True):
                src = iframe['src']
                if not self._check_link_valid(src):
                    broken_links.append({
                        "url": src,
                        "element": "iframe",
                        "type": "video"
                    })
            
            logger.info(f"Found {len(broken_links)} broken links and {len(broken_images)} broken images")
            
        except Exception as e:
            logger.error(f"Error validating links: {e}")
        
        return {
            "broken_links": broken_links,
            "broken_images": broken_images
        }
    
    def _is_external_link(self, url: str) -> bool:
        """Check if URL is external (not a local anchor or file)"""
        if not url or url.startswith('#') or url.startswith('javascript:'):
            return False
        
        parsed = urlparse(url)
        return bool(parsed.netloc)
    
    def _check_link_valid(self, url: str) -> bool:
        """Check if a link is valid and accessible"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Handle YouTube/Vimeo embeds differently
            if 'youtube.com/embed' in url or 'youtu.be' in url:
                # YouTube embeds are usually valid if URL format is correct
                return self._validate_youtube_url(url)
            elif 'vimeo.com' in url:
                return self._validate_vimeo_url(url)
            
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            return response.status_code < 400
            
        except Exception as e:
            logger.debug(f"Link validation failed for {url}: {e}")
            return False
    
    def _validate_youtube_url(self, url: str) -> bool:
        """Validate YouTube URL format"""
        youtube_patterns = [
            r'youtube\.com/embed/[a-zA-Z0-9_-]+',
            r'youtu\.be/[a-zA-Z0-9_-]+',
            r'youtube\.com/watch\?v=[a-zA-Z0-9_-]+'
        ]
        
        for pattern in youtube_patterns:
            if re.search(pattern, url):
                return True
        
        return False
    
    def _validate_vimeo_url(self, url: str) -> bool:
        """Validate Vimeo URL format"""
        vimeo_patterns = [
            r'vimeo\.com/\d+',
            r'player\.vimeo\.com/video/\d+'
        ]
        
        for pattern in vimeo_patterns:
            if re.search(pattern, url):
                return True
        
        return False
    
    def update_portfolio(self, verified_projects: List[Dict], validation_results: Dict):
        """Update portfolio with verified projects and fix broken links"""
        logger.info("Updating portfolio...")
        
        # Generate update report
        report = {
            "timestamp": datetime.now().isoformat(),
            "verified_projects": verified_projects,
            "broken_links": validation_results.get("broken_links", []),
            "broken_images": validation_results.get("broken_images", []),
            "recommendations": self._generate_recommendations(verified_projects, validation_results)
        }
        
        # Save report
        report_path = Path("portfolio_updates") / f"update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Update report saved to {report_path}")
        
        return report
    
    def _generate_recommendations(self, projects: List[Dict], validation_results: Dict) -> List[str]:
        """Generate recommendations for portfolio updates"""
        recommendations = []
        
        if validation_results.get("broken_links"):
            recommendations.append(f"Fix {len(validation_results['broken_links'])} broken links")
        
        if validation_results.get("broken_images"):
            recommendations.append(f"Replace {len(validation_results['broken_images'])} broken images")
        
        if projects:
            recommendations.append(f"Consider adding {len(projects)} newly discovered verified projects")
        
        return recommendations
    
    def run_full_scan(self):
        """Run complete portfolio sourcing and validation scan"""
        logger.info("=" * 60)
        logger.info("Starting Full Portfolio Scan")
        logger.info("=" * 60)
        
        # Step 1: Search for projects
        discovered_projects = self.search_web_for_projects()
        
        # Step 2: Verify attribution
        verified_projects = []
        for project in discovered_projects:
            is_verified, score, evidence = self.verify_attribution(project)
            if is_verified:
                project["verification_score"] = score
                project["verification_evidence"] = evidence
                verified_projects.append(project)
        
        # Step 3: Validate existing links
        validation_results = self.validate_links()
        
        # Step 4: Generate update report
        report = self.update_portfolio(verified_projects, validation_results)
        
        logger.info("=" * 60)
        logger.info("Scan Complete")
        logger.info("=" * 60)
        
        return report


def main():
    """Main entry point"""
    sourcer = PortfolioSourcer()
    report = sourcer.run_full_scan()
    
    print("\n" + "=" * 60)
    print("PORTFOLIO SOURCER REPORT")
    print("=" * 60)
    print(f"\nVerified Projects Found: {len(report.get('verified_projects', []))}")
    print(f"Broken Links: {len(report.get('broken_links', []))}")
    print(f"Broken Images: {len(report.get('broken_images', []))}")
    print(f"\nRecommendations:")
    for rec in report.get('recommendations', []):
        print(f"  - {rec}")
    print("\nFull report saved to portfolio_updates/ directory")


if __name__ == "__main__":
    main()

