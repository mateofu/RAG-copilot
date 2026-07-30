import asyncio
from dataclasses import dataclass
from typing import Protocol


class DependencyProbe(Protocol):
    name: str

    async def is_ready(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class DependencyReadiness:
    name: str
    ready: bool


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    ready: bool
    dependencies: tuple[DependencyReadiness, ...]


class CheckReadiness:
    def __init__(
        self,
        probes: tuple[DependencyProbe, ...],
        timeout_seconds: float,
    ) -> None:
        self._probes = probes
        self._timeout_seconds = timeout_seconds

    async def execute(self) -> ReadinessResult:
        dependencies = tuple(
            await asyncio.gather(*(self._check_probe(probe) for probe in self._probes))
        )
        return ReadinessResult(
            ready=all(dependency.ready for dependency in dependencies),
            dependencies=dependencies,
        )

    async def _check_probe(self, probe: DependencyProbe) -> DependencyReadiness:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                ready = await probe.is_ready()
        except Exception:
            ready = False

        return DependencyReadiness(name=probe.name, ready=ready)
