ARG := $(wordlist 2, $(words $(MAKECMDGOALS)), $(MAKECMDGOALS))

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

setup_test_pypi:
	poetry config repositories.test-pypi https://test.pypi.org/legacy/
	poetry config pypi-token.test-pypi $(ARG)

publish_test:
	poetry publish --build -r test-pypi
