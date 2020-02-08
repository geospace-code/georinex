PREFIX=$(HOME)/.local

COPTS=-O2

.PHONY: all
all: rnx2crx crx2rnx

rnx2crx: source/rnx2crx.c
	$(CC) $(COPTS) $^ -o $@
	
crx2rnx: source/crx2rnx.c
	$(CC) $(COPTS) $^ -o $@

.PHONY: install
install: crx2rnx rnx2crx
	mkdir -p $(PREFIX)/bin
	cp $^ $(PREFIX)/bin

