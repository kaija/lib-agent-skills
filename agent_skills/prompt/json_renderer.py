"""JSON prompt renderer for Agent Skills Runtime."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_skills.models import SkillDescriptor


class JSONRenderer:
    """Renders skills as JSON array.
    
    Produces JSON output in the format:
    [
      {"name": "...", "description": "...", "location": "..."},
      ...
    ]
    """
    
    def render(
        self,
        skills: list["SkillDescriptor"],
        include_location: bool = True
    ) -> str:
        """Render skills as JSON array format.
        
        Args:
            skills: List of skill descriptors to render
            include_location: Whether to include filesystem path in output
            
        Returns:
            JSON string with available skills as array
            
        Example:
            >>> renderer = JSONRenderer()
            >>> skills = [SkillDescriptor(name="test", description="A test skill", path=Path("/test"))]
            >>> print(renderer.render(skills, include_location=True))
            [
              {
                "name": "test",
                "description": "A test skill",
                "location": "/test"
              }
            ]
        """
        skill_list = []
        
        for skill in skills:
            skill_dict = {
                "name": skill.name,
                "description": skill.description,
            }
            
            if include_location:
                skill_dict["location"] = str(skill.path)
            
            skill_list.append(skill_dict)
        
        # Use indent=2 for readable formatting
        return json.dumps(skill_list, indent=2, ensure_ascii=False)
