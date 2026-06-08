from datetime import UTC, datetime

from textual_dockerclustermon.docker import Container, DockerPsError
from textual_dockerclustermon.monitor import MonitorSnapshot
from textual_dockerclustermon.ui import DockerClusterMonitorApp


class DemoMonitor:
    def __init__(self) -> None:
        self._should_fail = False

    def show_error(self) -> None:
        self._should_fail = True

    def show_sample_data(self) -> None:
        self._should_fail = False

    def refresh(self) -> MonitorSnapshot:
        if self._should_fail:
            raise DockerPsError("demo permission denied")

        return MonitorSnapshot(
            server_name="demo-server",
            containers=[
                Container(
                    id="abc123",
                    name="web",
                    image="nginx:latest",
                    status="Up 2 minutes",
                    ports="0.0.0.0:8080->80/tcp",
                ),
                Container(
                    id="def456",
                    name="cache",
                    image="redis:7",
                    status="Up 1 hour",
                    ports="6379/tcp",
                ),
            ],
            updated_at=datetime(2026, 6, 8, 12, 30, tzinfo=UTC),
        )


class DemoDockerClusterMonitorApp(DockerClusterMonitorApp):
    BINDINGS = [
        *DockerClusterMonitorApp.BINDINGS,
        ("e", "demo_error", "Demo Error"),
        ("s", "demo_sample", "Demo Sample"),
    ]

    def __init__(self, monitor: DemoMonitor) -> None:
        super().__init__(monitor)
        self._demo_monitor = monitor

    def action_demo_error(self) -> None:
        self._demo_monitor.show_error()
        self._refresh()

    def action_demo_sample(self) -> None:
        self._demo_monitor.show_sample_data()
        self._refresh()


def create_demo_app() -> DockerClusterMonitorApp:
    return DemoDockerClusterMonitorApp(DemoMonitor())


def main() -> None:
    create_demo_app().run()
