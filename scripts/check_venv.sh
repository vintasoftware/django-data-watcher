#!/bin/bash

PYTHON_PATH=$(which python)
echo "Checking for venv..."
if [[ $PYTHON_PATH == *"virtualenvs/"* ]]; then
    echo "Virtual env is running, apparently"
else
    echo "Your virtual env is not running, you should run it."
    echo "Check README file file if need to configurate it."
    exit 1
fi
