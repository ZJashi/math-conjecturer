from pathlib import Path

from .fetch_papers import fetch_arxiv_source
from .file_cleaning import clean_latex
from .find_mainTeX_and_bbls import find_bbls, find_main_tex
from .substitute_bibliography import substitute_bbl_content
from .substitute_inputs_and_includes import inline_inputs



def pipeline(paper_id: str):
    #Download Paper
    working_dir = fetch_arxiv_source(paper_id)

    #Identify main TeX file and bbl file
    bbls = find_bbls(working_dir)
    main_tex = find_main_tex(working_dir)

    #Substitute Inputs/Includes (get content without modifying original)
    content = inline_inputs(main_tex)

    #Substitute Bibliography (on content, not file)
    content = substitute_bbl_content(content, bbls)

    #Clean the content
    content = clean_latex(content)

    # Create ingest folder and save cleaned text there
    ingest_dir = working_dir / "step1_ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)

    output_path = ingest_dir / "processed.tex"
    output_path.write_text(content, encoding="utf-8")

    return content



if __name__ == "__main__":
    pipeline('2601.09704')