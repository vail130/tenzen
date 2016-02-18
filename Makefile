PYTHON=PYTHONPATH=$${PWD} python

install:
	pip install -r requirements.txt

test:
	nosetests $$suite

play:
	$(PYTHON) tenzen/game.py

play-test:
	$(PYTHON) tenzen/game.py --test

sim:
	$(PYTHON) tenzen/game.py --simulation

.PHONY: test
