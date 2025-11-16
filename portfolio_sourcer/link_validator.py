"""
Link Validator
Validates external links, images, and video embeds in the portfolio
"""

import logging
import re
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LinkValidator:
    """Validates links, images, and video embeds"""
    
    def __init__(self, portfolio_file: str = "index.html"):
        """Initialize link validator"""
        self.portfolio_file = portfolio_file
        self.broken_links = []
        self.broken_images = []
        self.broken_videos = []
        
    def validate_all(self) -> Dict[str, List[Dict]]:
        """
        Validate all links, images, and videos in portfolio
        Returns:
            Dictionary with broken_links, broken_images, broken_videos
        """
        logger.info(f"Validating links in {self.portfolio_file}...")
        
        try:
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Validate links
            self._validate_links(soup)
            
            # Validate images
            self._validate_images(soup)
            
            # Validate videos (iframes)
            self._validate_videos(soup)
            
            logger.info(f"Validation complete: {len(self.broken_links)} broken links, "
                       f"{len(self.broken_images)} broken images, "
                       f"{len(self.broken_videos)} broken videos")
            
        except Exception as e:
            logger.error(f"Error validating links: {e}")
        
        return {
            "broken_links": self.broken_links,
            "broken_images": self.broken_images,
            "broken_videos": self.broken_videos
        }
    
    def _validate_links(self, soup: BeautifulSoup):
        """Validate all anchor links"""
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            if self._is_external_link(href):
                if not self._check_link_valid(href):
                    self.broken_links.append({
                        "url": href,
                        "element": str(link)[:200],  # First 200 chars of HTML
                        "text": link.get_text(strip=True)[:100],
                        "type": "link"
                    })
    
    def _validate_images(self, soup: BeautifulSoup):
        """Validate all image sources"""
        for img in soup.find_all('img', src=True):
            src = img['src']
            
            if self._is_external_link(src):
                if not self._check_link_valid(src):
                    self.broken_images.append({
                        "url": src,
                        "alt": img.get('alt', ''),
                        "type": "image"
                    })
    
    def _validate_videos(self, soup: BeautifulSoup):
        """Validate all video embeds (iframes)"""
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src']
            
            if not self._check_video_valid(src):
                self.broken_videos.append({
                    "url": src,
                    "type": self._get_video_type(src),
                    "element": "iframe"
                })
    
    def _is_external_link(self, url: str) -> bool:
        """Check if URL is external (not a local anchor or file)"""
        if not url:
            return False
        
        # Skip anchors, javascript, mailto, tel
        if url.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            return False
        
        # Check if it's a full URL
        parsed = urlparse(url)
        return bool(parsed.netloc)
    
    def _check_link_valid(self, url: str) -> bool:
        """Check if a link is valid and accessible"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use HEAD request for efficiency
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            return response.status_code < 400
            
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout checking {url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error checking {url}: {e}")
            return False
    
    def _check_video_valid(self, url: str) -> bool:
        """Check if video embed URL is valid"""
        # YouTube validation
        if 'youtube.com' in url or 'youtu.be' in url:
            return self._validate_youtube_url(url)
        
        # Vimeo validation
        if 'vimeo.com' in url:
            return self._validate_vimeo_url(url)
        
        # Other video platforms - try standard link check
        return self._check_link_valid(url)
    
    def _validate_youtube_url(self, url: str) -> bool:
        """Validate YouTube URL format and accessibility"""
        # Check URL format
        youtube_patterns = [
            r'youtube\.com/embed/[a-zA-Z0-9_-]+',
            r'youtu\.be/[a-zA-Z0-9_-]+',
            r'youtube\.com/watch\?v=[a-zA-Z0-9_-]+'
        ]
        
        format_valid = any(re.search(pattern, url) for pattern in youtube_patterns)
        if not format_valid:
            return False
        
        # Extract video ID
        video_id = self._extract_youtube_id(url)
        if not video_id:
            return False
        
        # Check if video exists using oEmbed API
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = requests.get(oembed_url, timeout=10)
            return response.status_code == 200
        except Exception:
            # Fallback: assume valid if format is correct
            return True
    
    def _validate_vimeo_url(self, url: str) -> bool:
        """Validate Vimeo URL format"""
        vimeo_patterns = [
            r'vimeo\.com/\d+',
            r'player\.vimeo\.com/video/\d+'
        ]
        
        return any(re.search(pattern, url) for pattern in vimeo_patterns)
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _get_video_type(self, url: str) -> str:
        """Determine video platform type"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return "youtube"
        elif 'vimeo.com' in url:
            return "vimeo"
        else:
            return "unknown"

