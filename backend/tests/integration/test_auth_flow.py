import os
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.infrastructure.database.session import SessionFactory, engine
from app.infrastructure.outbox.models import OutboxEventModel
from app.main import app
from app.modules.documents.application.ingestion import (
    IngestDocument,
    IngestDocumentCommand,
)
from app.modules.documents.infrastructure.extraction.pypdf import PyPdfTextExtractor
from app.modules.documents.infrastructure.persistence.models import (
    DocumentChunkModel,
    DocumentVersionModel,
)
from app.modules.documents.infrastructure.persistence.unit_of_work import (
    SqlAlchemyIngestionUnitOfWork,
)
from app.modules.documents.infrastructure.storage.local import LocalDocumentStorage
from app.modules.identity.infrastructure.persistence.models import (
    OrganizationModel,
    UserModel,
)
from app.modules.identity.infrastructure.tokens import JwtAccessTokenService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="integration tests are disabled",
    ),
]


def make_text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    )
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode())
        content.extend(body)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(content)


async def test_complete_authentication_lifecycle(tmp_path: Path) -> None:
    unique = uuid4().hex
    email = f"auth-{unique}@example.com"
    slug = f"auth-{unique}"
    password = "correct horse battery staple"
    app.state.public_registration_enabled = True
    app.state.access_token_service = JwtAccessTokenService(
        secret="integration-secret-with-at-least-32-characters",
        issuer="integration",
        audience="integration-api",
        ttl=timedelta(minutes=15),
    )
    app.state.document_storage = LocalDocumentStorage(
        tmp_path,
        max_size_bytes=1024 * 1024,
    )
    transport = ASGITransport(app=app)
    registration = None

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            registration = await client.post(
                "/api/v1/organizations",
                json={
                    "organizationName": "Authentication Test",
                    "organizationSlug": slug,
                    "ownerEmail": email,
                    "ownerDisplayName": "Authentication Owner",
                    "ownerPassword": password,
                },
            )
            assert registration.status_code == 201

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200
            original = login.json()

            identity = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {original['accessToken']}"},
            )
            assert identity.status_code == 200
            assert identity.json()["email"] == email
            assert identity.json()["memberships"][0]["role"] == "owner"
            organization_id = identity.json()["memberships"][0]["organizationId"]

            context = await client.get(
                "/api/v1/auth/context",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": organization_id,
                },
            )
            assert context.status_code == 200
            assert context.json()["organizationId"] == organization_id
            assert context.json()["role"] == "owner"
            assert "members:manage" in context.json()["permissions"]

            denied_context = await client.get(
                "/api/v1/auth/context",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": str(uuid4()),
                },
            )
            assert denied_context.status_code == 403
            assert denied_context.json()["detail"]["code"] == "organization_access_denied"

            pdf_content = make_text_pdf("integration document text")
            upload = await client.post(
                "/api/v1/documents",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": organization_id,
                },
                data={"title": "Integration Handbook"},
                files={"file": ("handbook.pdf", pdf_content, "application/pdf")},
            )
            assert upload.status_code == 201
            assert upload.json()["documentNumber"] > 0
            assert upload.json()["versionNumber"] == 1
            assert upload.json()["status"] == "pending"

            duplicate = await client.post(
                "/api/v1/documents",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": organization_id,
                },
                data={"title": "Duplicate Handbook"},
                files={"file": ("duplicate.pdf", pdf_content, "application/pdf")},
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["detail"]["code"] == "duplicate_document"

            async with SessionFactory() as session:
                outbox_event = await session.scalar(
                    select(OutboxEventModel).where(
                        OutboxEventModel.aggregate_id == UUID(upload.json()["versionId"])
                    )
                )
            assert outbox_event is not None
            assert outbox_event.event_type == "document.uploaded"
            assert outbox_event.payload["organizationId"] == organization_id

            ingestion = IngestDocument(
                SqlAlchemyIngestionUnitOfWork(SessionFactory),
                app.state.document_storage,
                PyPdfTextExtractor(),
            )
            ingestion_command = IngestDocumentCommand(
                organization_id=UUID(organization_id),
                version_id=UUID(upload.json()["versionId"]),
            )
            first_ingestion = await ingestion.execute(ingestion_command)
            second_ingestion = await ingestion.execute(ingestion_command)
            assert first_ingestion.chunk_count == 1
            assert not first_ingestion.already_processed
            assert second_ingestion.already_processed

            async with SessionFactory() as session:
                version = await session.get(
                    DocumentVersionModel,
                    ingestion_command.version_id,
                )
                chunks = (
                    await session.scalars(
                        select(DocumentChunkModel).where(
                            DocumentChunkModel.organization_id == ingestion_command.organization_id,
                            DocumentChunkModel.version_id == ingestion_command.version_id,
                        )
                    )
                ).all()
            assert version is not None
            assert version.status.value == "ready"
            assert len(chunks) == 1
            assert chunks[0].content == "integration document text"

            documents = await client.get(
                "/api/v1/documents",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": organization_id,
                },
            )
            assert documents.status_code == 200
            assert documents.json()["total"] == 1
            document_number = documents.json()["items"][0]["documentNumber"]

            document_detail = await client.get(
                f"/api/v1/documents/{document_number}",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": organization_id,
                },
            )
            assert document_detail.status_code == 200
            assert document_detail.json()["status"] == "ready"

            rotation = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": original["refreshToken"]},
            )
            assert rotation.status_code == 200
            replacement = rotation.json()
            assert replacement["refreshToken"] != original["refreshToken"]

            reuse = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": original["refreshToken"]},
            )
            assert reuse.status_code == 401
            assert reuse.json()["detail"]["code"] == "refresh_token_reused"

            revoked_family = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": replacement["refreshToken"]},
            )
            assert revoked_family.status_code == 401

            second_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            second = second_login.json()
            logout = await client.post(
                "/api/v1/auth/logout",
                json={"refreshToken": second["refreshToken"]},
            )
            assert logout.status_code == 204

            identity_after_logout = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {second['accessToken']}"},
            )
            assert identity_after_logout.status_code == 401
    finally:
        async with engine.begin() as connection:
            payload = registration.json() if registration is not None else {}
            organization_id = payload.get("organizationId")
            user_id = payload.get("userId")
            if organization_id:
                await connection.execute(
                    delete(OrganizationModel).where(OrganizationModel.id == UUID(organization_id))
                )
            if user_id:
                await connection.execute(delete(UserModel).where(UserModel.id == UUID(user_id)))
