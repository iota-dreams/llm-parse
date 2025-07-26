# 🚀 Project Commands

Use the `Makefile` for common tasks.

> ⚠️ On Windows without `make`, use WSL or manually run the commands.

## 🔧 Install dependencies and hooks

```bash
make setup
```

## 📦 Update requirements (dev + prod)

```bash
make update-reqs
```

This regenerates:

* `deploy/requirements.txt`: Based on actual imports in `src/`, `app/`, and `docs/`
* `deploy/requirements_dev.txt`: Full `pip freeze`, with a reference to `requirements.txt`

Note: The script skips unnecessary files like `__pycache__`, notebooks, and other non-Python files to keep the output clean.

## 🧼 Format code

```bash
make format
```

## 🔍 Lint code

```bash
make lint
```

## ✅ Format + lint (pre-commit dry run)

```bash
make check
```

## 📘 Build docs

```bash
make docs
```

## 🧽 Clean build artifacts and cache

```bash
make clean
```
