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
from llm_parse.utils import load_config_with_fallback

# 🔐 Set your API keys as environment variables
# Refer to LangChain's setup guide for different providers:
# https://python.langchain.com/docs/integrations/chat/

# Example for Gemini or OpenAI:
# os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
os.environ["GOOGLE_API_KEY"] = "your-gemini-api-key"

example_pdf = "data/test/input/pdf/attention_is_all_you_need.pdf"
start_page = 3
end_page = 6
enable_image_description = True
write_to_disk = True
return_images = "path"
output_dir = "data/test/output/pdf"
denormalize_images = True
user_question = None
password = ""
apply_document_postprocessing = True

# Load parsing prompt and model config from YAML
config = load_config_with_fallback(config_path)
parser_cfg = config.parser
image_cfg = config.image_description

parse_config = LLMConfig(
    provider=parser_cfg.provider,
    model_name=parser_cfg.model_name,
    temperature=parser_cfg.get("temperature", 0),
    prompt=parser_cfg.prompt,
)

image_description_config = LLMConfig(
    provider=image_cfg.provider,
    model_name=image_cfg.model_name,
    temperature=image_cfg.get("temperature", 0),
    prompt=image_cfg.prompt,
)

# Process the PDF
parsed_pdf = process_pdf(
    file_path=example_pdf,
    parser_config=parse_config,
    enable_image_description=enable_image_description,
    image_description_config=image_description_config,
    start_page=start_page,
    end_page=end_page,
    response_model=LLMParse,
    table_handler=TableHandler.html,
    denormalize_images=denormalize_images,
    user_question=user_question,
    password=password,
    write_to_disk=write_to_disk,
    output_dir=output_dir,
    return_images=return_images,
    apply_document_postprocessing=apply_document_postprocessing,
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
llm_parse -f data/test/input/pdf/example.pdf \
  -c configs/prompts.yaml\
  -s 1 \
  -e 2 \
  -i \
  -w \
  -r path \
  -o data/test/output/pdf \
  -d \
  --postprocess \
```

> 🔧 `--config-path` is optional. If not provided, it uses the default bundled config shipped with the package.

---

#### ✅ CLI Options

Run `llm_parse --help` to see all available options:

```text
usage: llm_parse [-h] [-f FILE] [-c CONFIG_PATH] [-s START_PAGE] [-e END_PAGE] [-i] [-w] [-r {path,base64,none}] [-o OUTPUT_DIR] [-d] [-q QUESTION] [-p PASSWORD] [--postprocess]

Parse PDF using LLM-based pipeline.

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Path to input PDF file
  -c CONFIG_PATH, --config-path CONFIG_PATH
                        Path to YAML config file (defaults to built-in config if not provided)
  -s START_PAGE, --start-page START_PAGE
                        Start page number (1-based)
  -e END_PAGE, --end-page END_PAGE
                        End page number (inclusive)
  -i, --enable-image-description
                        Enable image captioning
  -w, --write-to-disk   Write outputs to disk
  -r {path,base64,none}, --return-images {path,base64,none}
                        Return image format
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Directory to save output files
  -d, --denormalize-images
                        Apply denormalization to images
  -q QUESTION, --question QUESTION
                        User question for LLM to answer per page
  -p PASSWORD, --password PASSWORD
                        Password for encrypted PDFs
  --postprocess         Enable document-level post-processing
```

---

### 📁 Prompt Configuration

By default, prompts are loaded from a bundled YAML config shipped with the package.
To use your own, pass it via `--config-path`:

```bash
llm_parse ... --config-path configs/my_custom_prompts.yaml
```

The config should be a `yaml` and should follow the below schema:

```yaml
parser:
  provider: google_genai
  model_name: gemini-2.5-flash
  temperature: 0
  safety_settings:
  prompt: |
    You are an expert in ...
```

You can define multiple models and prompts under different providers.

## 📚 Documentation

* [Developer Setup](docs/markdown/DEVELOPER_SETUP.md)
* [Project Commands](docs/markdown/PROJECT_COMMANDS.md)
* [Environment Setup](docs/markdown/ENVIRONMENT.md)
* [Contributing Guide](CONTRIBUTING.md)
* [Pre-commit Hooks](docs/markdown/PRECOMMIT.md)

---

## 🔗 Contributing

We welcome contributions! Please check the [contribution guide](CONTRIBUTING.md).
