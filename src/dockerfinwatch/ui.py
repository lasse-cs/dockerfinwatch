from typing import Protocol

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static

from dockerfinwatch.monitor import MonitorLogsError, MonitorRefreshError, MonitorSnapshot


CONTAINER_NAME_COLUMN_KEY = "name"
CONTAINER_ID_COLUMN_KEY = "id"


class Monitor(Protocol):
    @property
    def server_name(self) -> str: ...

    def refresh(self) -> MonitorSnapshot: ...

    def fetch_logs(self, container_id: str, tail: int) -> str: ...

    def close(self) -> None: ...


class LogsScreen(ModalScreen[None]):
    BINDINGS = [
        ("r", "refresh_logs", "Refresh"),
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def __init__(
        self,
        monitor: Monitor,
        container_id: str,
        container_name: str,
        tail: int,
    ) -> None:
        super().__init__()
        self._monitor = monitor
        self._container_id = container_id
        self._container_name = container_name
        self._tail = tail
        self._refresh_in_progress = False

    def compose(self) -> ComposeResult:
        with Vertical(id="logs-dialog"):
            yield Static(
                self._title_text(),
                id="logs-title",
            )
            with VerticalScroll(id="logs-scroll"):
                yield Static("Loading...", id="logs-content", markup=False)
            yield Footer()

    def on_mount(self) -> None:
        self.query_one("#logs-scroll", VerticalScroll).anchor()
        self._refresh_logs("loading...", clear_content=True)

    def action_refresh_logs(self) -> None:
        self._refresh_logs("refreshing...")

    def _refresh_logs(self, status: str, *, clear_content: bool = False) -> None:
        if self._refresh_in_progress:
            return

        self._refresh_in_progress = True
        self.query_one("#logs-title", Static).update(self._title_text(status))
        if clear_content:
            self.query_one("#logs-content", Static).update("Loading...")
        self._fetch_logs_in_background()

    @work(thread=True)
    def _fetch_logs_in_background(self) -> None:
        try:
            logs = self._monitor.fetch_logs(self._container_id, tail=self._tail)
        except MonitorLogsError as error:
            self.app.call_from_thread(self._complete_refresh, f"Error: {error}")
        except Exception as error:
            self.app.call_from_thread(self._raise_fatal, error)
        else:
            self.app.call_from_thread(self._complete_refresh, logs or "(no output)")

    def _complete_refresh(self, content: str) -> None:
        self._refresh_in_progress = False
        self.query_one("#logs-title", Static).update(self._title_text())
        self.query_one("#logs-content", Static).update(content)

    def _title_text(self, status: str | None = None) -> str:
        title = f"Logs: {self._container_name} (last {self._tail} lines)"
        if status is not None:
            return f"{title} | {status}"
        return title

    def _raise_fatal(self, error: Exception) -> None:
        raise error


class ServerMonitorView(Vertical):
    BINDINGS = [("l", "view_logs", "View Logs")]

    def __init__(
        self,
        monitor: Monitor,
        index: int,
        refresh_seconds: float,
        log_tail_lines: int,
    ) -> None:
        super().__init__(id=f"server-{index}", classes="server-view")
        self._monitor = monitor
        self._index = index
        self._refresh_seconds = refresh_seconds
        self._log_tail_lines = log_tail_lines
        self._refresh_in_progress = False
        self._ready = False

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self._monitor.server_name} | waiting for first refresh...",
            id=f"server-status-{self._index}",
            classes="server-status",
        )
        table = DataTable(
            show_row_labels=False,
            zebra_stripes=True,
            cursor_type="row",
            id=f"containers-{self._index}",
            classes="server-containers",
        )
        table.loading = True
        yield table

    def on_mount(self) -> None:
        table = self.query_one(f"#containers-{self._index}", DataTable)
        table.add_columns(
            ("Name", CONTAINER_NAME_COLUMN_KEY),
            "Image",
            "Status",
            "CPU",
            "Memory",
            "Mem %",
            "Net I/O",
            "Block I/O",
            "PIDs",
            "Ports",
            ("ID", CONTAINER_ID_COLUMN_KEY),
        )
        self._ready = True
        self.set_interval(self._refresh_seconds, self.refresh_monitor)
        self.refresh_monitor()

    def refresh_monitor(self) -> None:
        if not self._ready:
            return

        if self._refresh_in_progress:
            return

        self._refresh_in_progress = True
        self._show_status(f"{self._monitor.server_name} | refreshing...", "refreshing")
        self._refresh_in_background()

    @work(thread=True)
    def _refresh_in_background(self) -> None:
        try:
            snapshot = self._monitor.refresh()
        except MonitorRefreshError as error:
            self.app.call_from_thread(self._complete_refresh_error, str(error))
        except Exception as error:
            self.app.call_from_thread(self._raise_fatal, error)
        else:
            self.app.call_from_thread(self._complete_refresh_success, snapshot)

    def _complete_refresh_error(self, message: str) -> None:
        self._refresh_in_progress = False
        self._finish_loading()
        self._show_status(f"{self._monitor.server_name} | {message}", "error")

    def _complete_refresh_success(self, snapshot: MonitorSnapshot) -> None:
        self._refresh_in_progress = False
        self._show_snapshot(snapshot)

    def _raise_fatal(self, error: Exception) -> None:
        raise error

    def _show_status(self, message: str, state: str | None = None) -> None:
        status = self.query_one(f"#server-status-{self._index}", Static)
        self.remove_class("is-ready", "is-refreshing", "is-error")
        status.remove_class("is-ready", "is-refreshing", "is-error")

        if state is not None:
            class_name = f"is-{state}"
            self.add_class(class_name)
            status.add_class(class_name)

        status.update(message)

    def _show_snapshot(self, snapshot: MonitorSnapshot) -> None:
        table = self.query_one(f"#containers-{self._index}", DataTable)
        self._finish_loading()

        table.clear()
        table.add_rows(
            (
                (
                    container.metadata.name,
                    container.metadata.image,
                    container.metadata.status,
                    container.stats.cpu_percent if container.stats else "-",
                    container.stats.memory_usage if container.stats else "-",
                    container.stats.memory_percent if container.stats else "-",
                    container.stats.network_io if container.stats else "-",
                    container.stats.block_io if container.stats else "-",
                    container.stats.pids if container.stats else "-",
                    container.metadata.ports,
                    container.metadata.id,
                )
                for container in snapshot.containers
            )
        )
        local_time = snapshot.updated_at.astimezone()
        self._show_status(
            f"{snapshot.server_name} | last updated {local_time:%H:%M:%S %Z}",
            "ready",
        )

    def action_view_logs(self) -> None:
        table = self.query_one(f"#containers-{self._index}", DataTable)
        if table.row_count == 0:
            return

        idx = table.cursor_row
        if idx >= table.row_count:
            return

        container_name = table.get_cell_at(
            Coordinate(idx, table.get_column_index(CONTAINER_NAME_COLUMN_KEY))
        )
        container_id = table.get_cell_at(
            Coordinate(idx, table.get_column_index(CONTAINER_ID_COLUMN_KEY))
        )
        self.app.push_screen(
            LogsScreen(
                self._monitor,
                str(container_id),
                str(container_name),
                self._log_tail_lines,
            )
        )

    def _finish_loading(self) -> None:
        table = self.query_one(f"#containers-{self._index}", DataTable)
        table.loading = False


class DockerFinWatchApp(App[None]):
    TITLE = "Docker Fin Watch"
    CSS_PATH = "ui.tcss"

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        monitors: list[Monitor],
        refresh_seconds: float,
        log_tail_lines: int,
    ) -> None:
        super().__init__()
        self._monitors = monitors
        self._refresh_seconds = refresh_seconds
        self._log_tail_lines = log_tail_lines

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._server_count_status(), id="status")
        with VerticalScroll(id="servers"):
            for index, monitor in enumerate(self._monitors):
                yield ServerMonitorView(
                    monitor,
                    index,
                    self._refresh_seconds,
                    self._log_tail_lines,
                )
        yield Footer()

    def action_refresh(self) -> None:
        self._refresh()

    def on_unmount(self) -> None:
        for monitor in self._monitors:
            monitor.close()

    def _refresh(self) -> None:
        for server_view in self.query(ServerMonitorView):
            server_view.refresh_monitor()

    def _server_count_status(self) -> str:
        server_count = len(self._monitors)
        label = "server" if server_count == 1 else "servers"
        return f"{server_count} {label}"
