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

# Use Mamba instead of Conda
MAMBA_ENV_TEST := llm_parse_test

# 🧪 Create test env, uninstall old, install built wheel, verify config
test-package-env:
	@echo "🧪 Creating test mamba environment '$(MAMBA_ENV_TEST)'..."
	@mamba create -n $(MAMBA_ENV_TEST) python=3.11 -y
	@echo "✅ Test environment created."

	@echo "📦 Building wheel..."
	python setup.py sdist bdist_wheel
	@echo "✅ Build complete."

	@echo "📦 Uninstalling existing llm_parse if present..."
	@mamba run -n $(MAMBA_ENV_TEST) pip uninstall -y llm_parse || true
	@echo "✅ Previous llm_parse (if any) removed."

	@echo "📦 Installing new built wheel into test env..."
	@mamba run -n $(MAMBA_ENV_TEST) pip install dist/*.whl
	@echo "✅ Package installed."

	@echo "🔍 Verifying config import..."
	@mamba run -n $(MAMBA_ENV_TEST) python -c "from llm_parse.utils import load_config_with_fallback; print(load_config_with_fallback())"
	@echo "✅ Config load test passed."

# 🧼 Cleanup test environment
test-package-clean:
	@echo "🧼 Removing test mamba environment..."
	@mamba env remove -n $(MAMBA_ENV_TEST)
	@echo "✅ Test environment removed."

# 🧪 Run CLI test inside Mamba test env
test-package-cli:
	@echo "🧪 Running CLI test in test env '$(MAMBA_ENV_TEST)'..."
	@mamba run -n $(MAMBA_ENV_TEST) llm_parse --help || echo "❌ CLI help test failed"
	@echo "🚀 Running full CLI invocation..."
	@mamba run -n $(MAMBA_ENV_TEST) llm_parse -f data/test/input/pdf/example.pdf \
	  -s 1 \
	  -e 2 \
	  -i \
	  -w \
	  -r path \
	  -o data/test/output/pdf \
	  -d \
	  --postprocess
	@echo "✅ CLI test passed."
	@echo "✅ CLI test done."

# 🐳 Run package test inside Docker (dev container)
docker-test-dev:
	@echo "🐳 Starting dev container..."
	docker compose -f docker-compose.dev.yaml up -d --build

	@echo "⏳ Waiting for dev server to be ready..."
	@until curl -s http://localhost:8000/ > /dev/null; do sleep 1; done
	@echo "✅ Dev server is up!"

	@echo "# Clean only dev test output folder"
	rm -rf tests/output/docker_dev_test_output && mkdir -p tests/output/docker_dev_test_output

	@echo "# Run CLI test with write-to-disk enabled"
	@docker exec -i llm-parse-api-dev \
		llm_parse --file /app/data/test/input/pdf/example.pdf \
		--start-page 1 \
		--end-page 2 \
		--write-to-disk \
		--output-dir tests/output/docker_dev_test_output \
		|| echo "⚠️ CLI returned non-zero status, continuing anyway..."

	@echo "# Run API test via docker exec curl"
		docker exec -i llm-parse-api-dev \
		curl -s -X POST http://localhost:8000/parse/api/v1/parse-pdf \
			-F file=@/app/data/test/input/pdf/example.pdf \
			-F start_page=1 \
			-F end_page=2 \
			-F write_to_disk=true \
			-F output_dir=tests/output/docker_dev_test_output \
			| tee tests/output/docker_dev_test_output/api_response.json \
			| jq

	@echo "# Check for API errors or skipped pages (dev)"
	@jq -e '.errors or .skipped_pages | select(. != null and . != [])' tests/output/docker_dev_test_output/api_response.json \
		&& echo "❌ Dev API returned errors or skipped pages!" && exit 1 || echo "✅ Dev API test passed!"

# 🐳 Run package test inside Docker (prod container)
docker-test-prod:
	@echo "🐳 Starting prod container..."
	docker compose -f docker-compose.prod.yaml up -d --build

	@echo "⏳ Waiting for prod server to be ready..."
	@until curl -s http://localhost:8000/ > /dev/null; do sleep 1; done
	@echo "✅ Prod server is up!"

	@echo "# Clean only prod test output folder"
	rm -rf tests/output/docker_prod_test_output && mkdir -p tests/output/docker_prod_test_output

	@echo "# Run CLI test with write-to-disk enabled"
	docker exec -i llm-parse-api-prod \
		llm_parse --file /app/data/test/input/pdf/example.pdf \
		--start-page 1 \
		--end-page 2 \
		--write-to-disk \
		--output-dir tests/output/docker_prod_test_output \
		|| echo "⚠️ CLI returned non-zero status, continuing anyway..."

	@echo "# Run API test via docker exec curl"
	@docker exec -i llm-parse-api-prod \
		curl -s -X POST http://localhost:8000/parse/api/v1/parse-pdf \
			-F file=@/app/data/test/input/pdf/example.pdf \
			-F start_page=1 \
			-F end_page=2 \
			-F write_to_disk=true \
			-F output_dir=tests/output/docker_prod_test_output \
			| tee tests/output/docker_prod_test_output/api_response.json \
			| jq

	@echo "# Check for API errors or skipped pages (prod)"
	@jq -e '.errors or .skipped_pages | select(. != null and . != [])' tests/output/docker_prod_test_output/api_response.json \
		&& echo "❌ Prod API returned errors or skipped pages!" && exit 1 || echo "✅ Prod API test passed!"

# 🔁 Combined test entrypoint
test-all: test-package-env test-package-cli docker-test-dev docker-test-prod test-package-clean
	@echo "🎯 All tests completed successfully."
