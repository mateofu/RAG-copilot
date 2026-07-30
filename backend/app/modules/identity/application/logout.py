from datetime import UTC, datetime
from typing import cast

from app.modules.identity.application.ports import IdentityUnitOfWork
from app.modules.identity.application.refresh import RefreshRepository


class Logout:
    def __init__(self, unit_of_work: IdentityUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, token_hash: str) -> None:
        async with self._unit_of_work:
            repository = cast(RefreshRepository, self._unit_of_work.repository)
            session = await repository.lock_refresh_session(token_hash)
            if session is None:
                return
            await repository.revoke_session_family(session.family_id, datetime.now(UTC))
            await self._unit_of_work.commit()
