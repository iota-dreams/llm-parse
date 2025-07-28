# llm_parse

> An open source package for parsing documents using an LLM.

![PyPI](https://img.shields.io/pypi/v/llm-parse)
![Python](https://img.shields.io/pypi/pyversions/llm-parse)
![License](https://img.shields.io/github/license/iota-dreams/llm-parse)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)
![CLI Support](https://img.shields.io/badge/CLI-Supported-blue?logo=gnu-bash&logoColor=white)
![Docker](https://img.shields.io/badge/docker-available-blue?logo=docker)


## 🗂️ Architecture

![Architecture](docs/images/arch.drawio.png)

✏️ You can edit this diagram directly using [draw.io](https://app.diagrams.net).

## 📦 Installation

```bash
pip install llm-parse
```

## 🧪 Quickstart Example

Parse a PDF using an LLM by loading your model configuration and prompt from `configs/prompts.yaml`. You can use this library either as a Python module or via the built-in FastAPI service.

---

### ▶️ Option 1: Run from Python Script

```python
import os
from llm_parse.models import LLMConfig, LLMParse, TableHandler
from llm_parse.parser import process_pdf
from llm_parse.utils import load_config

# 🔐 Set your API keys as environment variables
# Refer to LangChain's setup guide for different providers:
# https://python.langchain.com/docs/integrations/chat/

# Example for Gemini or OpenAI:
# os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
os.environ["GOOGLE_API_KEY"] = "your-gemini-api-key"

# Load parsing prompt and model config from YAML
raw_config = load_config("configs/prompts.yaml").parser
llm_config = LLMConfig(
    provider=raw_config.provider,
    model_name=raw_config.model_name,
    temperature=raw_config.get("temperature", 0.7),
    prompt=raw_config.prompt,
)

# (Optional) Load image description prompt config if using image parsing
image_config_raw = load_config("configs/prompts.yaml").image_description
image_description_config = LLMConfig(
    provider=image_config_raw.provider,
    model_name=image_config_raw.model_name,
    temperature=image_config_raw.get("temperature", 0.7),
    prompt=image_config_raw.prompt,
)

# Parse the PDF using process_pdf()
results = process_pdf(
    file_path="data/test/input/pdf/sample.pdf",
    parser_config=llm_config,
    image_description_config=image_description_config,
    start_page=1,
    end_page=2,
    enable_image_description=True,
    table_handler=TableHandler.html,
    write_to_disk=True,
    output_dir="data/test/output/pdf",
    return_images="path",  # Can be "path", "base64", or None
)

# Print the text from the first parsed page
print(results[0].text)
```

---

### 🌐 Option 2: Use the FastAPI Server

Start the server:

```bash
uvicorn app.main:app --reload
```

#### ⬆️ Upload a File via /parse-pdf

```bash
curl -X POST http://localhost:8000/api/v1/parse-pdf \
  -F file=@sample.pdf \
  -F enable_image_description=true \
  -F return_images=base64 \
  -F start_page=1 \
  -F end_page=2
```

You'll receive a structured JSON response with extracted text, image descriptions, tables, and metadata.
#### 📘 Alternative: Use Swagger UI

Open http://localhost:8000/docs in your browser to explore all routes with Swagger.

### 📟 Option 3: Use the Command Line Interface

You can also use `llm_parse` as a CLI tool after installing the package:

```bash
llm_parse -f data/test/input/pdf/sample.pdf \
  -s 1 \
  -e 2 \
  -i \
  -w \
  -r path \
  -o data/test/output/pdf \
  -d \
  -q "What is the main idea on this page?" \
  --postprocess
```

#### ✅ CLI Options

Run `llm_parse --help` to see all available options:

```text
usage: llm_parse [-f FILE] [-s START_PAGE] [-e END_PAGE]
                 [-i] [-w] [-r {path,base64,none}]
                 [-o OUTPUT_DIR] [-d]
                 [-q QUESTION] [-p PASSWORD] [--postprocess]

options:
  -f, --file                  Path to input PDF file
  -s, --start-page            Start page number (1-based)
  -e, --end-page              End page number (inclusive)
  -i, --enable-image-description  Enable image captioning
  -w, --write-to-disk         Write outputs to disk
  -r, --return-images         Return image format: path | base64 | none
  -o, --output-dir            Directory to save output files
  -d, --denormalize-images    Apply denormalization to images
  -q, --question              User question for LLM to answer per page
  -p, --password              Password for encrypted PDFs
      --postprocess           Enable document-level post-processing
```

This mode is ideal for scripting, automation, and integration into data pipelines.
### 📁 Prompt Configuration

Prompts are loaded from configs/prompts.yaml, like this:
```yaml
google_genai:
  gemini-1.5-pro-latest:
    parse:
      prompt_template: |
        You are an expert at reading scanned PDFs...
      temperature: 0.2
```

You can customize the provider, model, temperature, and prompt templates per use case.

## 📚 Documentation

* [Developer Setup](docs/markdown/DEVELOPER_SETUP.md)
* [Project Commands](docs/markdown/PROJECT_COMMANDS.md)
* [Environment Setup](docs/markdown/ENVIRONMENT.md)
* [Contributing Guide](CONTRIBUTING.md)
* [Pre-commit Hooks](docs/markdown/PRECOMMIT.md)

---

## 🔗 Contributing

We welcome contributions! Please check the [contribution guide](CONTRIBUTING.md).
