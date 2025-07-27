# Use Zsh as the shell
SHELL := /bin/zsh

# Name of your active conda env
CONDA_ENV := llm_parse

.PHONY: check-env check-direnv setup update-reqs format lint check docs clean onboard

# 🔐 Ensure you're in the correct conda env
check-env:
	@[[ "$$CONDA_DEFAULT_ENV" == "$(CONDA_ENV)" ]] || \
	(echo "❌ Conda environment '$(CONDA_ENV)' is not active."; \
	 echo "💡 Run 'direnv allow' or 'mamba activate $(CONDA_ENV)' to activate."; \
	 exit 1)

# 🔎 Check if direnv is installed (optional but helpful)
check-direnv:
	@command -v direnv >/dev/null 2>&1 && \
	 echo "✅ direnv is installed." || \
	 (echo "⚠️ direnv not found. Install from https://direnv.net for auto-activation support."; exit 0)

# 🚀 First-time setup guide
onboard: check-direnv check-env setup check docs
	@echo "🎉 Onboarding complete. You're ready to go!"

# ⚙️ Install dev dependencies & pre-commit
setup: check-env
	@echo "📦 Installing dev dependencies..."
	pip install -r deploy/requirements_dev.txt
	pre-commit install
	@command -v direnv >/dev/null 2>&1 && \
	 echo "💡 Tip: Run 'direnv allow' to enable automatic environment activation." || \
	 echo "ℹ️ direnv not found. Activate manually with 'mamba activate $(CONDA_ENV)'"
	@echo "✅ Setup complete! Run 'make check' or 'make docs' next."

# 🔄 Update deploy/requirements*.txt using your custom Zsh script
update-reqs: check-env
	@echo "🔄 Updating requirements..."
	./update_reqs.zsh
	@echo "✅ Requirements updated."

# 🧹 Format code using black & ruff
format: check-env
	@echo "🧼 Formatting code with black and ruff..."
	black .
	ruff check . --fix
	@echo "✅ Format complete."

# 🔍 Lint without modifying
lint: check-env
	@echo "🔍 Linting code with ruff..."
	ruff check .
	@echo "✅ Lint complete."

# ✅ Format + lint (safe pre-commit dry-run)
check: format lint
	@echo "✅ Code check passed."

# 📘 Build Sphinx HTML docs
docs: check-env
	@echo "📘 Building documentation..."
	cd docs && make html
	@echo "✅ Docs built at docs/build/html/index.html"

# 🐳 Clean up unused Docker artifacts
clean-docker:
	@command -v docker >/dev/null 2>&1 || { echo "🐳 Docker not installed. Skipping Docker cleanup."; exit 0; }
	@echo "🐋 Cleaning unused Docker resources..."
	@docker image prune -a -f
	@docker container prune -f
	@docker builder prune -f
	@echo "✅ Docker cleanup complete."
	@echo "📊 Docker system disk usage after cleanup:"
	@docker system df | grep -E 'Images|Containers|Volumes|Build Cache'

# 🧽 Clean up build artifacts
clean: clean-docker
	@echo "🧽 Cleaning build artifacts..."
	rm -rf docs/build
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Clean complete."

# 🐳 Run local development server with hot reload
dev: check-env
	docker compose -f docker-compose.dev.yaml up --build

# 🐳 Stop dev container
dev-down:
	docker compose -f docker-compose.dev.yaml down

# 🚀 Run production server (no reload, no volume mounts)
prod:
	docker compose -f docker-compose.prod.yaml up --build

# 🛑 Stop prod container
prod-down:
	docker compose -f docker-compose.prod.yaml down
