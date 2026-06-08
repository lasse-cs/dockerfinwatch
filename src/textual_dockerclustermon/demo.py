from datetime import UTC, datetime

from textual_dockerclustermon.docker import Container
from textual_dockerclustermon.monitor import MonitorSnapshot
from textual_dockerclustermon.ui import DockerClusterMonitorApp


class DemoMonitor:
    def refresh(self) -> MonitorSnapshot:
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


def create_demo_app() -> DockerClusterMonitorApp:
    return DockerClusterMonitorApp(DemoMonitor())


def main() -> None:
    create_demo_app().run()
