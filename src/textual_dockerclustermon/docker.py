import json
from dataclasses import dataclass

from textual_dockerclustermon.commands import CommandError, CommandRunner


DOCKER_PS_COMMAND = "docker ps --format '{{json .}}'"


@dataclass(frozen=True)
class Container:
    id: str
    name: str
    image: str
    status: str
    ports: str


class DockerPsError(Exception):
    pass


class DockerPsQuery:
    def __init__(self, runner: CommandRunner, timeout_seconds: int = 20) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def fetch(self) -> list[Container]:
        try:
            result = self._runner.run(DOCKER_PS_COMMAND, self._timeout_seconds)
        except CommandError as error:
            raise DockerPsError(f"could not run docker ps: {error}") from error

        if result.exit_code != 0:
            raise DockerPsError(
                result.stderr or f"docker ps exited with {result.exit_code}"
            )

        return [self._container_from_line(line) for line in result.stdout.splitlines()]

    def _container_from_line(self, line: str) -> Container:
        data = json.loads(line)
        return Container(
            id=data["ID"],
            name=data["Names"],
            image=data["Image"],
            status=data["Status"],
            ports=data["Ports"],
        )
