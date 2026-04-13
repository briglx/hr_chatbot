import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from ingest_data import chunk_text, insert_document, get_connection, extract_text_from_pdf, extract_text_from_docx, get_embedding, ingest_file, ingest_directory, parse_args, main

SAMPLE_HR_TEXT = """
Employee Code of Conduct:

- Treat colleagues with respect
- Avoid conflicts of interest
- Maintain confidentiality
- Follow company policies

Leave Policies:

- Vacation: 1.25 days/month, max 30 days
- Sick: 10 days/year, carry over 20 days
- Parental: 12 weeks paid leave

Benefits:

- Health, dental, vision
- 401(k) match 4%
- Professional development reimbursement
"""

def make_embedding(dim: int = 1536) -> list[float]:
    return [0.1] * dim

@pytest.fixture
def db_connection():
    """Fixture to provide a database connection and cleanup after test."""
    conn = get_connection()
    conn.autocommit = False  # Use transactions for test isolation
    yield conn
    conn.rollback()  # Rollback any changes made during the test

@pytest.fixture
def mock_conn():
    """Returns a mock psycopg2 connection with a cursor context manager."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


@pytest.fixture(autouse=True)
def azure_env_vars(monkeypatch):
    """Ensures Azure env vars are always set for tests that import the module."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    

class TestExtractTextFromPdf:
    @pytest.mark.unit
    def test_extract_text_from_test_pdf(self, project_root):
        result = extract_text_from_pdf(Path(project_root, "tests", "test_docs", "HRPolicyHandbook.pdf"))
        
        assert "HR Policy Handbook" in result
        assert "retirement plan with 4" in result

    @pytest.mark.unit
    def test_extracts_text_from_all_pages(self):

        mock_page_1 = MagicMock()
        mock_page_1.extract_text.return_value = "Page one content"
        mock_page_2 = MagicMock()
        mock_page_2.extract_text.return_value = "Page two content"

        with patch("ingest_data.PdfReader") as mock_reader_cls:
            mock_reader_cls.return_value.pages = [mock_page_1, mock_page_2]
            result = extract_text_from_pdf(Path("dummy.pdf"))

        assert "Page one content" in result
        assert "Page two content" in result


    @pytest.mark.unit
    def test_handles_empty_page(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None  # some pages return None

        with patch("ingest_data.PdfReader") as mock_reader_cls:
            mock_reader_cls.return_value.pages = [mock_page]
            result = extract_text_from_pdf(Path("dummy.pdf"))

        assert result == ""

class TestExtractTextFromDocx:

    @pytest.mark.unit
    def test_extract_text_from_docx(self):
        para1 = MagicMock()
        para1.text = "Vacation Policy"
        para2 = MagicMock()
        para2.text = "Employees are entitled to 20 days per year."

        with patch("ingest_data.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, para2]
            result = extract_text_from_docx(Path("dummy.docx"))
        
        assert "Vacation Policy" in result
        assert "Employees are entitled to 20 days per year." in result

    @pytest.mark.unit
    def test_skips_empty_paragraphs(self):

        para1 = MagicMock()
        para1.text = "Real content"
        empty = MagicMock()
        empty.text = "   "  # whitespace-only

        with patch("ingest_data.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, empty]
            result = extract_text_from_docx(Path("dummy.docx"))

        assert result == "Real content"

    @pytest.mark.unit
    def test_joins_paragraphs_with_double_newline(self):

        para1 = MagicMock()
        para1.text = "First"
        para2 = MagicMock()
        para2.text = "Second"

        with patch("ingest_data.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, para2]
            result = extract_text_from_docx(Path("dummy.docx"))

        assert result == "First\n\nSecond"

    @pytest.mark.unit
    def test_extract_text_from_test_docx(self, project_root):
        result = extract_text_from_docx(Path(project_root, "tests", "test_docs", "HRPolicyHandbook.docx"))
        
        assert "HR Policy Handbook" in result
        assert "retirement plan with 4" in result


class TestChunkText:

    @pytest.mark.unit
    def test_short_text_returns_single_chunk(self):
        result = chunk_text("Short text", chunk_size=500, overlap=50)
        assert result == ["Short text"]

    @pytest.mark.unit
    def test_long_text_splits_into_multiple_chunks(self):
        text = "A" * 1200
        result = chunk_text(text, chunk_size=500, overlap=50)
        assert len(result) > 1

    @pytest.mark.unit
    def test_chunks_respect_size(self):
        text = "B" * 1000
        result = chunk_text(text, chunk_size=200, overlap=0)
        for chunk in result:
            assert len(chunk) <= 200

    @pytest.mark.unit
    def test_overlap_means_chunks_share_content(self):
        text = "X" * 100
        result = chunk_text(text, chunk_size=60, overlap=20)
        # With overlap, second chunk starts at index 40, which overlaps with first chunk's [40:60]
        assert len(result) >= 2

    @pytest.mark.unit
    def test_empty_text_returns_empty_list(self):
        result = chunk_text("", chunk_size=500, overlap=50)
        assert result == []

    @pytest.mark.unit
    def test_whitespace_only_text_returns_empty_list(self):
        result = chunk_text("   \n  \t  ", chunk_size=500, overlap=50)
        assert result == []


class TestGetEmbedding:

    @pytest.mark.unit
    def test_returns_embedding_vector(self):
        mock_response = MagicMock()
        mock_response.data[0].embedding = make_embedding()

        with patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_response
            result = get_embedding("some HR text")

        assert isinstance(result, list)
        assert len(result) == 1536

    @pytest.mark.unit
    def test_strips_newlines_from_input(self):
        mock_response = MagicMock()
        mock_response.data[0].embedding = make_embedding()

        with patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_response
            get_embedding("line one\nline two\nline three")
            _, kwargs = mock_client.embeddings.create.call_args
            assert "\n" not in kwargs["input"]

    @pytest.mark.unit
    def test_uses_configured_deployment_name(self):
        mock_response = MagicMock()
        mock_response.data[0].embedding = make_embedding()

        with patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_response
            get_embedding("test text")
            _, kwargs = mock_client.embeddings.create.call_args
            assert kwargs["model"] == "text-embedding-3-small"

class TestInsertDocument:

    @pytest.mark.unit
    def test_inserts_with_correct_values(self, mock_conn):
        conn, cursor = mock_conn
        embedding = make_embedding()
        metadata = {"source": "policy.pdf", "chunk_index": 0}

        insert_document(conn, "some content", embedding, metadata)

        cursor.execute.assert_called_once()
        args = cursor.execute.call_args[0]
        assert args[1][0] == "some content"
        assert args[1][1] == embedding
        assert json.loads(args[1][2]) == metadata

    @pytest.mark.unit
    def test_commit_not_called_after_insert(self, mock_conn):
        conn, _ = mock_conn
        insert_document(conn, "content", make_embedding(), {})
        conn.commit.assert_not_called()



class TestIngestFile:

    @pytest.mark.unit
    def test_skips_unsupported_format(self, mock_conn, capsys):
        conn, cursor = mock_conn
        result = ingest_file(Path("notes.txt"), conn)

        assert result == 0
        cursor.execute.assert_not_called()
        assert "skip" in capsys.readouterr().out

    @pytest.mark.unit
    def test_warns_on_empty_extraction(self, mock_conn, capsys):
        conn, cursor = mock_conn

        mock_reader = MagicMock()
        mock_reader.pages = []  # Empty PDF = no pages

        with patch("ingest_data.PdfReader", return_value=mock_reader):
            result = ingest_file(Path("empty.pdf"), conn)

        assert result == 0
        cursor.execute.assert_not_called()
        assert "warn" in capsys.readouterr().out

    @pytest.mark.unit
    def test_returns_chunk_count(self, mock_conn, project_root):
        conn, _ = mock_conn

        mock_embedding_response = MagicMock()
        mock_embedding_response.data[0].embedding = make_embedding()

        test_file = Path(project_root, "tests", "test_docs", "HRPolicyHandbook.pdf")

        with  patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_embedding_response
            result = ingest_file(test_file, conn)

        assert result > 0

    @pytest.mark.unit
    def test_metadata_contains_expected_fields(self, mock_conn, project_root):
        conn, cursor = mock_conn
        mock_embedding_response = MagicMock()
        mock_embedding_response.data[0].embedding = make_embedding()

        test_file = Path(project_root, "tests", "test_docs", "HRPolicyHandbook.pdf")

        with  patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_embedding_response
            _ = ingest_file(test_file, conn)

        # Check metadata on the first insert call
        first_call_args = cursor.execute.call_args_list[0][0]
        metadata = json.loads(first_call_args[1][2])

        assert metadata["source"] == "HRPolicyHandbook.pdf"
        assert metadata["file_type"] == "pdf"
        assert metadata["chunk_index"] == 0
        assert "total_chunks" in metadata

    @pytest.mark.unit
    def test_chunk_indices_are_sequential(self, mock_conn, project_root):
        conn, cursor = mock_conn
        mock_embedding_response = MagicMock()
        mock_embedding_response.data[0].embedding = make_embedding()

        test_file = Path(project_root, "tests", "test_docs", "HRPolicyHandbook.pdf")

        with  patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_embedding_response
            _ = ingest_file(test_file, conn)

        indices = [
            json.loads(c[0][1][2])["chunk_index"]
            for c in cursor.execute.call_args_list
        ]
        assert indices == list(range(len(indices)))


    @pytest.mark.unit
    def test_commit_called_after_file(self, mock_conn, project_root):
        conn, _ = mock_conn
        mock_embedding_response = MagicMock()
        mock_embedding_response.data[0].embedding = make_embedding()

        test_file = Path(project_root, "tests", "test_docs", "HRPolicyHandbook.pdf")

        with  patch("ingest_data.azure_client") as mock_client:
            mock_client.embeddings.create.return_value = mock_embedding_response
            _ = ingest_file(test_file, conn)

        conn.commit.assert_called_once()


class TestIngestDirectory:

    @pytest.mark.unit
    def test_processes_matching_files_only(self, mock_conn, capsys, test_docs_dir):
        conn, _ = mock_conn

        with patch("ingest_data.ingest_file", return_value=3) as mock_ingest:
            ingest_directory(test_docs_dir, ["pdf", "docx"], conn)

        called_names = {call_args[0][0].name for call_args in mock_ingest.call_args_list}
        assert "HRPolicyHandbook.pdf" in called_names
        assert "HRPolicyHandbook.docx" in called_names
        assert "notes.txt" not in called_names

    @pytest.mark.unit
    def test_warns_when_no_files_found(self, mock_conn, capsys, test_docs_dir):
        conn, _ = mock_conn
        ingest_directory(test_docs_dir, ["csv"], conn)  # no CSV files in tmp_docs

        output = capsys.readouterr().out
        assert "No matching files" in output

    @pytest.mark.unit
    def test_prints_total_chunk_count(self, test_docs_dir, mock_conn, capsys):
        conn, _ = mock_conn

        with patch("ingest_data.ingest_file", return_value=5):
            ingest_directory(test_docs_dir, ["pdf", "docx"], conn)

        output = capsys.readouterr().out
        assert "10" in output  # 2 files × 5 chunks each



class TestMain:

    @pytest.mark.unit
    def test_missing_source_raises(self):
        with pytest.raises(SystemExit) as exc:
            parse_args([])  # --source is required, so argparse calls sys.exit(2)
        assert exc.value.code == 2

    @pytest.mark.unit
    def test_valid_args(self):
        args = parse_args(["--source", "/some/path"])
        assert args.source == Path("/some/path")
        assert args.format == "pdf,docx"  # default

    @pytest.mark.unit
    def test_custom_format(self):
        args = parse_args(["--source", "/some/path", "--format", "pdf"])
        assert args.format == "pdf"

    @pytest.mark.unit
    def test_exits_if_azure_endpoint_missing(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["prog", "--source", "/some/path"])  # satisfy argparse


        with pytest.raises(SystemExit) as exc_info:
            main()

        assert "AZURE_OPENAI_ENDPOINT" in str(exc_info.value)

    @pytest.mark.unit
    def test_exits_if_source_is_not_a_directory(self, monkeypatch, tmp_path):
        fake_path = tmp_path / "nonexistent"
        monkeypatch.setattr("sys.argv", ["ingest_data.py", "--source", str(fake_path)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert "not a directory" in str(exc_info.value)

    @pytest.mark.unit
    def test_closes_connection_on_success(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.argv", ["ingest_data.py", "--source", str(tmp_path), "--format", "pdf"])

        mock_conn = MagicMock()

        with patch("ingest_data.get_connection", return_value=mock_conn), \
             patch("ingest_data.ingest_directory"):
            main()

        mock_conn.close.assert_called_once()

    @pytest.mark.unit
    def test_closes_connection_on_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.argv", ["ingest_data.py", "--source", str(tmp_path)])

        mock_conn = MagicMock()

        with patch("ingest_data.get_connection", return_value=mock_conn), \
             patch("ingest_data.ingest_directory", side_effect=RuntimeError("DB error")):
            with pytest.raises(RuntimeError):
                main()

        mock_conn.close.assert_called_once()


# These require a running Postgres instance and valid Azure OpenAI credentials.
# Skip by default unless explicitly opted in with: pytest -m integration

class TestIntegration:

    @pytest.mark.integration
    def test_chunk_text_and_insert(self, db_connection):
        """Test ingestion of sample HR text with dummy embeddings."""

        conn = db_connection

        # Chunk the sample text
        chunks = chunk_text(SAMPLE_HR_TEXT, chunk_size=100, overlap=20)
        assert len(chunks) > 0, "Chunking failed to produce any chunks"

        # Insert chunks with dummy embeddings
        for i, chunk in enumerate(chunks):
            dummy_embedding = [0.0] * 1536
            metadata = {
                "source": "pytest_sample_hr",
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            insert_document(conn, chunk, dummy_embedding, metadata)

        # Verify rows inserted
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents WHERE metadata->>'source' = 'pytest_sample_hr'")
            count = cur.fetchone()[0]

        assert count == len(chunks), f"Expected {len(chunks)} rows, found {count}"


    @pytest.mark.integration
    def test_end_to_end_pdf_ingestion(self, db_connection, project_root):
        """Ingests a real (minimal) PDF and checks a row lands in the DB."""
        test_file = Path(project_root, "tests", "test_docs", "HRPolicyHandbook.pdf")
        conn = db_connection
        result = ingest_file(test_file, conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents WHERE metadata->>'source' = 'HRPolicyHandbook.pdf'")
            count = cur.fetchone()[0]
        assert count > 0
