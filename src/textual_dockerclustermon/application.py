from collections.abc import Callable
from pathlib import Path

from textual_dockerclustermon.commands import CommandRunner
from textual_dockerclustermon.config import AppConfig, ServerConfig, load_config
from textual_dockerclustermon.docker import DockerPsQuery
from textual_dockerclustermon.monitor import MonitorService
from textual_dockerclustermon.runner_factory import create_command_runner
from textual_dockerclustermon.ui import DockerClusterMonitorApp


DEFAULT_CONFIG_PATH = Path("dockerclustermon.toml")
CommandRunnerFactory = Callable[[ServerConfig], CommandRunner]


def create_app(
    config_path: Path = DEFAULT_CONFIG_PATH,
    command_runner_factory: CommandRunnerFactory = create_command_runner,
) -> DockerClusterMonitorApp:
    return create_app_from_config(load_config(config_path), command_runner_factory)


def create_app_from_config(
    config: AppConfig,
    command_runner_factory: CommandRunnerFactory = create_command_runner,
) -> DockerClusterMonitorApp:
    runner = command_runner_factory(config.server)
    docker_ps_query = DockerPsQuery(runner)
    monitor = MonitorService(config.server.name, docker_ps_query)
    return DockerClusterMonitorApp(monitor, config.refresh_seconds)


def main() -> None:
    create_app().run()
