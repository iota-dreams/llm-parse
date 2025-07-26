# 🔒 Pre-commit Hooks

Install once after cloning:

```bash
pre-commit install
```

Pre-commit hooks will:

* Format code using `black`
* Lint and fix issues with `ruff`
* Update `deploy/requirements*.txt` via `update_reqs.zsh`

Run manually with:

```bash
pre-commit run --all-files
```
