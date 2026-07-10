"""Synchronize paper/main_cas.tex from paper/main.tex.

The CAS file has a different front matter, but the scientific body should stay
identical to the stable elsarticle manuscript.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
MAIN = PAPER / "main.tex"
CAS = PAPER / "main_cas.tex"


def extract_env(text: str, name: str) -> str:
    start = text.index(f"\\begin{{{name}}}") + len(f"\\begin{{{name}}}")
    end = text.index(f"\\end{{{name}}}", start)
    return text[start:end].strip()


def extract_command_arg(text: str, command: str) -> str:
    start = text.index(f"\\{command}") + len(command) + 1
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : i].strip()
    raise ValueError(f"unterminated command {command}")


def main() -> None:
    text = MAIN.read_text()
    title = extract_command_arg(text, "title")
    abstract = extract_env(text, "abstract")
    keywords = extract_env(text, "keyword")
    body = text[text.index("\\section{Introduction}") :]
    body = body.replace("\\bibliographystyle{elsarticle-num}\n", "")
    body = body.replace("\\begin{figure}[H]", "\\begin{figure}")
    body = body.replace("\\begin{table}[H]", "\\begin{table}")

    preamble = rf"""\PassOptionsToPackage{{hypertexnames=false}}{{hyperref}}
\documentclass[a4paper,fleqn]{{cas-sc}}

\usepackage[numbers]{{natbib}}
\usepackage{{amsmath,amssymb,amsfonts}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{multirow}}
\usepackage{{float}}
\usepackage{{algorithm}}
\usepackage{{algpseudocode}}

% Temporary while real author ORCID metadata are not yet available.
\RenewDocumentCommand \printorcid {{}} {{}}

\newcommand{{\breeze}}{{BREEZE}}
\newcommand{{\pucond}}{{N09\_M07\_F10}}

\begin{{document}}
\let\WriteBookmarks\relax
\def\floatpagepagefraction{{1}}
\def\textpagefraction{{.001}}

\shorttitle{{BREEZE physical-gate admission for LLM fault signals}}
\shortauthors{{Author One et~al.}}

\title [mode = title]{{{title}}}

\author[1]{{Author One}}
\author[1]{{Author Two}}

\affiliation[1]{{organization={{Department}},
            city={{City}},
            country={{Country}}}}

\begin{{abstract}}
{abstract}
\end{{abstract}}

\begin{{keywords}}
{keywords}
\end{{keywords}}

\maketitle

"""
    CAS.write_text(preamble + body)


if __name__ == "__main__":
    main()
