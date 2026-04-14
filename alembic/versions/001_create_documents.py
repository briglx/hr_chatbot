from alembic import op

# revision identifiers, used by Alembic.
revision = "001_create_documents"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.execute("DROP TABLE IF EXISTS documents")
