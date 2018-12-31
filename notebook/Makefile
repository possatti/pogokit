# Makefile options
SHELL=/bin/bash
.PHONY: all clean remove_trash_files

# Other variables
MAIN_FILE = notebook
TEX_FILES = $(wildcard *.tex)
# IMAGES = $(wildcard img/*)

all: $(MAIN_FILE).pdf

$(MAIN_FILE).pdf: $(TEX_FILES)
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN_FILE)
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN_FILE)
	$(MAKE) remove_trash_files

remove_trash_files:
	-rm -f *.bbl *.idx *.lot *.toc *.blg *.lof *.aux *.brf *.log \
		*.fls *.ilg *.ind *_latexmk *.synctex.*

clean:
	$(MAKE) remove_trash_files
	-rm -f $(MAIN_FILE).pdf
