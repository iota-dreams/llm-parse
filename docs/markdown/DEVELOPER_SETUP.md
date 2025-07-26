# 🧰 Developer Setup

This project uses:

* [`conda`](https://docs.conda.io/)[/](https://docs.conda.io/)[`mamba`](https://docs.conda.io/) for environment management
* [`direnv`](https://direnv.net/) for automatic shell activation (optional)
* `black`, `ruff`, `isort` for formatting and linting
* `pre-commit` for enforcing standards
* `Sphinx` with reStructuredText for documentation
* Automatic requirements extraction via `update_reqs.zsh` from `src/`, `app/`, and `docs/`

To install dependencies and set up the development environment:

```bash
make setup
```

To run format + lint checks (pre-commit dry run):

```bash
make check
```

To build documentation locally:

```bash
make docs
```

Then view in browser:

```bash
open docs/build/html/index.html  # macOS
xdg-open docs/build/html/index.html  # Linux
start docs/build/html/index.html  # Windows CMD
```

The project uses **Read the Docs** for hosting via `.readthedocs.yaml`.
