checkvenv:
	./scripts/check_venv.sh

update: checkvenv
	poetry update

install: checkvenv
	poetry install

setupvenv: checkvenv
	make install
	poetry run pre-commit install
	poetry run pre-commit install --hook-type pre-push
