# ⚙️ Environment Setup

## 1. Install Prerequisites

```bash
brew install direnv mamba
```

Use your package manager:

```bash
# For Ubuntu/Debian
sudo apt install direnv
# Install mamba via conda
conda install mamba -n base -c conda-forge
```

* Use [Miniforge](https://github.com/conda-forge/miniforge) or [Mambaforge](https://github.com/conda-forge/miniforge#mambaforge).
* Optional: `direnv` does not natively work on Windows; skip or use WSL.
* Activate manually: `mamba activate llm_parse`

---

## 2. Clone & Setup Environment

```bash
git clone https://github.com/iota-dreams/llm-parse
cd llm_parse
```

---

## 3. Activate Conda Environment

1. Add to your `~/.zshrc` or `~/.bashrc`:
   ```sh
   eval "$(direnv hook zsh)"  # or bash
   ```
2. Allow the project:
   ```bash
   direnv allow
   ```

This uses the project's pre-configured .envrc file:

```sh
source ~/miniforge3/etc/profile.d/conda.sh
mamba activate llm_parse
```

Manual activation (no direnv):

```bash
source ~/miniforge3/etc/profile.d/conda.sh
mamba activate llm_parse
```

Or on Windows:

```powershell
conda activate llm_parse
```
