# 🚀 Project Commands

This project provides a `Makefile` to simplify common development, formatting, and deployment tasks.

> 🛠️ Works best with `direnv`, `mamba/conda`, and Docker.
> ⚠️ On Windows, use WSL for full compatibility with `zsh` and `make`.

---

## 🆕 First-Time Setup

Run this to get everything ready — environment checks, installs, docs build:

```bash
make onboard
```

Includes:

* Verifies `direnv` presence (optional)
* Verifies active `conda` env (`llm_parse`)
* Installs dev dependencies and pre-commit hooks
* Builds docs as sanity check

---

## 🔧 Install Dev Dependencies

Install Python packages and Git hooks:

```bash
make setup
```

> ℹ️ Tip: After setup, run `make check` or `make docs`

---

## 🐍 Conda Environment Check

Ensure the right environment is active (`llm_parse`):

```bash
make check-env
```

---

## 📦 Update Requirements

Regenerates:

* `deploy/requirements.txt`: Based on actual imports
* `deploy/requirements_dev.txt`: Full `pip freeze`

```bash
make update-reqs
```

> Uses `update_reqs.zsh` for custom filtering
> Skips `__pycache__`, notebooks, etc.

---

## 🧼 Format Code

Apply formatting via `black` and fixable `ruff` rules:

```bash
make format
```

---

## 🔍 Lint Code

Run `ruff` in check-only mode:

```bash
make lint
```

---

## ✅ Pre-Commit Dry Run

Check code formatting and linting (like CI would):

```bash
make check
```

---

## 📘 Build Documentation

Build local HTML docs via Sphinx:

```bash
make docs
```

Output will be in:

```
docs/build/html/index.html
```

---

## 🧽 Clean Up

Remove Python build artifacts, cache files, and docs:

```bash
make clean
```

Also triggers Docker cleanup if installed.

---

## 🐳 Docker Cleanup (Optional)

Reclaim disk space from unused Docker layers/containers:

```bash
make clean-docker
```

---

## 🧪 Run FastAPI in Dev Mode (Docker)

Local development server with hot reload and volume mounts:

```bash
make dev
```

Stop with:

```bash
make dev-down
```

---

## 🚀 Run in Production Mode (Docker)

Optimized for deployment (no volume mounts or reload):

```bash
make prod
```

Stop with:

```bash
make prod-down
```
