.PHONY: run
run:
	python3 app.py

.PHONY: env
env:
	python3 -m venv venv
	. venv/bin/activate

.PHONY: install
install:
	. venv/bin/activate && pip install -r requirements.txt

.PHONY: test
test:
	python3 -m unittest discover -s tests

.PHONY: clean
clean:
	rm -rf __pycache__ tests/__pycache__ tests/*.pyc
	rm -rf */__pycache__ */*.pyc
	rm -rf .pytest_cache
	rm -rf venv
	rm -rf logs
