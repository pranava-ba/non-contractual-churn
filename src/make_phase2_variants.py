"""Generate alternative-style typesettings of the Phase 2 manuscript.

The Springer `sn-jnl` version (`paper/manuscript_phase2.tex`) is left untouched. This
script extracts its title / abstract / keywords / body, standardises the sn-jnl-specific
macros (``\\botrule`` -> ``\\bottomrule``, ``\\bmhead`` -> ``\\subsection*``,
``\\backmatter`` removed) into a shared ``paper/phase2_body_std.tex``, and wraps it in two
standard-``article`` preambles:

  * manuscript_phase2_modern.tex  -- Times body, sans coloured headings, accent links.
  * manuscript_phase2_elegant.tex -- Palatino body, classic small-caps centred headings.

Run:  python src/make_phase2_variants.py   (then latexmk the produced files in paper/).
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "paper")
SRC = os.path.join(PAPER, "manuscript_phase2.tex")


def braced_after(text: str, brace_idx: int) -> tuple[str, int]:
    """Return (content, index_of_closing_brace) for the balanced group at brace_idx ('{')."""
    depth = 0
    for j in range(brace_idx, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_idx + 1 : j], j
    raise ValueError("unbalanced braces")


def extract_macro_arg(text: str, macro: str) -> str:
    """Extract the mandatory {...} argument of the first occurrence of `macro`."""
    i = text.index(macro)
    b = text.index("{", i)
    return braced_after(text, b)[0]


def main() -> None:
    with open(SRC, encoding="utf-8") as fh:
        tex = fh.read()

    title = extract_macro_arg(tex, r"\title")
    abstract = extract_macro_arg(tex, r"\abstract")
    keywords = extract_macro_arg(tex, r"\keywords")

    a = tex.index(r"\maketitle") + len(r"\maketitle")
    b = tex.index(r"\bibliography{refs")
    body = tex[a:b]
    # standardise sn-jnl-only macros
    body = body.replace(r"\botrule", r"\bottomrule")
    body = body.replace(r"\backmatter", "")
    body = re.sub(r"\\bmhead\{([^}]*)\}", r"\\subsection*{\1}", body)

    with open(os.path.join(PAPER, "phase2_body_std.tex"), "w", encoding="utf-8") as fh:
        fh.write("%% Auto-generated shared body -- edit manuscript_phase2.tex, then rerun\n")
        fh.write("%% src/make_phase2_variants.py.\n")
        fh.write(body.strip() + "\n")

    affil = (r"\small Department of Computer Science and Engineering (AI \& ML), "
             r"Easwari Engineering College, Chennai, India\\[2pt] "
             r"\texttt{pranavabaascaran@gmail.com} \quad \texttt{vyasa.rajesawaran@gmail.com}")

    modern_preamble = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{amsmath}
\usepackage{newtxtext,newtxmath}
\usepackage[scaled=0.92]{helvet}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{booktabs,multirow,array}
\usepackage{algorithm,algpseudocode}
\usepackage[title]{appendix}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage[round,authoryear]{natbib}
\definecolor{accent}{RGB}{20,80,150}
\usepackage[colorlinks=true,linkcolor=accent,citecolor=accent,urlcolor=accent]{hyperref}
\graphicspath{{figures/}}
\titleformat{\section}{\sffamily\Large\bfseries\color{accent}}{\thesection}{0.6em}{}
\titleformat{\subsection}{\sffamily\large\bfseries\color{accent!80!black}}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\sffamily\normalsize\bfseries}{\thesubsubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{1.4\baselineskip}{0.5\baselineskip}
\setlist{itemsep=2pt,topsep=3pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.45\baselineskip}
"""

    elegant_preamble = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[a4paper,margin=1.15in]{geometry}
\usepackage{amsmath}
\usepackage{newpxtext,newpxmath}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{booktabs,multirow,array}
\usepackage{algorithm,algpseudocode}
\usepackage[title]{appendix}
\usepackage{xcolor}
\usepackage{titlesec}
\definecolor{link}{RGB}{60,60,95}
\usepackage[round,authoryear]{natbib}
\usepackage[colorlinks=true,linkcolor=link,citecolor=link,urlcolor=link]{hyperref}
\graphicspath{{figures/}}
\titleformat{\section}[hang]{\centering\scshape\large}{\thesection.}{0.6em}{}
\titleformat{\subsection}[hang]{\scshape\normalsize\bfseries}{\thesubsection.}{0.5em}{}
\titleformat{\subsubsection}[hang]{\itshape\normalsize}{}{0em}{}
\titlespacing*{\section}{0pt}{1.7\baselineskip}{0.9\baselineskip}
\linespread{1.04}
"""

    def wrap(preamble: str, centered_rule: bool) -> str:
        rule = r"\vspace{2pt}\hrule\vspace{6pt}" if centered_rule else ""
        return (
            preamble
            + "\n\\begin{document}\n"
            + f"\\title{{{title}}}\n"
            + "\\author{BA Pranava \\and Vyasa R Rajesawaran}\n"
            + "\\date{}\n\\maketitle\n"
            + f"\\begin{{center}}{affil}\\end{{center}}\n{rule}\n"
            + f"\\begin{{abstract}}\\noindent {abstract}\\end{{abstract}}\n"
            + f"\\noindent\\textbf{{Keywords:}} {keywords}\\par\\vspace{{1em}}\n\n"
            + "\\input{phase2_body_std.tex}\n\n"
            + "\\bibliographystyle{plainnat}\n\\bibliography{refs,refs_phase2}\n\\end{document}\n"
        )

    with open(os.path.join(PAPER, "manuscript_phase2_modern.tex"), "w", encoding="utf-8") as fh:
        fh.write(wrap(modern_preamble, centered_rule=False))
    with open(os.path.join(PAPER, "manuscript_phase2_elegant.tex"), "w", encoding="utf-8") as fh:
        fh.write(wrap(elegant_preamble, centered_rule=True))

    print("wrote phase2_body_std.tex, manuscript_phase2_modern.tex, manuscript_phase2_elegant.tex")


if __name__ == "__main__":
    main()
