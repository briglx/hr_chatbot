"""This script is responsible for initializing the database by running Alembic migrations. It can be executed manually or as part of an automated deployment process to ensure that the database schema is up to date before the application starts."""

from app.config.settings import get_settings


def main():
    """Entry point for the database initialization script. This function retrieves the application settings and prints the database URL. In a real implementation, it would also run Alembic migrations to update the database schema."""
    settings = get_settings()
    print(settings.database_url)

    # result = subprocess.run(
    #     ["alembic", "upgrade", "head"],
    #     capture_output=True, text=True
    # )
    # print(result.stdout)
    # if result.returncode != 0:
    #     print(result.stderr)
    #     sys.exit(1)


if __name__ == "__main__":
    main()
