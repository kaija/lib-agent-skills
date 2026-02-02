"""Entry point for running agent-skills as a module.

This allows the package to be executed as:
    python -m agent_skills

It delegates to the CLI main function.
"""

from agent_skills.cli.main import main

if __name__ == "__main__":
    main()
