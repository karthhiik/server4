"""Team Handler for Standard Mode.

This module manages team member data and generates team slides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class TeamMember:
    """A team member with their role and credentials."""
    
    name: str
    role: str
    title: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    x_url: Optional[str] = None
    credentials: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TeamSlideData:
    """Data for a team slide."""
    
    title: str
    description: str
    team_members: list[TeamMember]
    layout: str = "grid-3"
    metadata: dict[str, Any] = field(default_factory=dict)


class TeamHandler:
    """Manages team member data and generates team slides."""

    def __init__(self) -> None:
        """Initialize the team handler."""

    async def generate_team_slide(
        self,
        team_data: list[dict[str, Any]],
        purpose: str,
    ) -> TeamSlideData:
        """Generate a team slide from team data.

        Args:
            team_data: List of team member dictionaries
            purpose: Presentation purpose for context

        Returns:
            TeamSlideData with formatted team information
        """
        try:
            # Convert raw team data to TeamMember objects
            team_members = [
                TeamMember(
                    name=member.get("name", ""),
                    role=member.get("role", "Team Member"),
                    title=member.get("title", ""),
                    bio=member.get("bio"),
                    photo_url=member.get("photo_url"),
                    linkedin_url=member.get("linkedin_url"),
                    x_url=member.get("x_url"),
                    credentials=member.get("credentials", []),
                    achievements=member.get("achievements", []),
                )
                for member in team_data
            ]

            # Determine slide title and description based on purpose
            title, description = self._get_purpose_specific_content(purpose)

            # Determine layout based on number of team members
            layout = self._determine_layout(len(team_members))

            team_slide_data = TeamSlideData(
                title=title,
                description=description,
                team_members=team_members,
                layout=layout,
                metadata={
                    "purpose": purpose,
                    "team_size": len(team_members),
                    "generated_at": self._get_timestamp(),
                },
            )

            logger.info(
                "team_slide_generated",
                purpose=purpose,
                team_size=len(team_members),
                layout=layout,
            )

            return team_slide_data

        except Exception as e:
            logger.error(
                "team_slide_generation_error",
                error=str(e),
                purpose=purpose,
                team_size=len(team_data) if team_data else 0,
            )
            # Return a minimal team slide on error
            return TeamSlideData(
                title="Our Team",
                description="Meet the team behind our vision",
                team_members=[],
                layout="grid-3",
                metadata={"error": str(e), "purpose": purpose},
            )

    def _get_purpose_specific_content(self, purpose: str) -> tuple[str, str]:
        """Get purpose-specific title and description for team slide."""
        content_map = {
            "deep_tech": ("Technical Team", "Our engineering and technical leadership"),
            "vc_pitch": ("Founding Team", "The team building the future"),
            "executive_brief": ("Leadership Team", "Executive leadership driving strategy"),
            "trust_compliance": ("Advisory Board", "Expert advisors ensuring compliance and trust"),
            "cinematic_keynote": ("Our Story", "The people behind the vision"),
            "seed_round": ("Founders", "The founders behind the idea"),
            "series_a": ("Leadership", "The team driving growth"),
            "partnership": ("Partnership Team", "Our team dedicated to partnership success"),
            "customer_case": ("Our Team", "The team behind your success"),
            "fundraising_roadshow": ("Management Team", "The team executing our vision"),
            "growth_deck": ("Growth Team", "The team driving our expansion"),
            "market_analysis": ("Research Team", "Our market research and analysis team"),
            "competitive_analysis": ("Strategy Team", "Our competitive intelligence team"),
            "team_deck": ("Our Team", "Meet the team"),
            "financial_projection": ("Finance Team", "Our financial planning team"),
            "product_roadmap": ("Product Team", "The team building our product"),
            "milestone_deck": ("Our Team", "The team behind our achievements"),
            "crisis_management": ("Crisis Response Team", "Leadership managing the response"),
            "expansion_plan": ("Expansion Team", "The team driving our expansion"),
            "advisory_board": ("Advisory Board", "Our esteemed advisors"),
            "strategic_partnership": ("Partnership Team", "Our partnership leadership"),
            "pre_seed_pitch": ("Founders", "The founders with the vision"),
        }

        return content_map.get(purpose, ("Our Team", "Meet the team behind our vision"))

    def _determine_layout(self, team_size: int) -> str:
        """Determine the appropriate layout based on team size."""
        if team_size <= 2:
            return "two-column"
        elif team_size <= 4:
            return "grid-2x2"
        elif team_size <= 6:
            return "grid-3"
        elif team_size <= 9:
            return "grid-3x3"
        else:
            return "grid-4"

    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


__all__ = ["TeamMember", "TeamSlideData", "TeamHandler"]
