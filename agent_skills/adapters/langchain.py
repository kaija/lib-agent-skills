"""LangChain adapter for Agent Skills Runtime.

This module provides LangChain BaseTool implementations for all skill operations:
- SkillsListTool: List all available skills
- SkillsActivateTool: Load skill instructions
- SkillsReadTool: Read references and assets
- SkillsRunTool: Execute scripts
- SkillsSearchTool: Full-text search in references

All tools return unified JSON responses using the ToolResponse format and apply
ResourcePolicy and ExecutionPolicy for security.
"""

import json
from typing import Any, Optional, Type

from pydantic import BaseModel, Field

try:
    from langchain.tools import BaseTool
except ImportError:
    raise ImportError(
        "LangChain is required for this adapter. "
        "Install it with: pip install langchain"
    )

from agent_skills.adapters.tool_response import (
    build_error_response,
    build_execution_response,
    build_instructions_response,
    build_metadata_response,
    build_reference_response,
    build_asset_response,
    build_search_response,
)
from agent_skills.resources.reader import FullTextSearcher
from agent_skills.runtime.repository import SkillsRepository


class SkillsListInput(BaseModel):
    """Input schema for skills.list tool."""
    q: Optional[str] = Field(None, description="Optional filter query to search skill names and descriptions")


class SkillsListTool(BaseTool):
    """LangChain tool for listing all available skills.
    
    This tool returns metadata for all discovered skills in the repository.
    Optionally filters skills by a query string matching name or description.
    """
    
    name: str = "skills_list"
    description: str = (
        "List all available skills with metadata (name, description, path, etc.). "
        "Optionally filter by query string matching skill names or descriptions."
    )
    args_schema: Type[BaseModel] = SkillsListInput
    
    # Custom field for repository - use Any to avoid Pydantic validation issues
    repository: Any
    
    def __init__(self, repository: SkillsRepository, **kwargs):
        """Initialize with repository.
        
        Args:
            repository: SkillsRepository instance
        """
        super().__init__(repository=repository, **kwargs)
    
    def _run(self, q: Optional[str] = None) -> str:
        """Execute tool and return JSON response.
        
        Args:
            q: Optional filter query
            
        Returns:
            JSON string containing ToolResponse
        """
        try:
            # Get all skills
            skills = self.repository.list()
            
            # Filter by query if provided
            if q:
                query_lower = q.lower()
                skills = [
                    skill for skill in skills
                    if query_lower in skill.name.lower() or query_lower in skill.description.lower()
                ]
            
            # Build response
            response = build_metadata_response(
                skill_name="all",
                descriptors=skills,
                meta={"query": q, "count": len(skills)},
            )
            
            return json.dumps(response.to_dict(), indent=2)
        
        except Exception as e:
            error_response = build_error_response(
                skill_name="all",
                error=e,
                include_traceback=False,
            )
            return json.dumps(error_response.to_dict(), indent=2)


class SkillsActivateInput(BaseModel):
    """Input schema for skills.activate tool."""
    name: str = Field(..., description="Name of the skill to activate")


class SkillsActivateTool(BaseTool):
    """LangChain tool for activating a skill and loading its instructions.
    
    This tool loads the SKILL.md body content for a specific skill.
    The content is cached after first load for performance.
    """
    
    name: str = "skills_activate"
    description: str = (
        "Activate a skill and load its instructions from SKILL.md. "
        "Returns the full markdown body with usage instructions, examples, and guidance."
    )
    args_schema: Type[BaseModel] = SkillsActivateInput
    
    repository: Any
    
    def __init__(self, repository: SkillsRepository, **kwargs):
        """Initialize with repository.
        
        Args:
            repository: SkillsRepository instance
        """
        super().__init__(repository=repository, **kwargs)
    
    def _run(self, name: str) -> str:
        """Execute tool and return JSON response.
        
        Args:
            name: Skill name
            
        Returns:
            JSON string containing ToolResponse
        """
        try:
            # Open skill handle
            handle = self.repository.open(name)
            
            # Load instructions (lazy loaded and cached)
            instructions = handle.instructions()
            
            # Build response
            response = build_instructions_response(
                skill_name=name,
                instructions=instructions,
                skill_path="SKILL.md",
                meta={},
            )
            
            return json.dumps(response.to_dict(), indent=2)
        
        except Exception as e:
            error_response = build_error_response(
                skill_name=name,
                error=e,
                path="SKILL.md",
                include_traceback=False,
            )
            return json.dumps(error_response.to_dict(), indent=2)


class SkillsReadInput(BaseModel):
    """Input schema for skills.read tool."""
    name: str = Field(..., description="Name of the skill")
    path: str = Field(..., description="Relative path to file in references/ or assets/ directory")
    max_bytes: Optional[int] = Field(None, description="Maximum bytes to read (optional)")


class SkillsReadTool(BaseTool):
    """LangChain tool for reading skill resources.
    
    This tool reads files from a skill's references/ or assets/ directories.
    Text files are returned as strings, binary files as base64-encoded strings.
    """
    
    name: str = "skills_read"
    description: str = (
        "Read a file from a skill's references/ or assets/ directory. "
        "Provide the skill name and relative path (e.g., 'api-docs.md' for references/api-docs.md). "
        "Text files are returned as strings, binary files as base64-encoded content."
    )
    args_schema: Type[BaseModel] = SkillsReadInput
    
    repository: Any
    
    def __init__(self, repository: SkillsRepository, **kwargs):
        """Initialize with repository.
        
        Args:
            repository: SkillsRepository instance
        """
        super().__init__(repository=repository, **kwargs)
    
    def _run(self, name: str, path: str, max_bytes: Optional[int] = None) -> str:
        """Execute tool and return JSON response.
        
        Args:
            name: Skill name
            path: Relative path to file
            max_bytes: Optional max bytes to read
            
        Returns:
            JSON string containing ToolResponse
        """
        try:
            # Open skill handle
            handle = self.repository.open(name)
            
            # Determine if this is a reference or asset based on path
            # If path starts with "assets/", treat as asset, otherwise reference
            if path.startswith("assets/"):
                # Read as asset (binary)
                asset_path = path[7:]  # Remove "assets/" prefix
                content = handle.read_asset(asset_path, max_bytes=max_bytes)
                
                # Build asset response
                response = build_asset_response(
                    skill_name=name,
                    asset_path=path,
                    content=content,
                    truncated=False,  # TODO: Get truncated flag from handle
                    meta={},
                )
            else:
                # Read as reference (text)
                # Remove "references/" prefix if present
                ref_path = path[11:] if path.startswith("references/") else path
                content = handle.read_reference(ref_path, max_bytes=max_bytes)
                
                # Build reference response
                response = build_reference_response(
                    skill_name=name,
                    reference_path=path if path.startswith("references/") else f"references/{path}",
                    content=content,
                    truncated=False,  # TODO: Get truncated flag from handle
                    meta={},
                )
            
            return json.dumps(response.to_dict(), indent=2)
        
        except Exception as e:
            error_response = build_error_response(
                skill_name=name,
                error=e,
                path=path,
                include_traceback=False,
            )
            return json.dumps(error_response.to_dict(), indent=2)


class SkillsRunInput(BaseModel):
    """Input schema for skills.run tool."""
    name: str = Field(..., description="Name of the skill")
    script_path: str = Field(..., description="Relative path to script in scripts/ directory")
    args: Optional[list[str]] = Field(None, description="Command-line arguments for the script")
    stdin: Optional[str] = Field(None, description="Standard input for the script")
    timeout_s: Optional[int] = Field(None, description="Timeout in seconds (optional)")


class SkillsRunTool(BaseTool):
    """LangChain tool for executing skill scripts.
    
    This tool executes scripts from a skill's scripts/ directory with
    comprehensive security policy enforcement.
    """
    
    name: str = "skills_run"
    description: str = (
        "Execute a script from a skill's scripts/ directory. "
        "Provide the skill name and relative path (e.g., 'process.py' for scripts/process.py). "
        "Optionally provide command-line arguments, stdin, and timeout. "
        "Returns execution result with exit code, stdout, stderr, and duration."
    )
    args_schema: Type[BaseModel] = SkillsRunInput
    
    repository: Any
    
    def __init__(self, repository: SkillsRepository, **kwargs):
        """Initialize with repository.
        
        Args:
            repository: SkillsRepository instance
        """
        super().__init__(repository=repository, **kwargs)
    
    def _run(
        self,
        name: str,
        script_path: str,
        args: Optional[list[str]] = None,
        stdin: Optional[str] = None,
        timeout_s: Optional[int] = None
    ) -> str:
        """Execute tool and return JSON response.
        
        Args:
            name: Skill name
            script_path: Relative path to script
            args: Optional command-line arguments
            stdin: Optional standard input
            timeout_s: Optional timeout in seconds
            
        Returns:
            JSON string containing ToolResponse
        """
        try:
            # Open skill handle
            handle = self.repository.open(name)
            
            # Remove "scripts/" prefix if present
            script_rel_path = script_path[8:] if script_path.startswith("scripts/") else script_path
            
            # Execute script
            result = handle.run_script(
                relpath=script_rel_path,
                args=args,
                stdin=stdin,
                timeout_s=timeout_s,
            )
            
            # Build execution response
            response = build_execution_response(
                skill_name=name,
                script_path=script_path if script_path.startswith("scripts/") else f"scripts/{script_path}",
                result=result,
                meta={},
            )
            
            return json.dumps(response.to_dict(), indent=2)
        
        except Exception as e:
            error_response = build_error_response(
                skill_name=name,
                error=e,
                path=script_path,
                include_traceback=False,
            )
            return json.dumps(error_response.to_dict(), indent=2)


class SkillsSearchInput(BaseModel):
    """Input schema for skills.search tool."""
    name: str = Field(..., description="Name of the skill")
    query: str = Field(..., description="Search query string")


class SkillsSearchTool(BaseTool):
    """LangChain tool for searching skill references.
    
    This tool performs full-text search across all files in a skill's
    references/ directory, returning matches with context.
    """
    
    name: str = "skills_search"
    description: str = (
        "Search for text in a skill's references/ directory. "
        "Performs case-insensitive full-text search across all reference files. "
        "Returns matching lines with file path, line number, and context."
    )
    args_schema: Type[BaseModel] = SkillsSearchInput
    
    repository: Any
    
    def __init__(self, repository: SkillsRepository, **kwargs):
        """Initialize with repository.
        
        Args:
            repository: SkillsRepository instance
        """
        super().__init__(repository=repository, **kwargs)
    
    def _run(self, name: str, query: str) -> str:
        """Execute tool and return JSON response.
        
        Args:
            name: Skill name
            query: Search query string
            
        Returns:
            JSON string containing ToolResponse
        """
        try:
            # Open skill handle
            handle = self.repository.open(name)
            
            # Get references directory path
            references_dir = handle.descriptor().path / "references"
            
            # Perform search
            searcher = FullTextSearcher()
            results = searcher.search(
                directory=references_dir,
                query=query,
                max_results=20,
            )
            
            # Build search response
            response = build_search_response(
                skill_name=name,
                query=query,
                results=results,
                meta={},
            )
            
            return json.dumps(response.to_dict(), indent=2)
        
        except Exception as e:
            error_response = build_error_response(
                skill_name=name,
                error=e,
                include_traceback=False,
            )
            return json.dumps(error_response.to_dict(), indent=2)


def build_langchain_tools(repository: SkillsRepository) -> list[BaseTool]:
    """Build LangChain tools from repository.
    
    This function creates all five skill operation tools configured with
    the provided repository. The tools can be used directly with LangChain
    agents and chains.
    
    Args:
        repository: SkillsRepository instance with discovered skills
        
    Returns:
        List of BaseTool instances:
        - SkillsListTool: List available skills
        - SkillsActivateTool: Load skill instructions
        - SkillsReadTool: Read references and assets
        - SkillsRunTool: Execute scripts
        - SkillsSearchTool: Search references
        
    Example:
        >>> from pathlib import Path
        >>> from agent_skills import SkillsRepository
        >>> from agent_skills.adapters.langchain import build_langchain_tools
        >>> 
        >>> # Initialize repository
        >>> repo = SkillsRepository(roots=[Path("./skills")])
        >>> repo.refresh()
        >>> 
        >>> # Build tools
        >>> tools = build_langchain_tools(repo)
        >>> 
        >>> # Use with LangChain agent
        >>> from langchain.agents import AgentExecutor, create_openai_functions_agent
        >>> from langchain_openai import ChatOpenAI
        >>> 
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> agent = create_openai_functions_agent(llm, tools, prompt)
        >>> agent_executor = AgentExecutor(agent=agent, tools=tools)
    """
    return [
        SkillsListTool(repository=repository),
        SkillsActivateTool(repository=repository),
        SkillsReadTool(repository=repository),
        SkillsRunTool(repository=repository),
        SkillsSearchTool(repository=repository),
    ]
