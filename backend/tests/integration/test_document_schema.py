import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.session import engine
from app.modules.documents.infrastructure.persistence.models import (
    DocumentModel,
    DocumentVersionModel,
)
from app.modules.identity.infrastructure.persistence.models import OrganizationModel

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="integration tests are disabled",
    ),
]


async def test_document_hash_is_unique_inside_an_organization() -> None:
    organization_id = uuid4()
    first_document_id = uuid4()
    second_document_id = uuid4()
    sha256 = "a" * 64

    async with engine.begin() as connection:
        await connection.execute(
            insert(OrganizationModel).values(
                id=organization_id,
                name="Document Test",
                slug=f"document-{organization_id}",
            )
        )
        for document_id, title in (
            (first_document_id, "First"),
            (second_document_id, "Second"),
        ):
            await connection.execute(
                insert(DocumentModel).values(
                    id=document_id,
                    organization_id=organization_id,
                    title=title,
                    created_by_user_id=uuid4(),
                )
            )
        await connection.execute(
            insert(DocumentVersionModel).values(
                id=uuid4(),
                organization_id=organization_id,
                document_id=first_document_id,
                version_number=1,
                original_filename="first.pdf",
                media_type="application/pdf",
                size_bytes=100,
                sha256=sha256,
                storage_key="organizations/test/first.pdf",
            )
        )

    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    insert(DocumentVersionModel).values(
                        id=uuid4(),
                        organization_id=organization_id,
                        document_id=second_document_id,
                        version_number=1,
                        original_filename="second.pdf",
                        media_type="application/pdf",
                        size_bytes=100,
                        sha256=sha256,
                        storage_key="organizations/test/second.pdf",
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(OrganizationModel).where(OrganizationModel.id == organization_id)
            )


async def test_same_hash_is_allowed_for_different_organizations() -> None:
    organization_ids = (uuid4(), uuid4())
    sha256 = "b" * 64

    try:
        async with engine.begin() as connection:
            for organization_id in organization_ids:
                document_id = uuid4()
                await connection.execute(
                    insert(OrganizationModel).values(
                        id=organization_id,
                        name=f"Organization {organization_id}",
                        slug=f"document-{organization_id}",
                    )
                )
                await connection.execute(
                    insert(DocumentModel).values(
                        id=document_id,
                        organization_id=organization_id,
                        title="Shared Hash",
                        created_by_user_id=uuid4(),
                    )
                )
                await connection.execute(
                    insert(DocumentVersionModel).values(
                        id=uuid4(),
                        organization_id=organization_id,
                        document_id=document_id,
                        version_number=1,
                        original_filename="shared.pdf",
                        media_type="application/pdf",
                        size_bytes=100,
                        sha256=sha256,
                        storage_key=f"organizations/{organization_id}/shared.pdf",
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(OrganizationModel).where(OrganizationModel.id.in_(organization_ids))
            )


async def test_version_cannot_reference_a_document_from_another_organization() -> None:
    owner_organization_id = uuid4()
    foreign_organization_id = uuid4()
    document_id = uuid4()

    async with engine.begin() as connection:
        for organization_id in (owner_organization_id, foreign_organization_id):
            await connection.execute(
                insert(OrganizationModel).values(
                    id=organization_id,
                    name=f"Organization {organization_id}",
                    slug=f"document-{organization_id}",
                )
            )
        await connection.execute(
            insert(DocumentModel).values(
                id=document_id,
                organization_id=owner_organization_id,
                title="Owner Document",
                created_by_user_id=uuid4(),
            )
        )

    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    insert(DocumentVersionModel).values(
                        id=uuid4(),
                        organization_id=foreign_organization_id,
                        document_id=document_id,
                        version_number=1,
                        original_filename="foreign.pdf",
                        media_type="application/pdf",
                        size_bytes=100,
                        sha256="c" * 64,
                        storage_key="organizations/foreign/foreign.pdf",
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(OrganizationModel).where(
                    OrganizationModel.id.in_((owner_organization_id, foreign_organization_id))
                )
            )
