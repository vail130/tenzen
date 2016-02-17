install:
	pip install -r requirements.txt

test:
	nosetests $$suite

.PHONY: test
