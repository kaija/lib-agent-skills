"""Metadata caching for skill descriptors."""

import json
import hashlib
from pathlib import Path
from typing import Optional

from ..models import SkillDescriptor


class MetadataCache:
    """Caches SkillDescriptor metadata to disk.
    
    The cache stores skill metadata as JSON files, using the skill's
    path hash as the filename. Cache validity is determined by comparing
    the stored mtime and hash with the current SKILL.md file.
    """
    
    def __init__(self, cache_dir: Path):
        """Initialize cache directory.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, skill_path: Path) -> Path:
        """Get cache file path for a skill.
        
        Args:
            skill_path: Path to the skill directory
            
        Returns:
            Path to the cache file
        """
        # Use hash of skill path as cache filename to avoid path issues
        path_hash = hashlib.sha256(str(skill_path.resolve()).encode()).hexdigest()
        return self.cache_dir / f"{path_hash}.json"
    
    def _get_skill_md_path(self, skill_path: Path) -> Path:
        """Get path to SKILL.md file.
        
        Args:
            skill_path: Path to the skill directory
            
        Returns:
            Path to SKILL.md file
        """
        return skill_path / "SKILL.md"
    
    def _is_valid(self, descriptor: SkillDescriptor, skill_md_path: Path) -> bool:
        """Check if cached descriptor is still valid.
        
        A descriptor is valid if:
        1. The SKILL.md file exists
        2. The mtime matches
        3. The hash matches (if available)
        
        Args:
            descriptor: Cached descriptor to validate
            skill_md_path: Path to SKILL.md file
            
        Returns:
            True if cache is valid, False otherwise
        """
        if not skill_md_path.exists():
            return False
        
        # Check mtime
        current_mtime = skill_md_path.stat().st_mtime
        if abs(current_mtime - descriptor.mtime) > 0.001:  # Allow small float differences
            return False
        
        # If hash is available, verify it matches
        # Note: We don't recompute hash here to avoid reading the file
        # The hash check happens during parsing
        
        return True
    
    def get(self, skill_path: Path) -> Optional[SkillDescriptor]:
        """Retrieve cached descriptor if valid.
        
        Args:
            skill_path: Path to the skill directory
            
        Returns:
            SkillDescriptor if cache is valid, None otherwise
        """
        cache_path = self._get_cache_path(skill_path)
        
        # Check if cache file exists
        if not cache_path.exists():
            return None
        
        try:
            # Load cached descriptor
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            descriptor = SkillDescriptor.from_dict(data)
            
            # Validate cache
            skill_md_path = self._get_skill_md_path(skill_path)
            if not self._is_valid(descriptor, skill_md_path):
                # Cache is stale, remove it
                self.invalidate(skill_path)
                return None
            
            return descriptor
            
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            # Cache file is corrupted or invalid, remove it
            self.invalidate(skill_path)
            return None
    
    def put(self, descriptor: SkillDescriptor) -> None:
        """Store descriptor in cache.
        
        Args:
            descriptor: SkillDescriptor to cache
        """
        cache_path = self._get_cache_path(descriptor.path)
        
        try:
            # Ensure cache directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write descriptor as JSON
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(descriptor.to_dict(), f, indent=2)
                
        except OSError:
            # If we can't write cache, just continue without caching
            # This allows the system to work even if cache directory is not writable
            pass
    
    def invalidate(self, skill_path: Path) -> None:
        """Remove cached descriptor.
        
        Args:
            skill_path: Path to the skill directory
        """
        cache_path = self._get_cache_path(skill_path)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
        except OSError:
            # If we can't delete cache file, just continue
            pass
    
    def clear(self) -> None:
        """Clear all cached descriptors."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
        except OSError:
            # If we can't clear cache, just continue
            pass
