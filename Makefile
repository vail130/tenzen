install:
	pip install -r requirements.txt

test:
	nosetests $$suite

play:
	python tenzen/go.py

play-test:
	python tenzen/go.py --test

sim:
	python tenzen/go.py --simulation

.PHONY: test
