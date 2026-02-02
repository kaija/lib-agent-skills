"""Unit tests for JSONRenderer."""

import json
from pathlib import Path

import pytest

from agent_skills.models import SkillDescriptor
from agent_skills.prompt.json_renderer import JSONRenderer


class TestJSONRenderer:
    """Tests for JSONRenderer."""
    
    def test_render_empty_list(self):
        """Test rendering empty skills list."""
        renderer = JSONRenderer()
        
        result = renderer.render([], include_location=True)
        
        assert result == "[]"
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed == []
    
    def test_render_single_skill_with_location(self):
        """Test rendering single skill with location."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="data-processor",
                description="Process CSV data",
                path=Path("/path/to/skills/data-processor"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "data-processor"
        assert parsed[0]["description"] == "Process CSV data"
        assert parsed[0]["location"] == "/path/to/skills/data-processor"
    
    def test_render_single_skill_without_location(self):
        """Test rendering single skill without location."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="data-processor",
                description="Process CSV data",
                path=Path("/path/to/skills/data-processor"),
            )
        ]
        
        result = renderer.render(skills, include_location=False)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "data-processor"
        assert parsed[0]["description"] == "Process CSV data"
        assert "location" not in parsed[0]
    
    def test_render_multiple_skills(self):
        """Test rendering multiple skills."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="data-processor",
                description="Process CSV data",
                path=Path("/path/to/skills/data-processor"),
            ),
            SkillDescriptor(
                name="api-client",
                description="Call external APIs",
                path=Path("/path/to/skills/api-client"),
            ),
            SkillDescriptor(
                name="file-manager",
                description="Manage files",
                path=Path("/path/to/skills/file-manager"),
            ),
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert len(parsed) == 3
        
        # Check first skill
        assert parsed[0]["name"] == "data-processor"
        assert parsed[0]["description"] == "Process CSV data"
        assert parsed[0]["location"] == "/path/to/skills/data-processor"
        
        # Check second skill
        assert parsed[1]["name"] == "api-client"
        assert parsed[1]["description"] == "Call external APIs"
        assert parsed[1]["location"] == "/path/to/skills/api-client"
        
        # Check third skill
        assert parsed[2]["name"] == "file-manager"
        assert parsed[2]["description"] == "Manage files"
        assert parsed[2]["location"] == "/path/to/skills/file-manager"
    
    def test_render_with_special_characters(self):
        """Test JSON special character handling."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name='skill-with-"quotes"',
                description='Description with "quotes" and \\ backslashes',
                path=Path("/path/with/special/chars"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Verify it's valid JSON (json.loads will fail if escaping is wrong)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == 'skill-with-"quotes"'
        assert parsed[0]["description"] == 'Description with "quotes" and \\ backslashes'
    
    def test_render_format_structure(self):
        """Test that output has correct JSON structure and formatting."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="test-skill",
                description="Test description",
                path=Path("/test/path"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert isinstance(parsed[0], dict)
        
        # Verify formatting (should be indented)
        assert "\n" in result
        assert "  " in result  # Should have indentation
    
    def test_render_with_complex_paths(self):
        """Test rendering with complex filesystem paths."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="test",
                description="Test",
                path=Path("/home/user/.agent-skills/my-skill-v1.0"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        parsed = json.loads(result)
        assert parsed[0]["location"] == "/home/user/.agent-skills/my-skill-v1.0"
    
    def test_render_preserves_skill_order(self):
        """Test that skills are rendered in the order provided."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(name="zebra", description="Last", path=Path("/z")),
            SkillDescriptor(name="alpha", description="First", path=Path("/a")),
            SkillDescriptor(name="middle", description="Middle", path=Path("/m")),
        ]
        
        result = renderer.render(skills, include_location=False)
        
        parsed = json.loads(result)
        assert parsed[0]["name"] == "zebra"
        assert parsed[1]["name"] == "alpha"
        assert parsed[2]["name"] == "middle"
    
    def test_render_with_unicode_characters(self):
        """Test rendering with unicode characters in skill metadata."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="unicode-skill",
                description="Skill with émojis 🚀 and spëcial çharacters",
                path=Path("/path/to/skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Verify it's valid JSON and unicode is preserved
        parsed = json.loads(result)
        assert parsed[0]["description"] == "Skill with émojis 🚀 and spëcial çharacters"
    
    def test_render_with_long_descriptions(self):
        """Test rendering with very long descriptions."""
        renderer = JSONRenderer()
        
        long_desc = "A " + "very " * 100 + "long description"
        skills = [
            SkillDescriptor(
                name="long-desc-skill",
                description=long_desc,
                path=Path("/path"),
            )
        ]
        
        result = renderer.render(skills, include_location=False)
        
        parsed = json.loads(result)
        assert parsed[0]["description"] == long_desc
    
    def test_render_field_order(self):
        """Test that fields appear in consistent order."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="test",
                description="Test skill",
                path=Path("/test"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        # Parse and verify field order
        parsed = json.loads(result)
        keys = list(parsed[0].keys())
        
        # name should come before description, location should be last
        assert keys.index("name") < keys.index("description")
        if "location" in keys:
            assert keys.index("location") > keys.index("description")
    
    def test_render_with_newlines_in_description(self):
        """Test rendering with newlines in description."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="multiline-skill",
                description="Line 1\nLine 2\nLine 3",
                path=Path("/path"),
            )
        ]
        
        result = renderer.render(skills, include_location=False)
        
        # Verify it's valid JSON and newlines are properly escaped
        parsed = json.loads(result)
        assert parsed[0]["description"] == "Line 1\nLine 2\nLine 3"
    
    def test_render_with_tabs_in_description(self):
        """Test rendering with tabs in description."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="tab-skill",
                description="Column1\tColumn2\tColumn3",
                path=Path("/path"),
            )
        ]
        
        result = renderer.render(skills, include_location=False)
        
        # Verify it's valid JSON and tabs are properly escaped
        parsed = json.loads(result)
        assert parsed[0]["description"] == "Column1\tColumn2\tColumn3"
    
    def test_render_returns_string(self):
        """Test that render always returns a string."""
        renderer = JSONRenderer()
        
        result = renderer.render([], include_location=True)
        assert isinstance(result, str)
        
        skills = [
            SkillDescriptor(name="test", description="test", path=Path("/test"))
        ]
        result = renderer.render(skills, include_location=True)
        assert isinstance(result, str)
    
    def test_render_with_windows_paths(self):
        """Test rendering with Windows-style paths."""
        renderer = JSONRenderer()
        
        skills = [
            SkillDescriptor(
                name="windows-skill",
                description="Test",
                path=Path("C:/Users/Agent/skills/test-skill"),
            )
        ]
        
        result = renderer.render(skills, include_location=True)
        
        parsed = json.loads(result)
        # Path should be converted to string properly
        assert "C:" in parsed[0]["location"] or "C:/" in parsed[0]["location"]
    
    def test_render_json_is_parseable(self):
        """Test that all rendered JSON is parseable."""
        renderer = JSONRenderer()
        
        # Test various edge cases
        test_cases = [
            [],
            [SkillDescriptor(name="a", description="b", path=Path("/c"))],
            [
                SkillDescriptor(name="x", description="y", path=Path("/z")),
                SkillDescriptor(name="1", description="2", path=Path("/3")),
            ],
        ]
        
        for skills in test_cases:
            result = renderer.render(skills, include_location=True)
            # Should not raise exception
            parsed = json.loads(result)
            assert isinstance(parsed, list)
            assert len(parsed) == len(skills)
