install:
	pip install -r requirements.txt

test:
	nosetests $$suite

play:
	python tenzen/go.py

.PHONY: test
