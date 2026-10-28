.PHONY: all clean pdf

all: pdf

pdf:
	@if command -v tectonic >/dev/null 2>&1; then \
		tectonic main.tex; \
	elif [ -f "C:/Users/user/.foundry/bin/tectonic.exe" ]; then \
		C:/Users/user/.foundry/bin/tectonic.exe main.tex; \
	elif command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf main.tex; \
	else \
		pdflatex -interaction=nonstopmode main.tex && \
		bibtex main && \
		pdflatex -interaction=nonstopmode main.tex && \
		pdflatex -interaction=nonstopmode main.tex; \
	fi

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.fdb_latexmk *.fls
