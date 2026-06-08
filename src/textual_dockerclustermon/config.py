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


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    refresh_seconds: int


def load_config(path: Path) -> AppConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    server = data["server"]
    defaults = data.get("defaults", {})
    kind = str(server["kind"])

    return AppConfig(
        server=_load_server_config(server, kind),
        refresh_seconds=defaults.get("refresh_seconds", 60),
    )


def _load_server_config(server: dict[str, object], kind: str) -> ServerConfig:
    if kind == "demo":
        return DemoServerConfig(name=str(server["name"]))

    if kind == "local":
        return LocalServerConfig(name=str(server["name"]))

    raise ValueError(f"Unsupported server kind: {kind}")
