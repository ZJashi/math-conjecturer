import io
import tarfile
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parents[3]   # project root (math-conjecturer/)
PAPERS_DIR = BASE_DIR / "papers"

def fetch_arxiv_source(arxiv_id: str, out_dir=PAPERS_DIR) -> Path:
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    out = Path(out_dir) / arxiv_id
    out.mkdir(parents=True, exist_ok=True)

    content = io.BytesIO(r.content)

    try:
        with tarfile.open(fileobj=content, mode="r:*") as tar:
            tar.extractall(path=out, filter="data")
            return out
    except tarfile.ReadError:
        # Not a tarball → single-file LaTeX
        (out / "main.tex").write_bytes(r.content)
        return out


if __name__=="__main__":

   print(type(fetch_arxiv_source("2601.03006")))