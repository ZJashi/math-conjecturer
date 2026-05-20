import re
from pathlib import Path

BIB_CMD = re.compile(r"\\bibliography\{[^}]+\}")


def substitute_bbl_content(tex: str, bbls: list[Path]) -> str:
    """Substitute bibliography in content string, returns modified content."""
    if not bbls:
        print("No .bbl files found — skipping substitution.")
        return tex

    if not BIB_CMD.search(tex):
        print(
            "⚠️ .bbl files exist, but no \\bibliography{...} found in main TeX - skipping substitution."
        )
        return tex

    bbl_path = max(bbls, key=lambda p: p.stat().st_size)
    bbl_content = bbl_path.read_text(errors="ignore")

    tex = BIB_CMD.sub(lambda _: bbl_content, tex)
    print(f"✅ Substituted bibliography using: {bbl_path.name}")
    return tex

