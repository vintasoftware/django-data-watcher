checkvenv:
	./scripts/check_venv.sh

compile: checkvenv
	pip-compile --allow-unsafe -o requirements/dev.txt requirements/dev.in
	pip-compile -o requirements/base.txt requirements/base.in

install: checkvenv
	pip-sync requirements/base.txt requirements/dev.txt

setupvenv: checkvenv
	pip install pip-tools
	make install
	pre-commit install
	pre-commit install --hook-type pre-push
