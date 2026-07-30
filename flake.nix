[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "traianus"
version = "0.1.0"
description = "An offline-first deterministic semantic infrastructure"
readme = "README.md"
license = { text = "GPL-3.0-or-later" }
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.28.0",
    "pydantic>=2.6.0",
    "sentence-transformers>=2.5.0",
    "numpy>=1.26.0"
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0"
]