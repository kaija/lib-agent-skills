#!/usr/bin/env python3
"""Example: LangChain integration with Agent Skills Runtime.

This example demonstrates how to integrate skills with LangChain agents.

Note: This requires langchain to be installed:
    pip install agent-skills[langchain]
"""

from pathlib import Path

try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain not available. Install with: pip install agent-skills[langchain]")

from agent_skills.runtime import SkillsRepository
from agent_skills.models import ExecutionPolicy


def create_agent_with_skills():
    """Create a LangChain agent with skills."""
    if not LANGCHAIN_AVAILABLE:
        print("Cannot create agent: LangChain not installed")
        return None
    
    # Import here to avoid errors if langchain not installed
    from agent_skills.adapters.langchain import build_langchain_tools
    
    # Initialize repository
    repo = SkillsRepository(
        roots=[Path("examples")],
        execution_policy=ExecutionPolicy(
            enabled=True,
            allow_skills={"test-skill"},
            allow_scripts_glob=["scripts/*.py"],
            timeout_s_default=30,
        )
    )
    repo.refresh()
    
    # Build LangChain tools
    tools = build_langchain_tools(repo)
    
    print(f"Created {len(tools)} LangChain tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    print()
    
    # Create prompt with available skills
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a helpful assistant with access to skills.

{repo.to_prompt(format="claude_xml")}

Available tools:
- skills.list: List all available skills
- skills.activate: Load skill instructions
- skills.read: Read references and documentation
- skills.run: Execute skill scripts
- skills.search: Search skill references

Workflow:
1. Use skills.list to see what skills are available
2. Use skills.activate to load instructions for a skill
3. Use skills.read to access documentation
4. Use skills.run to execute scripts when needed
"""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create LLM (requires OpenAI API key)
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        
        # Create agent
        agent = create_openai_functions_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
        )
        
        return agent_executor
    except Exception as e:
        print(f"Could not create LLM (OpenAI API key required): {e}")
        return None


def run_example_query(agent_executor, query):
    """Run an example query with the agent."""
    if agent_executor is None:
        print("Agent not available")
        return
    
    print("=" * 60)
    print(f"Query: {query}")
    print("=" * 60)
    print()
    
    try:
        result = agent_executor.invoke({"input": query})
        print("\nResult:")
        print("-" * 60)
        print(result["output"])
        print("-" * 60)
    except Exception as e:
        print(f"Error running query: {e}")


def main():
    """Demonstrate LangChain integration."""
    print("=" * 60)
    print("Agent Skills Runtime - LangChain Integration Example")
    print("=" * 60)
    print()
    
    if not LANGCHAIN_AVAILABLE:
        print("This example requires LangChain to be installed.")
        print("Install with: pip install agent-skills[langchain]")
        return
    
    # Create agent
    agent_executor = create_agent_with_skills()
    
    if agent_executor is None:
        print("\nNote: To run queries, you need an OpenAI API key.")
        print("Set OPENAI_API_KEY environment variable.")
        return
    
    # Example queries
    queries = [
        "List all available skills",
        "What does the test-skill do? Load its instructions.",
        "Read the example reference from test-skill",
        "Run the hello.py script from test-skill with argument 'LangChain'",
    ]
    
    for query in queries:
        run_example_query(agent_executor, query)
        print()
    
    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
