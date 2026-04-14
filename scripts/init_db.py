from app.config.settings import get_settings


def main():

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
