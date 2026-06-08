from pathlib import Path

from textual_dockerclustermon.config import AppConfig, load_config
from textual_dockerclustermon.docker import DockerPsQuery
from textual_dockerclustermon.monitor import MonitorService
from textual_dockerclustermon.runner_factory import create_command_runner
from textual_dockerclustermon.ui import DockerClusterMonitorApp


DEFAULT_CONFIG_PATH = Path("dockerclustermon.toml")


def create_app(config_path: Path = DEFAULT_CONFIG_PATH) -> DockerClusterMonitorApp:
    return create_app_from_config(load_config(config_path))


def create_app_from_config(config: AppConfig) -> DockerClusterMonitorApp:
    runner = create_command_runner(config.server)
    docker_ps_query = DockerPsQuery(runner)
    monitor = MonitorService(config.server.name, docker_ps_query)
    return DockerClusterMonitorApp(monitor)


def main() -> None:
    create_app().run()
