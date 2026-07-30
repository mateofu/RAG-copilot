from app.modules.system.application.readiness import CheckReadiness


class StubProbe:
    def __init__(self, name: str, ready: bool) -> None:
        self.name = name
        self._ready = ready

    async def is_ready(self) -> bool:
        return self._ready


class FailingProbe:
    name = "failing"

    async def is_ready(self) -> bool:
        raise RuntimeError("dependency failed")


async def test_readiness_requires_every_dependency() -> None:
    checker = CheckReadiness(
        probes=(
            StubProbe(name="database", ready=True),
            StubProbe(name="redis", ready=False),
        ),
        timeout_seconds=1,
    )

    result = await checker.execute()

    assert result.ready is False
    assert [(item.name, item.ready) for item in result.dependencies] == [
        ("database", True),
        ("redis", False),
    ]


async def test_readiness_converts_probe_errors_to_down_status() -> None:
    checker = CheckReadiness(
        probes=(FailingProbe(),),
        timeout_seconds=1,
    )

    result = await checker.execute()

    assert result.ready is False
    assert result.dependencies[0].name == "failing"
    assert result.dependencies[0].ready is False
