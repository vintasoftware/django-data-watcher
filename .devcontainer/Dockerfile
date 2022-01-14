# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.202.5/containers/debian/.devcontainer/base.Dockerfile
# https://github.com/python-poetry/poetry/discussions/1879

FROM python:3.6.8
ENV PYTHONUNBUFFERED 1
RUN useradd -ms /bin/bash vscode
RUN apt-get update && apt-get install -y vim

USER vscode
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
ENV PATH="/home/vscode/.poetry/bin:$PATH"

COPY poetry.lock poetry.toml pyproject.toml ./
RUN poetry install
