import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.session import engine
from app.modules.conversations.infrastructure.models import (
    ConversationMessageModel,
    ConversationModel,
)
from app.modules.identity.infrastructure.persistence.models import OrganizationModel

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="integration tests are disabled",
    ),
]


async def test_message_cannot_reference_conversation_from_another_organization() -> None:
    owner_organization_id = uuid4()
    foreign_organization_id = uuid4()
    conversation_id = uuid4()

    async with engine.begin() as connection:
        for index, organization_id in enumerate((owner_organization_id, foreign_organization_id)):
            await connection.execute(
                insert(OrganizationModel).values(
                    id=organization_id,
                    name=f"Conversation Organization {index}",
                    slug=f"conversation-{organization_id}",
                )
            )
        await connection.execute(
            insert(ConversationModel).values(
                id=conversation_id,
                organization_id=owner_organization_id,
                created_by_user_id=uuid4(),
                title="Owner conversation",
            )
        )

    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    insert(ConversationMessageModel).values(
                        id=uuid4(),
                        organization_id=foreign_organization_id,
                        conversation_id=conversation_id,
                        role="user",
                        content="Foreign message",
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(OrganizationModel).where(
                    OrganizationModel.id.in_((owner_organization_id, foreign_organization_id))
                )
            )
