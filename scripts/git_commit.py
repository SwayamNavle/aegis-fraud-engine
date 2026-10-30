#!/usr/bin/env python3
"""
Lightweight Git commit helper utilizing dulwich for environments
without native command-line git / Xcode tools installed.
"""

import sys
import os
from dulwich import porcelain
from dulwich.repo import Repo


def commit_all(message: str) -> None:
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        repo = Repo(repo_path)
    except Exception:
        repo = Repo.init(repo_path)

    # Add all files (respecting .gitignore)
    porcelain.add(repo.path, paths=["."])
    
    # Commit
    author = "Aegis Architect <aegis@engine.local>"
    commit_id = porcelain.commit(repo.path, message=message.encode("utf-8"), author=author.encode("utf-8"))
    print(f"Committed: {commit_id.decode('utf-8')[:8]} - {message}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python git_commit.py '<commit_message>'")
        sys.exit(1)
    commit_all(sys.argv[1])
