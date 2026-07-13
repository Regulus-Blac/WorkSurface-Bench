# WorkSurface-Bench paper

This directory contains the ARR manuscript and its submission assets.

## Layout

- `main.tex`, `custom.bib`: manuscript source and bibliography.
- `figure*.{pdf,png}`: figures referenced directly by the manuscript.
- `figures_spec/`: editable figure specifications and source deck.
- `styles/`: local ACL style and bibliography files.
- `build/`: generated LaTeX intermediates and compilation logs.
- `qa/`: rendered pages used for visual inspection.
- `releases/`: dated submission PDFs and upload archives.

## Build

Run `make` from this directory. The compiled manuscript is written to
`../output/pdf/WorkSurface-Bench.pdf`; LaTeX intermediates remain in `build/`.
Run `make qa` to render the PDF to PNG pages for visual inspection.
