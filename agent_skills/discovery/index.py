"""Skill indexing for discovered skills."""

from pathlib import Path

from agent_skills.exceptions import SkillParseError
from agent_skills.models import SkillDescriptor
from agent_skills.parsing.frontmatter import FrontmatterParser


class SkillIndexer:
    """Creates SkillDescriptor objects from discovered skill paths.
    
    The indexer parses frontmatter from each skill's SKILL.md file and
    creates a SkillDescriptor object containing the metadata. It handles
    parsing errors gracefully, logging them and continuing with other skills.
    """
    
    def __init__(self):
        """Initialize the skill indexer."""
        self.parser = FrontmatterParser()
    
    def index_skills(self, skill_paths: list[Path]) -> list[SkillDescriptor]:
        """Parse frontmatter for each discovered skill and create SkillDescriptor objects.
        
        Args:
            skill_paths: List of paths to skill directories (containing SKILL.md)
            
        Returns:
            List of SkillDescriptor objects for successfully parsed skills
            
        Note:
            Parsing errors are handled gracefully - skills that fail to parse
            are skipped and an error message is printed. This allows the system
            to continue indexing other valid skills.
            
        Example:
            >>> indexer = SkillIndexer()
            >>> scanner = SkillScanner()
            >>> skill_paths = scanner.scan([Path("./skills")])
            >>> descriptors = indexer.index_skills(skill_paths)
            >>> print(f"Indexed {len(descriptors)} skills")
        """
        descriptors = []
        
        for skill_path in skill_paths:
            try:
                descriptor = self._create_descriptor(skill_path)
                descriptors.append(descriptor)
            except SkillParseError as e:
                # Handle parsing errors gracefully - log and continue
                print(f"Warning: Failed to parse skill at {skill_path}: {e}")
                continue
            except Exception as e:
                # Catch any unexpected errors
                print(f"Warning: Unexpected error parsing skill at {skill_path}: {e}")
                continue
        
        return descriptors
    
    def _create_descriptor(self, skill_path: Path) -> SkillDescriptor:
        """Create a SkillDescriptor from a skill directory path.
        
        Args:
            skill_path: Path to the skill directory
            
        Returns:
            SkillDescriptor object with parsed metadata
            
        Raises:
            SkillParseError: If parsing fails or required fields are missing
        """
        # Parse frontmatter
        metadata, body_offset = self.parser.parse(skill_path)
        
        # Extract the hash that was computed during parsing
        frontmatter_hash = metadata.pop('_frontmatter_hash', '')
        
        # Get modification time of SKILL.md
        skill_md_path = skill_path / "SKILL.md"
        mtime = skill_md_path.stat().st_mtime if skill_md_path.exists() else 0.0
        
        # Create SkillDescriptor
        descriptor = SkillDescriptor(
            name=metadata['name'],
            description=metadata['description'],
            path=skill_path,
            license=metadata.get('license'),
            compatibility=metadata.get('compatibility'),
            metadata=metadata.get('metadata'),
            allowed_tools=metadata.get('allowed_tools'),
            hash=frontmatter_hash,
            mtime=mtime,
        )
        
        return descriptor
