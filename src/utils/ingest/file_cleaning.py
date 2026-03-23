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

# Matches start of \[re]newcommand{\name} — used by expand_macros
_NEWCMD_HDR_RE = re.compile(r'\\(?:re)?newcommand\s*\{\\([A-Za-z@]+)\}')


def _brace_balanced(tex: str, start: int) -> tuple[str, int]:
    """Extract content inside matching braces.
    `start` must point to the opening '{'.
    Returns (inner_content, index_after_closing_brace).
    """
    depth = 1
    i = start + 1
    while i < len(tex) and depth > 0:
        if tex[i] == '{':
            depth += 1
        elif tex[i] == '}':
            depth -= 1
        i += 1
    return tex[start + 1:i - 1], i


def expand_macros(tex: str) -> str:
    """Parse zero-argument \\newcommand definitions and substitute them throughout
    the source so the LLM never sees undefined custom macros in its output.
    Macros that take arguments are left untouched.
    """
    macros: dict[str, str] = {}

    # --- pass 1: collect zero-arg macro definitions ---
    scan = 0
    while scan < len(tex):
        m = _NEWCMD_HDR_RE.search(tex, scan)
        if not m:
            break
        name = m.group(1)
        p = m.end()
        # skip whitespace
        while p < len(tex) and tex[p] in ' \t\n':
            p += 1
        if p >= len(tex):
            break
        if tex[p] == '[':
            # has argument count — skip
            scan = p + 1
            continue
        if tex[p] != '{':
            scan = p
            continue
        definition, end = _brace_balanced(tex, p)
        macros[name] = definition
        scan = end

    if not macros:
        return tex

    # --- pass 2: remove definition statements for collected macros ---
    parts: list[str] = []
    pos = 0
    while pos < len(tex):
        m = _NEWCMD_HDR_RE.search(tex, pos)
        if not m:
            parts.append(tex[pos:])
            break
        name = m.group(1)
        if name not in macros:
            parts.append(tex[pos:m.end()])
            pos = m.end()
            continue
        parts.append(tex[pos:m.start()])
        p = m.end()
        while p < len(tex) and tex[p] in ' \t\n':
            p += 1
        if p < len(tex) and tex[p] == '{':
            _, p = _brace_balanced(tex, p)
        pos = p

    tex = ''.join(parts)

    # --- pass 3: substitute uses, longest names first to avoid prefix clashes ---
    for name in sorted(macros, key=len, reverse=True):
        definition = macros[name]
        # Use a lambda so the replacement is treated as a literal string,
        # avoiding re.sub's backslash-escape interpretation of the replacement.
        tex = re.sub(
            rf'\\{re.escape(name)}(?![A-Za-z])',
            lambda _, d=definition: d,
            tex,
        )

    # Normalize text-mode font commands that don't render in math environments.
    # \textsc{x} and {\rm x} are not supported by KaTeX/MathJax inside $...$;
    # replace them with \mathrm{x} which is universally supported.
    tex = re.sub(r'\\textsc\{([^}]*)\}', r'\\mathrm{\1}', tex)
    tex = re.sub(r'\{\\rm\s+([^}]*)\}', r'{\\mathrm{\1}}', tex)
    tex = re.sub(r'\\rm\s+', r'\\mathrm ', tex)

    return tex


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
    tex = expand_macros(tex)
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
