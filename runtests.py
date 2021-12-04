import sys

import pytest


def main(*args):
    pytest_args = list(args[1:]) if len(args) > 1 else []

    try:
        pytest_args.remove('--coverage')
    except ValueError:
        pass
    else:
        pytest_args = [
            '--cov',
            '.',
            '--cov-report',
            'xml',
        ] + pytest_args

    sys.exit(pytest.main(pytest_args))


if __name__ == '__main__':
    main(*sys.argv)
