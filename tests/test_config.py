import pytest

from textual_dockerclustermon.config import DemoServerConfig, load_config


def test_load_config_reads_demo_server_from_toml(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[server]
name = "demo"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.server, DemoServerConfig)
    assert config.server.name == "demo"
    assert config.server.kind == "demo"
    assert config.refresh_seconds == 60


def test_load_config_reads_refresh_seconds_default(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[defaults]
refresh_seconds = 30

[server]
name = "demo"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.refresh_seconds == 30


def test_load_config_rejects_unknown_server_kind(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[server]
name = "prod"
kind = "unknown"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as error:
        load_config(config_path)

    assert "Unsupported server kind: unknown" in str(error.value)
