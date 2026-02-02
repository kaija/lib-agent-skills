"""Claude XML prompt renderer for Agent Skills Runtime."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_skills.models import SkillDescriptor


class ClaudeXMLRenderer:
    """Renders skills in Claude XML format.
    
    Produces XML output in the format:
    <available_skills>
      <skill name="..." description="..." location="..." />
      ...
    </available_skills>
    """
    
    def render(
        self,
        skills: list["SkillDescriptor"],
        include_location: bool = True
    ) -> str:
        """Render skills as Claude XML format.
        
        Args:
            skills: List of skill descriptors to render
            include_location: Whether to include filesystem path in output
            
        Returns:
            XML string with available skills
            
        Example:
            >>> renderer = ClaudeXMLRenderer()
            >>> skills = [SkillDescriptor(name="test", description="A test skill", path=Path("/test"))]
            >>> print(renderer.render(skills, include_location=True))
            <available_skills>
              <skill name="test" description="A test skill" location="/test" />
            </available_skills>
        """
        if not skills:
            return "<available_skills>\n</available_skills>"
        
        lines = ["<available_skills>"]
        
        for skill in skills:
            # Escape XML special characters in attributes
            name = self._escape_xml_attr(skill.name)
            description = self._escape_xml_attr(skill.description)
            
            # Build skill element
            attrs = [
                f'name="{name}"',
                f'description="{description}"',
            ]
            
            if include_location:
                location = self._escape_xml_attr(str(skill.path))
                attrs.append(f'location="{location}"')
            
            skill_line = f'  <skill {" ".join(attrs)} />'
            lines.append(skill_line)
        
        lines.append("</available_skills>")
        return "\n".join(lines)
    
    def _escape_xml_attr(self, text: str) -> str:
        """Escape XML special characters for use in attributes.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for XML attributes
        """
        # Replace XML special characters
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&apos;",
        }
        
        for char, escape in replacements.items():
            text = text.replace(char, escape)
        
        return text
