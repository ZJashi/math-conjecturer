import re
from pathlib import Path

BIB_CMD = re.compile(r"\\bibliography\{[^}]+\}")

def substitute_bbl(main_tex: Path, bbls: list[Path]) -> None:
    if not bbls:
        print("No .bbl files found — skipping substitution.")
        return

    tex = main_tex.read_text(errors="ignore")

    if not BIB_CMD.search(tex):
        print(
            "⚠️ .bbl files exist, but no \\bibliography{...} found in main TeX - skipping substitution."
        )
        return

    bbl_path = max(bbls, key=lambda p: p.stat().st_size)
    bbl_content = bbl_path.read_text(errors="ignore")

    tex = BIB_CMD.sub(lambda _: bbl_content, tex)
    main_tex.write_text(tex)

    print(f"✅ Substituted bibliography using: {bbl_path.name}")




if __name__ == "__main__":
    print(1)

