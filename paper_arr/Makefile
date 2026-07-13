PAPER := WorkSurface-Bench
BUILD := build
OUTPUT := ../output/pdf
QA := qa

.PHONY: all qa clean

all: $(OUTPUT)/$(PAPER).pdf

$(OUTPUT)/$(PAPER).pdf: main.tex custom.bib figure1_teaser_polished.pdf figure2_pipeline.pdf figure3.png figure4_distribution.png
	mkdir -p $(BUILD) $(OUTPUT)
	TEXINPUTS=styles:.: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	cd $(BUILD) && BIBINPUTS=..: BSTINPUTS=../styles: bibtex main
	TEXINPUTS=styles:.: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	TEXINPUTS=styles:.: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	cp $(BUILD)/main.pdf $(OUTPUT)/$(PAPER).pdf

qa: all
	rm -f $(QA)/page-*.png
	mkdir -p $(QA)
	pdftoppm -png -r 120 $(OUTPUT)/$(PAPER).pdf $(QA)/page

clean:
	rm -rf $(BUILD)
