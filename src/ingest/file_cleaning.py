import re
from pathlib import Path
from .find_mainTeX_and_bbls import find_main_tex

'''
Line Based Commands
'''



METADATA_PREFIXES = [
    r'\maketitle',
    r'\author',
    r'\affiliation',
    r'\address',
    r'\email',
    r'\date',
    r'\keywords',
    r'\subclass',
    r'\PACS',
    r'\MSC',
]

LAYOUT_LINE_PREFIXES = [
    r'\raggedright',
    r'\raggedleft',
    r'\centering',
    r'\onecolumn',
    r'\twocolumn',
    r'\sloppy',
    r'\fussy',
]

FONT_SIZE_PREFIXES = [
    r'\tiny',
    r'\scriptsize',
    r'\footnotesize',
    r'\small',
    r'\normalsize',
    r'\large',
    r'\Large',
    r'\LARGE',
    r'\huge',
    r'\Huge',
]


'''
Regex Based Commands
'''

LAYOUT_REGEX = [
    r'\\vspace\*?\{.*?\}',
    r'\\hspace\*?\{.*?\}',
    r'\\(newpage|pagebreak|clearpage|cleardoublepage)\b',
    r'\\(linebreak|nolinebreak)\b',
    r'\\(smallskip|medskip|bigskip)\b',
    r'\\par\b',
    r'\\noindent\b',
]

COLOR_REGEX = [
    r'\\color\{.*?\}',
    r'\\pagecolor\{.*?\}',
    r'\\definecolor\{.*?\}\{.*?\}\{.*?\}',
    r'\\textcolor\{.*?\}\{.*?\}',
]

BOX_REGEX = [
    r'\\mbox\{.*?\}',
    r'\\fbox\{.*?\}',
    r'\\framebox\{.*?\}',
    r'\\raisebox\{.*?\}\{.*?\}',
    r'\\makebox\{.*?\}\{.*?\}',
]

ENVIRONMENTS_TO_FLATTEN = [
    'center',
    'flushleft',
    'flushright',
]

'''
    Unused Macros
'''

MACRO_DEF_RE = re.compile(
    r'\\(newcommand|renewcommand|def|DeclareMathOperator)\s*\{\\([A-Za-z@]+)\}',
    re.MULTILINE,
)



def remove_comments(tex: str) -> str:
    return re.sub(r'(?<!\\)%.*', '', tex)


def remove_line_based_junk(tex: str) -> str:
    lines = tex.splitlines()
    out = []

    for line in lines:
        stripped = line.lstrip()

        if any(stripped.startswith(p) for p in METADATA_PREFIXES):
            continue
        if any(stripped.startswith(p) for p in LAYOUT_LINE_PREFIXES):
            continue
        if any(stripped.startswith(p) for p in FONT_SIZE_PREFIXES):
            continue

        out.append(line)

    return "\n".join(out)


def remove_regex_junk(tex: str) -> str:
    for pat in LAYOUT_REGEX + COLOR_REGEX + BOX_REGEX:
        tex = re.sub(pat, '', tex, flags=re.DOTALL)
    return tex


def flatten_layout_environments(tex: str) -> str:
    for env in ENVIRONMENTS_TO_FLATTEN:
        tex = re.sub(
            rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}',
            r'\1',
            tex,
            flags=re.DOTALL,
        )
    return tex


def remove_unused_macros(tex: str) -> str:
    defs = MACRO_DEF_RE.findall(tex)
    defined = {name for _, name in defs}

    # remove macro definitions before checking usage
    tex_wo_defs = MACRO_DEF_RE.sub('', tex)

    used = set(re.findall(r'\\([A-Za-z@]+)\b', tex_wo_defs))
    unused = defined - used

    for name in unused:
        tex = re.sub(
            rf'\\(newcommand|renewcommand|def|DeclareMathOperator)\s*\{{\\{name}\}}.*',
            '',
            tex,
        )

    return tex


def normalize_whitespace(tex: str) -> str:
    tex = re.sub(r'\n{3,}', '\n\n', tex)
    tex = re.sub(r'[ \t]+\n', '\n', tex)
    return tex.strip() + "\n"



def clean_latex(tex: str) -> str:
    tex = remove_comments(tex)
    tex = remove_line_based_junk(tex)
    tex = remove_regex_junk(tex)
    tex = flatten_layout_environments(tex)
    tex = remove_unused_macros(tex)
    tex = normalize_whitespace(tex)
    return tex



if __name__ == "__main__":
    working_dir = Path("../../papers")
    paper_id = "test_paper"

    tex_dir = working_dir / paper_id
    main_tex = find_main_tex(tex_dir)

    original = main_tex.read_text(errors="ignore")
    cleaned = clean_latex(original)

    main_tex.write_text(cleaned)

    print("LaTeX cleaned successfully.")
