"""
Verification System
Triple-verification system for attributing projects to Joshua German
"""

import logging
import re
import requests
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class VerificationSystem:
    """Handles attribution verification using multiple methods"""
    
    def __init__(self, config: Dict):
        """Initialize verification system with configuration"""
        self.config = config
        self.verification_names = config.get("verification_names", [])
        self.known_agencies = config.get("known_agencies", [])
        self.known_brands = config.get("known_brands", [])
        self.verification_threshold = config.get("verification_threshold", 3)
        self.linkedin_url = config.get("linkedin_url", "")
        self.portfolio_url = config.get("portfolio_url", "")
        
    def verify_attribution(self, project: Dict) -> Tuple[bool, int, List[str]]:
        """
        Triple-verification system for Joshua German attribution
        Args:
            project: Project dictionary with url, title, snippet
        Returns:
            Tuple of (is_verified, verification_score, evidence_sources)
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
                    verification_score += min(name_mentions, 3)  # Cap at 3 points
                    evidence_sources.append(f"Name mentioned {name_mentions} time(s) on page")
            
            # Method 2: Check for agency associations
            if content:
                agency_matches = self._check_agency_associations(content)
                if agency_matches:
                    verification_score += len(agency_matches)
                    evidence_sources.append(f"Associated with agencies: {', '.join(agency_matches)}")
            
            # Method 3: Check for brand associations
            if content:
                brand_match = self._check_brand_association(content)
                if brand_match:
                    verification_score += 1
                    evidence_sources.append(f"Associated with known brand: {brand_match}")
            
            # Method 4: Check LinkedIn profile mention (if accessible)
            linkedin_match = self._check_linkedin_mention(project, content or "")
            if linkedin_match:
                verification_score += 2  # LinkedIn is worth more
                evidence_sources.append("Mentioned on LinkedIn profile")
            
            # Method 5: Check for portfolio site mentions
            if self.portfolio_url:
                portfolio_match = self._check_portfolio_mention(url, content or "")
                if portfolio_match:
                    verification_score += 1
                    evidence_sources.append("Mentioned on portfolio site")
            
        except Exception as e:
            logger.error(f"Error verifying attribution: {e}")
        
        is_verified = verification_score >= self.verification_threshold
        
        if is_verified:
            logger.info(f"✓ Verified (score: {verification_score}): {project.get('title', 'Unknown')}")
        else:
            logger.debug(f"✗ Not verified (score: {verification_score}): {project.get('title', 'Unknown')}")
        
        return is_verified, verification_score, evidence_sources
    
    def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and parse page content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            return soup.get_text()
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None
    
    def _count_name_mentions(self, content: str) -> int:
        """Count how many times Joshua German's name appears in content"""
        count = 0
        content_lower = content.lower()
        
        for name in self.verification_names:
            # Case-insensitive search with word boundaries
            pattern = re.compile(r'\b' + re.escape(name.lower()) + r'\b', re.IGNORECASE)
            matches = pattern.findall(content)
            count += len(matches)
        
        return count
    
    def _check_agency_associations(self, content: str) -> List[str]:
        """Check if content mentions known agencies"""
        found_agencies = []
        content_lower = content.lower()
        
        for agency in self.known_agencies:
            # Normalize agency name for matching
            agency_normalized = agency.lower().replace('\\', '').replace('/', '')
            if agency_normalized in content_lower:
                found_agencies.append(agency)
        
        return found_agencies
    
    def _check_brand_association(self, content: str) -> Optional[str]:
        """Check if content is associated with known brands"""
        content_lower = content.lower()
        
        for brand in self.known_brands:
            brand_normalized = brand.lower().replace("'", "").replace(" ", "")
            if brand_normalized in content_lower or brand.lower() in content_lower:
                return brand
        
        return None
    
    def _check_linkedin_mention(self, project: Dict, content: str) -> bool:
        """
        Check if project is mentioned on LinkedIn profile
        Note: This is a placeholder - full implementation would require LinkedIn API
        """
        # Check if URL contains LinkedIn
        url = project.get("url", "").lower()
        if "linkedin.com" in url:
            return True
        
        # Check if content mentions LinkedIn profile
        if self.linkedin_url and self.linkedin_url.lower() in content.lower():
            return True
        
        return False
    
    def _check_portfolio_mention(self, url: str, content: str) -> bool:
        """Check if URL/content references portfolio site"""
        if not self.portfolio_url:
            return False
        
        portfolio_domains = [
            "jgerms20.github.io",
            "joshuagerman.com",
            "joshua-german.com"
        ]
        
        url_lower = url.lower()
        for domain in portfolio_domains:
            if domain in url_lower:
                return True
        
        return False
    
    def verify_multiple_projects(self, projects: List[Dict]) -> List[Dict]:
        """
        Verify multiple projects and return verified ones
        Args:
            projects: List of project dictionaries
        Returns:
            List of verified projects with verification metadata
        """
        verified_projects = []
        
        for project in projects:
            is_verified, score, evidence = self.verify_attribution(project)
            
            if is_verified:
                project["verification_score"] = score
                project["verification_evidence"] = evidence
                project["verified"] = True
                verified_projects.append(project)
            else:
                project["verification_score"] = score
                project["verification_evidence"] = evidence
                project["verified"] = False
        
        logger.info(f"Verified {len(verified_projects)} out of {len(projects)} projects")
        return verified_projects

