from __future__ import annotations

from datetime import datetime
from pathlib import Path


ENV_ROOT_NAMES = {
    ".alpha_env",
    "eidollona_env",
    "quantum_env",
    "venv",
    ".venv",
    "env",
    "eidollona_env_backup",
    "eidollona_env_old",
    "quantum_env_old",
}

SKIP_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".git",
}

ENV_ONLY_NAMES = {
    "lib",
    "lib64",
    "lib32",
    "libs",
    "site-packages",
    "include",
    "scripts",
}


def should_skip(path: Path, env_roots: set[str]) -> bool:
    name = path.name.lower()
    if name in env_roots:
        return True
    if name in SKIP_NAMES:
        return True
    if name in ENV_ONLY_NAMES and any(parent.name.lower() in env_roots for parent in path.parents):
        return True
    return False


def build_tree(root: Path) -> list[str]:
    env_roots = {item.lower() for item in ENV_ROOT_NAMES}
    lines: list[str] = [root.name]

    def walk(current: Path, prefix: str = "") -> None:
        try:
            entries = [child for child in current.iterdir() if child.is_dir()]
        except PermissionError:
            return

        children = sorted(
            (entry for entry in entries if not should_skip(entry, env_roots)),
            key=lambda item: item.name.lower(),
        )

        for index, child in enumerate(children):
            connector = "└── " if index == len(children) - 1 else "├── "
            lines.append(f"{prefix}{connector}{child.name}")
            extension = "    " if index == len(children) - 1 else "│   "
            walk(child, prefix + extension)

    walk(root)
    return lines


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    timestamp = datetime.now().strftime("%Y%m%d")
    output = root / f"project_tree_{timestamp}.txt"

    lines = build_tree(root)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output} ({len(lines)} entries)")


if __name__ == "__main__":
    main()
