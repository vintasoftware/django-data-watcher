# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.202.5/containers/debian/.devcontainer/base.Dockerfile

FROM python:3.6.8
ENV PYTHONUNBUFFERED 1
RUN useradd -ms /bin/bash vscode

USER vscode
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
ENV PATH "/home/vscode/.poetry/bin:$PATH"

COPY ./poetry.lock ./poetry.lock
COPY ./pyproject.toml ./pyproject.toml
COPY ./config.toml ./config.toml
RUN poetry install
