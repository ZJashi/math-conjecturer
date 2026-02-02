from pathlib import Path



def find_bbls(workdir: Path) -> list[Path]:
    return list(workdir.rglob("*.bbl")) + list(workdir.rglob("*.bib"))


def find_main_tex(workdir: Path | str) -> Path | None:
    workdir = Path(workdir)

    for tex in workdir.rglob("*.tex"):
        try:
            content = tex.read_text(errors="ignore")
        except Exception:
            continue

        if "\\documentclass" in content:
            return tex

    return None


if __name__ == "__main__":
    print(1)