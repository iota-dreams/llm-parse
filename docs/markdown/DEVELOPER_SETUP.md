# 🧰 Developer Setup

This project uses:

* [`conda`](https://docs.conda.io/)[/](https://docs.conda.io/)[`mamba`](https://mamba.readthedocs.io/en/latest/) for environment management
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

---

### 🔐 API Keys & LangChain Configuration

This project uses [LangChain](https://python.langchain.com/docs/introduction/) to dispatch prompts to LLMs.

#### ✅ Required Environment Variables

Depending on your `configs/prompts.yaml` config, you must set provider-specific API keys. For example:

```bash
export GOOGLE_API_KEY="your-google-api-key"
```

> Tip: Add this to your `.bashrc`, `.zshrc`, or `.envrc` for persistence.

Alternatively, use a `.env` file with [python-dotenv](https://saurabh-kumar.com/python-dotenv/) and load it automatically:

```python
from dotenv import load_dotenv
load_dotenv()
```

🔗 [LangChain: Environment Setup](https://python.langchain.com/docs/integrations/chat/)

---

### ⚙️ Prompt Configuration

Parsing logic and image description prompts are defined in `configs/prompts.yaml`. You can customize:

* Model provider (`google_genai`, `openai`, etc.)
* Model name (e.g., `gemini-2.0-flash-001`)
* Temperature and safety settings
* Prompt templates

Prompts are automatically loaded during parsing by matching the `LLMConfig` (provider and model) to the relevant entry in `prompts.yaml`.

Be sure to:

* Match your environment variables to the selected provider
* Set valid model names per provider
* Review or override the prompt templates for your use case

Example entry in `configs/prompts.yaml`:

```yaml
image_description:
  provider: google_genai
  model_name: gemini-2.0-flash-001
  temperature: 0.3
  safety_settings:
  prompt: |
	You are an expert in ...
```
