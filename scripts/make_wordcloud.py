#!/usr/bin/env python3
"""
Build a word cloud from all PDFs in a folder.

Usage:
  python3 scripts/make_wordcloud.py --input papers --output wordcloud.png
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


def _strip_latex(text: str) -> str:
    # Drop comments.
    text = re.sub(r"(?m)^%.*$", " ", text)
    # Remove math blocks.
    text = re.sub(r"\$.*?\$", " ", text)
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.S)
    # Remove common commands and their args.
    text = re.sub(r"\\(cite|ref|label|eqref|footnote|url|href)\{.*?\}", " ", text)
    # Remove remaining commands like \section{...}
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    # Remove braces leftover.
    text = text.replace("{", " ").replace("}", " ")
    return text


def _clean_text(text: str, min_len: int) -> list[str]:
    # Keep letters and spaces only, normalize whitespace.
    text = re.sub(r"[^A-Za-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    words = [w for w in text.split(" ") if len(w) >= min_len]
    return words


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a word cloud from PDFs.")
    parser.add_argument("--input", default="papers", help="Folder containing PDF files.")
    parser.add_argument("--output", default="wordcloud.png", help="Output PNG path.")
    parser.add_argument("--min-len", type=int, default=3, help="Minimum word length.")
    parser.add_argument("--max-words", type=int, default=90, help="Max words in cloud.")
    parser.add_argument("--print-top", type=int, default=0, help="Print top N words after filtering.")
    parser.add_argument(
        "--debug-words",
        default="",
        help="Comma-separated words to report counts for (before/after filtering).",
    )
    parser.add_argument(
        "--stopwords",
        default="",
        help="Optional newline-separated stopwords file. If omitted, uses ../stopwords.txt if it exists.",
    )
    parser.add_argument(
        "--extra-stopwords",
        default="",
        help="Comma-separated stopwords to add (e.g., 'paper,section,table').",
    )
    args = parser.parse_args()

    try:
        from wordcloud import WordCloud, STOPWORDS
    except Exception as exc:  # pragma: no cover
        print("Missing dependency: wordcloud")
        print("Install with: python3 -m pip install wordcloud")
        print(f"Details: {exc}")
        return 1

    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"Input folder not found: {input_dir}")
        return 1

    tex_files = sorted(input_dir.glob("*.tex"))
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not tex_files and not pdfs:
        print(f"No .tex or .pdf files found in: {input_dir}")
        return 1

    stopwords = set(STOPWORDS)
    stop_path = Path(args.stopwords) if args.stopwords else (Path(__file__).resolve().parent / ".." / "stopwords.txt")
    if stop_path.exists():
        stopwords.update(w.strip().lower() for w in stop_path.read_text().splitlines() if w.strip())
    elif args.stopwords:
        print(f"Stopwords file not found: {stop_path}")
        return 1
    if args.extra_stopwords:
        stopwords.update(w.strip().lower() for w in args.extra_stopwords.split(",") if w.strip())

    all_words: list[str] = []
    if tex_files:
        for tex in tex_files:
            text = tex.read_text(errors="ignore")
            text = _strip_latex(text)
            all_words.extend(_clean_text(text, args.min_len))
    else:
        try:
            from pdfminer.high_level import extract_text
        except Exception as exc:  # pragma: no cover
            print("Missing dependency: pdfminer.six")
            print("Install with: python3 -m pip install pdfminer.six")
            print(f"Details: {exc}")
            return 1

        for pdf in pdfs:
            text = extract_text(str(pdf))
            all_words.extend(_clean_text(text, args.min_len))

    raw_counts = Counter(all_words)
    words = [w for w in all_words if w not in stopwords]
    counts = Counter(words)

    wc = WordCloud(
        width=1600,
        height=900,
        background_color="white",
        max_words=args.max_words,
        collocations=False,
    )
    wc.generate_from_frequencies(counts)
    output_path = Path(args.output)
    wc.to_file(str(output_path))

    top = counts.most_common(20)
    print(f"Saved word cloud to: {output_path}")
    print("Top words:", ", ".join(f"{w}({c})" for w, c in top))
    if args.print_top:
        print(f"Top {args.print_top} after filtering:")
        for word, count in counts.most_common(args.print_top):
            print(f"{word}\t{count}")
    if args.debug_words:
        targets = [w.strip().lower() for w in args.debug_words.split(",") if w.strip()]
        for word in targets:
            print(f"debug:{word}\traw={raw_counts.get(word, 0)}\tfiltered={counts.get(word, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
