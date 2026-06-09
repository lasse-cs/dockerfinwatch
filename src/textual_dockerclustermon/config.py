from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import tomllib


@dataclass(frozen=True)
class ServerConfig:
    name: str
    kind: str


@dataclass(frozen=True)
class DemoServerConfig(ServerConfig):
    kind: Literal["demo"] = "demo"


@dataclass(frozen=True)
class LocalServerConfig(ServerConfig):
    kind: Literal["local"] = "local"


@dataclass(frozen=True, kw_only=True)
class SSHServerConfig(ServerConfig):
    kind: Literal["ssh"] = "ssh"
    host: str
    username: str | None = None
    port: int | None = None
    key_filename: str | None = None
    ssh_config_file: str | None = "~/.ssh/config"


@dataclass(frozen=True)
class AppConfig:
    servers: list[ServerConfig]
    refresh_seconds: int


def load_config(path: Path) -> AppConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})

    return AppConfig(
        servers=[
            _load_server_config(server, str(server["kind"]), defaults)
            for server in data["servers"]
        ],
        refresh_seconds=defaults.get("refresh_seconds", 60),
    )


def _load_server_config(
    server: dict[str, object],
    kind: str,
    defaults: dict[str, object],
) -> ServerConfig:
    if kind == "demo":
        return DemoServerConfig(name=str(server["name"]))

    if kind == "local":
        return LocalServerConfig(name=str(server["name"]))

    if kind == "ssh":
        return SSHServerConfig(
            name=str(server["name"]),
            host=str(server["host"]),
            username=_optional_str(server.get("username")),
            port=_optional_int(server.get("port")),
            key_filename=_optional_str(server.get("key_filename")),
            ssh_config_file=_ssh_config_file(
                server.get(
                    "ssh_config_file",
                    defaults.get("ssh_config_file", "~/.ssh/config"),
                )
            ),
        )

    raise ValueError(f"Unsupported server kind: {kind}")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _ssh_config_file(value: object) -> str | None:
    if value is False:
        return None
    return _optional_str(value)
