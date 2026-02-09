"""Markdown body loading for SKILL.md files."""

from pathlib import Path

from agent_skills.exceptions import SkillParseError


class SkillMarkdownLoader:
    """Loads SKILL.md body using offset from frontmatter parsing."""

    def load_body(self, skill_path: Path, offset: int) -> str:
        """
        Load markdown body starting from offset.

        Args:
            skill_path: Path to the skill directory containing SKILL.md
            offset: Byte offset where the body starts (after second '---' delimiter)

        Returns:
            The markdown body content as a string, with formatting preserved.
            Returns empty string if body is empty or contains only whitespace.

        Raises:
            SkillParseError: If SKILL.md cannot be read
        """
        skill_md_path = skill_path / "SKILL.md"

        if not skill_md_path.exists():
            raise SkillParseError(f"SKILL.md not found at {skill_md_path}")

        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                # Seek to the body offset
                f.seek(offset)

                # Read the rest of the file (the body)
                body = f.read()

                # Return the body as-is to preserve formatting
                # If it's empty or only whitespace, return empty string
                if not body or body.strip() == '':
                    return ''

                return body

        except SkillParseError:
            raise
        except Exception as e:
            raise SkillParseError(f"Error reading SKILL.md body: {e}")
