import pytest

from textual_dockerclustermon.config import (
    DemoServerConfig,
    LocalServerConfig,
    SSHServerConfig,
    load_config,
)


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


def test_load_config_reads_local_server_from_toml(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[server]
name = "local"
kind = "local"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.server, LocalServerConfig)
    assert config.server.name == "local"
    assert config.server.kind == "local"


def test_load_config_reads_ssh_server_from_toml(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[server]
name = "prod"
kind = "ssh"
host = "prod.example.com"
username = "deploy"
port = 2222
key_filename = "/home/me/.ssh/id_ed25519"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.server, SSHServerConfig)
    assert config.server.name == "prod"
    assert config.server.kind == "ssh"
    assert config.server.host == "prod.example.com"
    assert config.server.username == "deploy"
    assert config.server.port == 2222
    assert config.server.key_filename == "/home/me/.ssh/id_ed25519"
    assert config.server.ssh_config_file == "~/.ssh/config"


def test_load_config_defaults_ssh_optional_fields(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[server]
name = "prod"
kind = "ssh"
host = "prod.example.com"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.server, SSHServerConfig)
    assert config.server.username is None
    assert config.server.port is None
    assert config.server.key_filename is None
    assert config.server.ssh_config_file == "~/.ssh/config"


def test_load_config_reads_ssh_config_file_default(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    ssh_config_path = tmp_path / "ssh_config"
    config_path.write_text(
        f"""
[defaults]
ssh_config_file = "{ssh_config_path}"

[server]
name = "prod"
kind = "ssh"
host = "prod.example.com"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.server, SSHServerConfig)
    assert config.server.ssh_config_file == str(ssh_config_path)


def test_load_config_can_disable_ssh_config_file(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[defaults]
ssh_config_file = false

[server]
name = "prod"
kind = "ssh"
host = "prod.example.com"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.server, SSHServerConfig)
    assert config.server.ssh_config_file is None


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
