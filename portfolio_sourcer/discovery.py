"""
Discovery Engine
Web search and discovery logic for finding portfolio projects
"""

import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """Handles web search and project discovery"""
    
    def __init__(self, config: Dict):
        """Initialize discovery engine with configuration"""
        self.config = config
        self.verification_names = config.get("verification_names", [])
        self.known_brands = config.get("known_brands", [])
        self.known_agencies = config.get("known_agencies", [])
        self.search_sources = config.get("search_sources", [])
        self.linkedin_url = config.get("linkedin_url", "")
        
    def generate_search_queries(self) -> List[str]:
        """
        Generate comprehensive search queries for project discovery
        Returns list of search query strings
        """
        queries = []
        
        # Name-based searches
        for name in self.verification_names:
            queries.extend([
                f'"{name}" advertising campaign',
                f'"{name}" strategy',
                f'"{name}" portfolio',
                f'"{name}" credits',
                f'"{name}" creative strategist',
            ])
            
            # Agency-specific searches
            for agency in self.known_agencies[:3]:  # Top 3 agencies
                queries.append(f'"{name}" {agency}')
        
        # Brand-specific searches
        for brand in self.known_brands:
            for name in self.verification_names[:3]:  # Top 3 name variations
                queries.append(f'"{name}" {brand}')
        
        # Industry publication searches
        for source in self.search_sources:
            for name in self.verification_names[:2]:  # Top 2 name variations
                queries.append(f'site:{source} "{name}"')
        
        # LinkedIn-specific searches
        if self.linkedin_url:
            linkedin_username = self.linkedin_url.split('/')[-1]
            queries.extend([
                f'site:linkedin.com "{self.verification_names[0]}"',
                f'site:linkedin.com/in/{linkedin_username}',
            ])
        
        # Writing-specific searches (Daily Gamecock, etc.)
        writing_sources = self.config.get("writing_sources", [])
        for source in writing_sources:
            source_queries = source.get("queries", [])
            queries.extend(source_queries)
        
        logger.info(f"Generated {len(queries)} search queries")
        return queries
    
    def perform_search(self, query: str, search_api=None) -> List[Dict]:
        """
        Perform web search for a given query
        Args:
            query: Search query string
            search_api: Optional search API function (for future API integration)
        Returns:
            List of search result dictionaries with title, url, snippet
        """
        results = []
        
        # If search API is provided, use it
        if search_api:
            try:
                results = search_api(query)
            except Exception as e:
                logger.error(f"Search API error for '{query}': {e}")
        
        # Fallback: Use web_search tool if available via MCP
        # This would be integrated with the MCP web_search tool
        # For now, return empty results structure
        
        return results
    
    def extract_projects_from_results(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Extract project information from search results
        Args:
            results: List of search result dictionaries
            query: Original search query for context
        Returns:
            List of project dictionaries
        """
        projects = []
        
        for result in results:
            try:
                project = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "source_query": query,
                    "source_engine": result.get("source", "unknown"),
                    "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Only add if URL is valid
                if project["url"] and self._is_valid_url(project["url"]):
                    projects.append(project)
                    
            except Exception as e:
                logger.error(f"Error extracting project from result: {e}")
        
        return projects
    
    def deduplicate_projects(self, projects: List[Dict]) -> List[Dict]:
        """
        Remove duplicate projects based on URL and title similarity
        Args:
            projects: List of project dictionaries
        Returns:
            Deduplicated list of projects
        """
        seen_urls = set()
        seen_titles = set()
        unique = []
        
        for project in projects:
            url = project.get("url", "").lower()
            title = project.get("title", "").lower()
            
            # Normalize URL
            normalized_url = self._normalize_url(url)
            
            if normalized_url and normalized_url not in seen_urls:
                # Check title similarity
                is_similar = False
                for seen_title in seen_titles:
                    if self._calculate_similarity(title, seen_title) > 0.8:
                        is_similar = True
                        break
                
                if not is_similar:
                    seen_urls.add(normalized_url)
                    seen_titles.add(title)
                    unique.append(project)
        
        logger.info(f"Deduplicated {len(projects)} projects to {len(unique)} unique")
        return unique
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            # Remove query params and fragments for comparison
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
            return normalized.lower()
        except Exception:
            return url.lower()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using word overlap
        Returns similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def discover_projects(self, search_api=None, rate_limit: float = 1.0) -> List[Dict]:
        """
        Main discovery method - searches web and returns unique projects
        Args:
            search_api: Optional search API function
            rate_limit: Seconds to wait between searches
        Returns:
            List of discovered project dictionaries
        """
        logger.info("Starting project discovery...")
        
        queries = self.generate_search_queries()
        all_projects = []
        
        for i, query in enumerate(queries):
            logger.debug(f"Searching [{i+1}/{len(queries)}]: {query}")
            
            try:
                results = self.perform_search(query, search_api)
                projects = self.extract_projects_from_results(results, query)
                all_projects.extend(projects)
                
                # Rate limiting
                if i < len(queries) - 1:
                    time.sleep(rate_limit)
                    
            except Exception as e:
                logger.error(f"Error searching '{query}': {e}")
        
        # Deduplicate
        unique_projects = self.deduplicate_projects(all_projects)
        
        logger.info(f"Discovery complete: {len(unique_projects)} unique projects found")
        return unique_projects

