import argparse
import os
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from pathlib import Path

from dockerfinwatch.commands import CommandRunner
from dockerfinwatch.config import AppConfig, ServerConfig, load_config
from dockerfinwatch.docker import (
    DockerContainerQuery,
    DockerPsQuery,
    DockerStatsQuery,
)
from dockerfinwatch.monitor import MonitorService
from dockerfinwatch.runner_factory import create_command_runner
from dockerfinwatch.ui import DockerClusterMonitorApp


CONFIG_ENV_VAR = "DOCKERFINWATCH_CONFIG"
CONFIG_FILENAME = "config.toml"
CONFIG_DIR_NAME = "dockerfinwatch"
CommandRunnerFactory = Callable[[ServerConfig], CommandRunner]


def create_app(
    config_path: Path,
    command_runner_factory: CommandRunnerFactory = create_command_runner,
) -> DockerClusterMonitorApp:
    return create_app_from_config(load_config(config_path), command_runner_factory)


def resolve_config_path(
    config_path: Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    environ = os.environ if environ is None else environ

    if config_path is not None:
        return _expand_user(config_path, home)

    env_config_path = environ.get(CONFIG_ENV_VAR)
    if env_config_path is not None:
        return _expand_user(Path(env_config_path), home)

    config_home = environ.get("XDG_CONFIG_HOME")
    if config_home is None:
        config_home_path = (Path.home() if home is None else home) / ".config"
    else:
        config_home_path = _expand_user(Path(config_home), home)

    return config_home_path / CONFIG_DIR_NAME / CONFIG_FILENAME


def config_path_from_args(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    args = _argument_parser().parse_args(argv)
    return resolve_config_path(args.config, environ=environ, home=home)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to config TOML file.",
    )
    return parser


def _expand_user(path: Path, home: Path | None) -> Path:
    if home is None:
        return path.expanduser()

    path_string = str(path)
    if path_string == "~":
        return home
    if path_string.startswith("~/"):
        return home / path_string[2:]
    return path


def create_app_from_config(
    config: AppConfig,
    command_runner_factory: CommandRunnerFactory = create_command_runner,
) -> DockerClusterMonitorApp:
    monitors = []
    for server in config.servers:
        stack = ExitStack()
        runner = stack.enter_context(command_runner_factory(server))
        docker_query = DockerContainerQuery(
            DockerPsQuery(runner),
            [DockerStatsQuery(runner)],
        )
        monitors.append(MonitorService(server.name, docker_query, cleanup=stack.close))

    return DockerClusterMonitorApp(monitors, config.refresh_seconds)


def main(argv: list[str] | None = None) -> None:
    create_app(config_path_from_args(argv)).run()
