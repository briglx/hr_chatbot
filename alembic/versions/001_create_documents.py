"""Create documents table."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_create_documents"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade the database schema by creating the 'documents' table with the necessary columns and indexes for storing document content, metadata, and vector embeddings for efficient similarity search."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE documents (
            id        SERIAL PRIMARY KEY,
            content   TEXT NOT NULL,
            source    TEXT NOT NULL DEFAULT '',
            metadata  JSONB,
            embedding vector(1536)
        )
    """)
    op.execute("""
        CREATE INDEX ON documents
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    """Downgrade the database schema by dropping the 'documents' table, which will remove all stored documents, metadata, and embeddings. This operation is irreversible and should be used with caution in a production environment."""
    op.execute("DROP TABLE IF EXISTS documents")
