import re
from pathlib import Path

from .find_mainTeX_and_bbls import find_main_tex

INPUT_RE = re.compile(r"\\(input|include)\*?\{([^}]+)\}")


def inline_inputs(tex_path: Path,
                  seen: set[Path] | None = None) -> str:

    if seen is None:
        seen = set()

    tex_path = tex_path.resolve()

    # Prevent infinite recursion
    if tex_path in seen:
        return f"% Skipped recursive include: {tex_path.name}\n"

    seen.add(tex_path)

    try:
        text = tex_path.read_text(errors="ignore")
    except FileNotFoundError:
        return f"% Missing file: {tex_path}\n"

    def replace(match: re.Match) -> str:
        name = match.group(2)

        # Add .tex if missing
        if not name.endswith(".tex"):
            name += ".tex"

        child = (tex_path.parent / name)
        print(child)
        if not child.exists():
            return f"% Missing file: {name}\n"

        return inline_inputs(child, seen)


    return INPUT_RE.sub(replace, text)


if __name__ == "__main__":
    working_dir = Path("../../papers")
    paper_id = "test_paper1"
    tex_path = working_dir / paper_id

    main_tex = find_main_tex(tex_path)

    flattened = inline_inputs(main_tex)
    main_tex.write_text(flattened)


