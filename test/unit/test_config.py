import importlib


def test_production_database_is_rag_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5432/rag")
    monkeypatch.setenv(
        "TRULENS_DATABASE_URL",
        "postgresql+psycopg://rag:rag@localhost:5432/trulens",
    )

    import src.core.config as config_module

    config_module = importlib.reload(config_module)
    assert config_module.Config.DATABASE_URL.endswith("/rag")
    assert config_module.Config.DATABASE_URL != config_module.Config.TRULENS_DATABASE_URL
