"""Unit tests for ClaudeXMLRenderer."""

from pathlib import Path

import pytest

from agent_skills.models import SkillDescriptor
from agent_skills.prompt.claude_xml import ClaudeXMLRenderer


class TestClaudeXMLRenderer:
    """Tests for ClaudeXMLRenderer."""
    
    def test_render_empty_list(self):
        """Test rendering empty skills list."""
        renderer = ClaudeXMLRenderer()
        result = renderer.render([], include_location=True)
        
        assert result == "<available_skills>\n</available_skills>"
    
    def test_render_single_skill_with_location(self):
        """Test rendering single skill with location."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="test-skill",
                description="A test skill",
                path=Path("/path/to/skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        assert "<available_skills>" in result
        assert "</available_skills>" in result
        assert 'name="test-skill"' in result
        assert 'description="A test skill"' in result
        assert 'location="/path/to/skill"' in result
        assert "<skill" in result
        assert "/>" in result
    
    def test_render_single_skill_without_location(self):
        """Test rendering single skill without location."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="test-skill",
                description="A test skill",
                path=Path("/path/to/skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=False)
        
        assert "<available_skills>" in result
        assert "</available_skills>" in result
        assert 'name="test-skill"' in result
        assert 'description="A test skill"' in result
        assert "location=" not in result
    
    def test_render_multiple_skills(self):
        """Test rendering multiple skills."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="skill-one",
                description="First skill",
                path=Path("/path/one"),
            ),
            SkillDescriptor(
                name="skill-two",
                description="Second skill",
                path=Path("/path/two"),
            ),
            SkillDescriptor(
                name="skill-three",
                description="Third skill",
                path=Path("/path/three"),
            ),
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Check structure
        assert result.startswith("<available_skills>")
        assert result.endswith("</available_skills>")
        
        # Check all skills are present
        assert 'name="skill-one"' in result
        assert 'name="skill-two"' in result
        assert 'name="skill-three"' in result
        assert 'description="First skill"' in result
        assert 'description="Second skill"' in result
        assert 'description="Third skill"' in result
        assert 'location="/path/one"' in result
        assert 'location="/path/two"' in result
        assert 'location="/path/three"' in result
        
        # Count skill elements
        assert result.count("<skill") == 3
    
    def test_escape_xml_special_characters(self):
        """Test XML special character escaping in attributes."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="test&skill",
                description='A "test" skill with <special> characters & more',
                path=Path("/path/with/special&chars"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Check that special characters are escaped
        assert "&amp;" in result
        assert "&quot;" in result
        assert "&lt;" in result
        assert "&gt;" in result
        
        # Check that raw special characters are not present in attributes
        # (except in the XML tags themselves)
        lines = result.split("\n")
        skill_line = [line for line in lines if "<skill" in line][0]
        
        # In the skill element, & should be escaped
        assert 'name="test&amp;skill"' in skill_line
        assert "&quot;" in skill_line
        assert "&lt;" in skill_line
        assert "&gt;" in skill_line
    
    def test_escape_xml_attr_method(self):
        """Test the _escape_xml_attr method directly."""
        renderer = ClaudeXMLRenderer()
        
        # Test all special characters
        assert renderer._escape_xml_attr("&") == "&amp;"
        assert renderer._escape_xml_attr("<") == "&lt;"
        assert renderer._escape_xml_attr(">") == "&gt;"
        assert renderer._escape_xml_attr('"') == "&quot;"
        assert renderer._escape_xml_attr("'") == "&apos;"
        
        # Test combined
        text = 'Test & "quotes" <tags> \'apostrophe\''
        escaped = renderer._escape_xml_attr(text)
        assert escaped == "Test &amp; &quot;quotes&quot; &lt;tags&gt; &apos;apostrophe&apos;"
        
        # Test normal text unchanged
        assert renderer._escape_xml_attr("normal text") == "normal text"
    
    def test_render_format_structure(self):
        """Test that output has correct XML structure and formatting."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="test-skill",
                description="A test skill",
                path=Path("/path/to/skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        lines = result.split("\n")
        
        # Check line count (opening tag, skill element, closing tag)
        assert len(lines) == 3
        
        # Check opening tag
        assert lines[0] == "<available_skills>"
        
        # Check skill element is indented
        assert lines[1].startswith("  <skill")
        assert lines[1].endswith("/>")
        
        # Check closing tag
        assert lines[2] == "</available_skills>"
    
    def test_render_with_complex_paths(self):
        """Test rendering with complex filesystem paths."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="skill",
                description="Test",
                path=Path("/home/user/.agent-skills/my-skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        assert 'location="/home/user/.agent-skills/my-skill"' in result
    
    def test_render_preserves_skill_order(self):
        """Test that skills are rendered in the order provided."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(name="zebra", description="Last", path=Path("/z")),
            SkillDescriptor(name="alpha", description="First", path=Path("/a")),
            SkillDescriptor(name="middle", description="Middle", path=Path("/m")),
        ]
        
        result = renderer.render(skills, include_location=False)
        
        # Find positions of each skill name in the output
        zebra_pos = result.find('name="zebra"')
        alpha_pos = result.find('name="alpha"')
        middle_pos = result.find('name="middle"')
        
        # Verify order is preserved (not alphabetical)
        assert zebra_pos < alpha_pos < middle_pos
    
    def test_render_with_unicode_characters(self):
        """Test rendering with unicode characters in skill metadata."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="unicode-skill",
                description="A skill with émojis 🚀 and spëcial çharacters",
                path=Path("/path/to/skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Unicode should be preserved (not escaped in XML)
        assert "émojis 🚀" in result
        assert "spëcial çharacters" in result
    
    def test_render_with_long_descriptions(self):
        """Test rendering with very long descriptions."""
        renderer = ClaudeXMLRenderer()
        long_desc = "A " + "very " * 100 + "long description"
        skills = [
            SkillDescriptor(
                name="long-skill",
                description=long_desc,
                path=Path("/path"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Should handle long descriptions without truncation
        assert long_desc in result
        assert 'name="long-skill"' in result
    
    def test_render_attribute_order(self):
        """Test that attributes appear in consistent order."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="test",
                description="Test skill",
                path=Path("/path"),
            )
        ]
        
        result_with_loc = renderer.render(skills, include_location=True)
        
        # Extract the skill line
        skill_line = [line for line in result_with_loc.split("\n") if "<skill" in line][0]
        
        # Check attribute order: name, description, location
        name_pos = skill_line.find('name=')
        desc_pos = skill_line.find('description=')
        loc_pos = skill_line.find('location=')
        
        assert name_pos < desc_pos
        assert desc_pos < loc_pos
    
    def test_render_self_closing_tags(self):
        """Test that skill elements use self-closing tag syntax."""
        renderer = ClaudeXMLRenderer()
        skills = [
            SkillDescriptor(
                name="test",
                description="Test",
                path=Path("/path"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Should use self-closing syntax: <skill ... />
        assert "<skill" in result
        assert "/>" in result
        # Should not have separate closing tag
        assert "</skill>" not in result
