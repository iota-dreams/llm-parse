# Use Zsh as the shell
SHELL := /bin/zsh

# Name of your active conda env
CONDA_ENV := llm_parse

.PHONY: check-env setup update-reqs format lint check docs clean

# 🔐 Ensure you're in the correct conda env
check-env:
	@[[ "$$CONDA_DEFAULT_ENV" == "$(CONDA_ENV)" ]] || \
	(echo "❌ Please activate the '$(CONDA_ENV)' conda environment."; exit 1)

# ⚙️ Install dev dependencies & pre-commit
setup: check-env
	pip install -r deploy/requirements_dev.txt
	pre-commit install

# 🔄 Update deploy/requirements*.txt using your custom Zsh script
update-reqs: check-env
	./update_reqs.zsh

# 🧹 Format code using black & ruff
format: check-env
	black .
	ruff check . --fix

# 🔍 Lint without modifying
lint: check-env
	ruff check .

# ✅ Format + lint (safe pre-commit dry-run)
check: format lint

# 📘 Build Sphinx HTML docs
docs: check-env
	cd docs && make html

# 🧽 Clean up build artifacts
clean:
	rm -rf docs/build
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
