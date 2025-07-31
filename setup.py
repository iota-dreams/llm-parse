import os
import re

from setuptools import find_packages, setup


def read_version():
    version_file = os.path.join("src", "llm_parse", "version.py")
    with open(version_file, "r") as f:
        content = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def read_requirements():
    req_file = os.path.join("deploy", "requirements.txt")
    with open(req_file, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


# Optional cloud logging dependencies
extras = {
    "cloud": [
        "google-cloud-logging",
        "watchtower",
        "opencensus-ext-azure",
        "sentry-sdk",
    ],
}

setup(
    name="llmparse",
    version=read_version(),
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=read_requirements(),
    extras_require=extras,
    description="An open source package for parsing documents using an LLM",
    author="Srikanth Sripada",
    author_email="srikanth6991@gmail.com",
    url="https://github.com/iota-dreams/llm-parse",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "llm_parse = llm_parse.main:main",
        ],
    },
)
