"""
Report Generator
Generates JSON reports with actionable recommendations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates portfolio update reports"""
    
    def __init__(self, output_dir: str = "portfolio_updates"):
        """Initialize report generator"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(self, 
                       verified_projects: List[Dict],
                       validation_results: Dict,
                       portfolio_structure: Dict = None,
                       new_projects: List[Dict] = None) -> Dict:
        """
        Generate comprehensive portfolio update report
        Args:
            verified_projects: List of verified projects
            validation_results: Dictionary with broken_links, broken_images, broken_videos
            portfolio_structure: Portfolio structure information
            new_projects: Projects not currently in portfolio
        Returns:
            Report dictionary
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self._generate_summary(verified_projects, validation_results, new_projects),
            "verified_projects": verified_projects,
            "validation_results": validation_results,
            "new_projects": new_projects or [],
            "recommendations": self._generate_recommendations(
                verified_projects, 
                validation_results, 
                new_projects
            ),
            "portfolio_structure": portfolio_structure or {}
        }
        
        return report
    
    def _generate_summary(self, 
                         verified_projects: List[Dict],
                         validation_results: Dict,
                         new_projects: List[Dict] = None) -> Dict:
        """Generate summary statistics"""
        broken_links = validation_results.get("broken_links", [])
        broken_images = validation_results.get("broken_images", [])
        broken_videos = validation_results.get("broken_videos", [])
        
        return {
            "total_verified_projects": len(verified_projects),
            "new_projects_found": len(new_projects) if new_projects else 0,
            "broken_links_count": len(broken_links),
            "broken_images_count": len(broken_images),
            "broken_videos_count": len(broken_videos),
            "total_issues": len(broken_links) + len(broken_images) + len(broken_videos)
        }
    
    def _generate_recommendations(self,
                                  verified_projects: List[Dict],
                                  validation_results: Dict,
                                  new_projects: List[Dict] = None) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Broken links recommendations
        broken_links = validation_results.get("broken_links", [])
        if broken_links:
            recommendations.append(
                f"Fix {len(broken_links)} broken link(s). Check URLs for updates or replacements."
            )
        
        # Broken images recommendations
        broken_images = validation_results.get("broken_images", [])
        if broken_images:
            recommendations.append(
                f"Replace {len(broken_images)} broken image(s). Verify image URLs or upload new images."
            )
        
        # Broken videos recommendations
        broken_videos = validation_results.get("broken_videos", [])
        if broken_videos:
            recommendations.append(
                f"Fix {len(broken_videos)} broken video embed(s). Verify YouTube/Vimeo URLs."
            )
        
        # New projects recommendations
        if new_projects:
            recommendations.append(
                f"Consider adding {len(new_projects)} newly discovered verified project(s) to portfolio."
            )
            # Add specific project suggestions
            for project in new_projects[:5]:  # Top 5
                title = project.get('title', 'Unknown')
                score = project.get('verification_score', 0)
                recommendations.append(
                    f"  - '{title}' (verification score: {score})"
                )
        
        # General maintenance
        if not broken_links and not broken_images and not broken_videos:
            recommendations.append("All links, images, and videos are valid. Portfolio is healthy!")
        
        return recommendations
    
    def suggest_portfolio_section(self, project: Dict) -> str:
        """
        Suggest which portfolio section a project should go in
        Args:
            project: Project dictionary
        Returns:
            Suggested section name
        """
        title = project.get("title", "").lower()
        snippet = project.get("snippet", "").lower()
        url = project.get("url", "").lower()
        
        combined_text = f"{title} {snippet} {url}"
        
        # Check for brand work indicators
        brand_keywords = ["campaign", "advertising", "brand", "commercial", "spot", "ad"]
        if any(keyword in combined_text for keyword in brand_keywords):
            return "campaigns"
        
        # Check for podcast indicators
        if "podcast" in combined_text:
            return "podcast"
        
        # Check for writing indicators
        if any(keyword in combined_text for keyword in ["article", "writing", "essay", "blog"]):
            return "writing"
        
        # Check for AI projects
        if any(keyword in combined_text for keyword in ["ai", "tool", "github", "prototype"]):
            return "ai-projects"
        
        # Default to campaigns
        return "campaigns"
    
    def save_report(self, report: Dict) -> Path:
        """
        Save report to JSON file
        Args:
            report: Report dictionary
        Returns:
            Path to saved report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"update_report_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to {filepath}")
        return filepath
    
    def generate_summary_text(self, report: Dict) -> str:
        """Generate human-readable summary text"""
        summary = report.get("summary", {})
        recommendations = report.get("recommendations", [])
        
        text = "=" * 60 + "\n"
        text += "PORTFOLIO SOURCER REPORT\n"
        text += "=" * 60 + "\n\n"
        
        text += f"Verified Projects Found: {summary.get('total_verified_projects', 0)}\n"
        text += f"New Projects Discovered: {summary.get('new_projects_found', 0)}\n"
        text += f"Broken Links: {summary.get('broken_links_count', 0)}\n"
        text += f"Broken Images: {summary.get('broken_images_count', 0)}\n"
        text += f"Broken Videos: {summary.get('broken_videos_count', 0)}\n"
        text += f"Total Issues: {summary.get('total_issues', 0)}\n\n"
        
        if recommendations:
            text += "Recommendations:\n"
            for rec in recommendations:
                text += f"  - {rec}\n"
        
        text += "\n" + "=" * 60 + "\n"
        text += f"Full report saved to: {self.output_dir}\n"
        text += "=" * 60 + "\n"
        
        return text

