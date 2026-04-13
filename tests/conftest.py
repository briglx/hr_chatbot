import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).parent.parent

@pytest.fixture(scope="session")
def test_docs_dir(project_root):
    return Path(project_root, "tests", "test_docs")


@pytest.fixture(autouse=True)
def mock_settings():
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
    with patch("app.config.settings.get_settings", return_value=settings), \
         patch("app.services.embedding_service.get_settings", return_value=settings):
        yield settings
