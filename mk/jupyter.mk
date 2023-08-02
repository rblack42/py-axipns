.PHONY: nb
nb:
	cd book && \
		jupyter notebook

.PHONY: book
book:
	jb build book
	cp -r book/_build/html/* docs
