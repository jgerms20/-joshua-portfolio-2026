"""
Portfolio Parser
Parses HTML to extract links, projects, and structure information
"""

import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PortfolioParser:
    """Parses portfolio HTML to extract structure and metadata"""
    
    def __init__(self, portfolio_file: str = "index.html"):
        """Initialize portfolio parser"""
        self.portfolio_file = portfolio_file
        self.soup = None
        self._load_portfolio()
    
    def _load_portfolio(self):
        """Load and parse portfolio HTML"""
        try:
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.soup = BeautifulSoup(html_content, 'html.parser')
            logger.info(f"Loaded portfolio: {self.portfolio_file}")
        except Exception as e:
            logger.error(f"Error loading portfolio: {e}")
            self.soup = None
    
    def extract_all_links(self) -> List[Dict]:
        """Extract all external links from portfolio"""
        if not self.soup:
            return []
        
        links = []
        
        # Extract anchor links
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            if self._is_external_link(href):
                links.append({
                    "url": href,
                    "type": "link",
                    "text": link.get_text(strip=True)[:100],
                    "element": "a"
                })
        
        # Extract image sources
        for img in self.soup.find_all('img', src=True):
            src = img['src']
            if self._is_external_link(src):
                links.append({
                    "url": src,
                    "type": "image",
                    "alt": img.get('alt', ''),
                    "element": "img"
                })
        
        # Extract iframe sources
        for iframe in self.soup.find_all('iframe', src=True):
            src = iframe['src']
            if self._is_external_link(src):
                links.append({
                    "url": src,
                    "type": "video",
                    "element": "iframe"
                })
        
        logger.info(f"Extracted {len(links)} external links")
        return links
    
    def extract_projects(self) -> List[Dict]:
        """Extract existing project information from portfolio"""
        if not self.soup:
            return []
        
        projects = []
        
        # Find all case study sections
        case_studies = self.soup.find_all('section', class_=re.compile(r'case-study'))
        
        for case_study in case_studies:
            project = {}
            
            # Extract title
            title_elem = case_study.find(['h2', 'h3'], class_=re.compile(r'title|case-study-title'))
            if title_elem:
                project['title'] = title_elem.get_text(strip=True)
            
            # Extract ID
            project_id = case_study.get('id', '')
            if project_id:
                project['id'] = project_id
            
            # Extract brand name from breadcrumb or title
            breadcrumb = case_study.find(class_=re.compile(r'breadcrumb'))
            if breadcrumb:
                breadcrumb_text = breadcrumb.get_text(strip=True)
                project['breadcrumb'] = breadcrumb_text
            
            # Extract meta information
            meta_items = case_study.find_all(class_=re.compile(r'meta-item|meta-value'))
            for meta in meta_items:
                label = meta.find_previous(class_=re.compile(r'meta-label'))
                if label:
                    label_text = label.get_text(strip=True).lower()
                    value = meta.get_text(strip=True)
                    project[label_text] = value
            
            # Extract videos
            videos = []
            for iframe in case_study.find_all('iframe', src=True):
                src = iframe.get('src', '')
                if 'youtube.com' in src or 'vimeo.com' in src:
                    videos.append(src)
            if videos:
                project['videos'] = videos
            
            if project:
                projects.append(project)
        
        logger.info(f"Extracted {len(projects)} existing projects")
        return projects
    
    def extract_brand_names(self) -> Set[str]:
        """Extract brand names from portfolio filters and sections"""
        if not self.soup:
            return set()
        
        brands = set()
        
        # Extract from filter buttons
        filter_buttons = self.soup.find_all('button', class_=re.compile(r'filter-btn'))
        for button in filter_buttons:
            brand_text = button.get_text(strip=True)
            if brand_text.lower() != 'all':
                brands.add(brand_text)
        
        # Extract from brand cards
        brand_cards = self.soup.find_all(class_=re.compile(r'brand-card|brand-title'))
        for card in brand_cards:
            brand_text = card.get_text(strip=True)
            if brand_text:
                brands.add(brand_text)
        
        logger.info(f"Extracted {len(brands)} brand names")
        return brands
    
    def compare_with_discovered(self, discovered_projects: List[Dict]) -> List[Dict]:
        """
        Compare discovered projects with existing portfolio projects
        Args:
            discovered_projects: List of discovered project dictionaries
        Returns:
            List of new projects not in portfolio
        """
        existing_projects = self.extract_projects()
        existing_titles = {p.get('title', '').lower() for p in existing_projects}
        existing_ids = {p.get('id', '') for p in existing_projects}
        
        new_projects = []
        
        for discovered in discovered_projects:
            discovered_title = discovered.get('title', '').lower()
            
            # Check if title matches existing project
            is_new = True
            for existing_title in existing_titles:
                if self._titles_similar(discovered_title, existing_title):
                    is_new = False
                    break
            
            # Check if URL matches existing project section
            discovered_url = discovered.get('url', '')
            if discovered_url:
                for existing_id in existing_ids:
                    if existing_id in discovered_url.lower():
                        is_new = False
                        break
            
            if is_new:
                new_projects.append(discovered)
        
        logger.info(f"Found {len(new_projects)} new projects not in portfolio")
        return new_projects
    
    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.7) -> bool:
        """Check if two titles are similar"""
        if not title1 or not title2:
            return False
        
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0.0
        return similarity >= threshold
    
    def _is_external_link(self, url: str) -> bool:
        """Check if URL is external"""
        if not url:
            return False
        
        if url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            return False
        
        parsed = urlparse(url)
        return bool(parsed.netloc)
    
    def get_portfolio_structure(self) -> Dict:
        """Get overall portfolio structure information"""
        if not self.soup:
            return {}
        
        structure = {
            "sections": [],
            "total_links": len(self.extract_all_links()),
            "total_projects": len(self.extract_projects()),
            "brands": list(self.extract_brand_names())
        }
        
        # Extract section IDs
        sections = self.soup.find_all('section', id=True)
        for section in sections:
            section_id = section.get('id', '')
            section_title = section.find(['h1', 'h2', 'h3'])
            structure["sections"].append({
                "id": section_id,
                "title": section_title.get_text(strip=True) if section_title else ""
            })
        
        return structure

