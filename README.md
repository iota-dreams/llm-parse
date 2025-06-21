# llm_parse

> An open source package for parsing documents using an LLM.

---

## 🧰 Developer Setup

This project uses:

- [`conda`/`mamba`](https://docs.conda.io/) for environment management
- [`direnv`](https://direnv.net/) for automatic shell activation (optional)
- `black`, `ruff`, `isort` for formatting and linting
- `pre-commit` for enforcing standards
- `Sphinx` with reStructuredText for documentation
- - Automatic requirements extraction via `update_reqs.zsh` from `src/`, `app/`, and `docs/`


---

## ⚙️ Environment Setup

### 1. Install Prerequisites

<details>
<summary>🔵 macOS (using Homebrew)</summary>

```bash
brew install direnv mamba
````

</details>

<details>
<summary>🟢 Linux</summary>

Use your package manager:

```bash
# For Ubuntu/Debian
sudo apt install direnv
# Install mamba via conda
conda install mamba -n base -c conda-forge
```

</details>

<details>
<summary>🟣 Windows (PowerShell or Git Bash)</summary>

* Use [Miniforge](https://github.com/conda-forge/miniforge) or [Mambaforge](https://github.com/conda-forge/miniforge#mambaforge).
* Optional: `direnv` does not natively work on Windows; skip or use WSL.
* Activate manually: `mamba activate llm_parse`

</details>

---

### 2. Clone & Setup Environment

```bash
git clone https://github.com/srikanth-sripada/llm-parse
cd llm_parse
```

---

### 3. Activate Conda Environment

<details>
<summary>Using <code>direnv</code> (Recommended on macOS/Linux)</summary>

1. Add to your `~/.zshrc` or `~/.bashrc`:

   ```sh
   eval "$(direnv hook zsh)"  # or bash
   ```

2. Allow the project:

   ```bash
   direnv allow
   ```

This uses `.envrc`:

```sh
source ~/miniforge3/etc/profile.d/conda.sh
mamba activate llm_parse
```

</details>

<details>
<summary>Without <code>direnv</code></summary>

Activate manually:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
mamba activate llm_parse
```

Or on Windows:

```powershell
conda activate llm_parse
```

</details>

---

## 🚀 Project Commands

Use the `Makefile` for common tasks.

> ⚠️ On Windows without `make`, use WSL or manually run the commands.

### 🔧 Install dependencies and hooks

```bash
make setup
```

### 📦 Update requirements (dev + prod)

```bash
make update-reqs
```

This regenerates:

- `deploy/requirements.txt`: Based on actual imports in `src/`, `app/`, and `docs/`
- `deploy/requirements_dev.txt`: Full `pip freeze`, with a reference to `requirements.txt`

Note: The script skips unnecessary files like `__pycache__`, notebooks, and other non-Python files to keep the output clean.

### 🧼 Format code

```bash
make format
```

### 🔍 Lint code

```bash
make lint
```

### ✅ Format + lint (pre-commit dry run)

```bash
make check
```

### 📘 Build docs

```bash
make docs
```

### 🧽 Clean build artifacts and cache

```bash
make clean
```

---

## 🔒 Pre-commit Hooks

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

---

## 📝 Documentation

Docs live in `docs/` and use Sphinx + reStructuredText.

To view locally:

```bash
make docs
open docs/build/html/index.html  # macOS
xdg-open docs/build/html/index.html  # Linux
start docs/build/html/index.html  # Windows CMD
```

To host externally, the project uses **Read the Docs** via `.readthedocs.yaml`.

---

## 🧪 Testing (Optional)

> Add testing details here once integrated (e.g., `pytest`, `tox`, etc.)

---

## 👥 For New Developers

```bash
git clone https://github.com/srikanth-sripada/llm-parse
cd llm_parse
direnv allow  # or mamba activate llm_parse
make setup
make check
make docs
```

You're ready to go! ✅

---

## 🔗 Contributing

> Contributions are welcome! Please open issues or pull requests.

---