from .fetch_papers import fetch_arxiv_source
from .find_mainTeX_and_bbls import find_main_tex
from .find_mainTeX_and_bbls import find_bbls
from .substitute_bibliography import substitute_bbl
from .file_cleaning import  clean_latex
from .substitute_inputs_and_includes import inline_inputs



def pipeline(paper_id: str):
    #Download Paper
    working_dir = fetch_arxiv_source(paper_id)

    #Identify main TeX file and bbl file
    bbls = find_bbls(working_dir)
    main_tex = find_main_tex(working_dir)

    #Substitute Inputs/Includes
    main_tex.write_text(inline_inputs(main_tex))

    #Substitute Bibliography
    substitute_bbl(main_tex, bbls)

    #Clean the file
    main_tex.write_text(clean_latex(main_tex.read_text()))

    return  main_tex.read_text()



if __name__ == "__main__":
    pipeline('2601.09704')