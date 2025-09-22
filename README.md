# rana-process-sdk

The SDK (Software Development Kit) for creating your own [Rana Water Intelligence](https://ranawaterintelligence.com) processes.


## Development on this project itself

See [nens-meta's documentation](https://nens-meta.readthedocs.io) for an explanation of the config files like `.editorconfig` and tools like `pre-commit` and `uv`.

The standard commands apply:

    $ uv sync
    $ uv run pytest
    $ uv run python  # You can also activate the virtualenv in .venv
    $ pre-commit run --all  # You can also do 'pre-commit install'
    $ uv add some-dependency

`uv` replaces pip/venv/requirement.txt/pip-tools. `pre-commit` does basic formatting.

The tests and pre-commit are also run automatically [on "github actions"](https://github.com/nens/rana-process-sdk/actions) for "main" and for pull requests. So don't just make a branch, but turn it into a pull request right away. On your pull request page, you also automatically get the feedback from the automated tests.

If you need a new dependency (like `requests`), add it in
`pyproject.toml` in `dependencies`:

    $ uv add requests

## Release

Make sure you have [zest.releaser](https://zestreleaser.readthedocs.io/en/latest/) installed.

    uv run fullrelease

When you created a tag, it will be uploaded automatically [to pypi](https://pypi.org/project/rana-process-sdk/) by a Github Action.
