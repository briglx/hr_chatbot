"""This file contains fixtures that are used across multiple test modules. It is automatically discovered by pytest, so you can define fixtures here that will be available in all your test files without needing to import them."""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture(scope="session")
def project_root():
    """Return the root directory of the project (the parent of the directory containing this file)."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_docs_dir(project_root):
    """Return the path to the test_docs directory, which contains sample HR documents for testing."""
    return Path(project_root, "tests", "test_docs")


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock the application settings for all tests, so that we don't make real API calls to Azure OpenAI during testing."""
    settings = MagicMock()
    settings.azure_openai_endpoint = "https://fake-endpoint.openai.azure.com/"
    settings.azure_openai_api_key = "sk-test-fake-key"
    settings.azure_openai_embedding_model = "text-embedding-3-small"
    settings.azure_openai_model = "gpt-4o"
    settings.openai_embedding_dimensions = 1536
    settings.openai_max_tokens = 1024
    settings.openai_temperature = 0.0
    settings.vector_top_k = 5
    settings.is_production = False
    with (
        patch("app.config.settings.get_settings", return_value=settings),
        patch("app.services.embedding_service.get_settings", return_value=settings),
    ):
        yield settings
