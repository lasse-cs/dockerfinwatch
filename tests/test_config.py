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
[[servers]]
name = "demo"
kind = "demo"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert len(config.servers) == 1
    assert isinstance(config.servers[0], DemoServerConfig)
    assert config.servers[0].name == "demo"
    assert config.servers[0].kind == "demo"
    assert config.refresh_seconds == 60


def test_load_config_reads_multiple_servers_from_toml(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[[servers]]
name = "local"
kind = "local"

[[servers]]
name = "prod"
kind = "ssh"
host = "prod.example.com"
username = "deploy"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert len(config.servers) == 2
    assert isinstance(config.servers[0], LocalServerConfig)
    assert config.servers[0].name == "local"
    assert isinstance(config.servers[1], SSHServerConfig)
    assert config.servers[1].name == "prod"
    assert config.servers[1].host == "prod.example.com"


def test_load_config_reads_refresh_seconds_default(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[defaults]
refresh_seconds = 30

[[servers]]
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
[[servers]]
name = "local"
kind = "local"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.servers[0], LocalServerConfig)
    assert config.servers[0].name == "local"
    assert config.servers[0].kind == "local"


def test_load_config_reads_ssh_server_from_toml(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[[servers]]
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

    assert isinstance(config.servers[0], SSHServerConfig)
    assert config.servers[0].name == "prod"
    assert config.servers[0].kind == "ssh"
    assert config.servers[0].host == "prod.example.com"
    assert config.servers[0].username == "deploy"
    assert config.servers[0].port == 2222
    assert config.servers[0].key_filename == "/home/me/.ssh/id_ed25519"
    assert config.servers[0].ssh_config_file == "~/.ssh/config"


def test_load_config_defaults_ssh_optional_fields(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[[servers]]
name = "prod"
kind = "ssh"
host = "prod.example.com"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.servers[0], SSHServerConfig)
    assert config.servers[0].username is None
    assert config.servers[0].port is None
    assert config.servers[0].key_filename is None
    assert config.servers[0].ssh_config_file == "~/.ssh/config"


def test_load_config_reads_ssh_config_file_default(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    ssh_config_path = tmp_path / "ssh_config"
    config_path.write_text(
        f"""
[defaults]
ssh_config_file = "{ssh_config_path}"

[[servers]]
name = "prod"
kind = "ssh"
host = "prod.example.com"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.servers[0], SSHServerConfig)
    assert config.servers[0].ssh_config_file == str(ssh_config_path)


def test_load_config_can_disable_ssh_config_file(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[defaults]
ssh_config_file = false

[[servers]]
name = "prod"
kind = "ssh"
host = "prod.example.com"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config.servers[0], SSHServerConfig)
    assert config.servers[0].ssh_config_file is None


def test_load_config_rejects_unknown_server_kind(tmp_path) -> None:
    config_path = tmp_path / "dockerclustermon.toml"
    config_path.write_text(
        """
[[servers]]
name = "prod"
kind = "unknown"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as error:
        load_config(config_path)

    assert "Unsupported server kind: unknown" in str(error.value)
