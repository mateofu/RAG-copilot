import { expect, test } from "@playwright/test";

test("authenticates and navigates through the tenant workspace", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      json: {
        accessToken: "access-token",
        refreshToken: "refresh-token",
        tokenType: "bearer",
      },
    });
  });
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      json: {
        userId: "10c5e939-d6a1-41ba-b73a-fc32a99f0c90",
        email: "owner@example.com",
        displayName: "Ada Lovelace",
        memberships: [
          {
            organizationId: "e8209087-e14a-45d9-a35f-a91d531df933",
            organizationName: "Acme Knowledge",
            organizationSlug: "acme",
            role: "owner",
          },
        ],
      },
    });
  });
  await page.route("**/api/v1/conversations**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/conversations")) {
      await route.fulfill({
        json: {
          items: [
            {
              conversationId: "bc469819-ff34-44f6-91c6-ef07fc34a98d",
              title: "Política de vacaciones",
              messageCount: 2,
              createdAt: "2026-07-31T12:00:00Z",
              updatedAt: "2026-07-31T12:01:00Z",
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        },
      });
      return;
    }
    await route.fulfill({
      json: {
        conversationId: "bc469819-ff34-44f6-91c6-ef07fc34a98d",
        title: "Política de vacaciones",
        createdAt: "2026-07-31T12:00:00Z",
        updatedAt: "2026-07-31T12:01:00Z",
        messages: [
          {
            messageId: "22dd7f1a-8551-4eb9-a258-715c377c8382",
            role: "user",
            content: "¿Cuántos días tengo?",
            inputTokens: 0,
            outputTokens: 0,
            createdAt: "2026-07-31T12:00:00Z",
            citations: [],
          },
          {
            messageId: "609816d1-a37d-42ac-84f9-eef1a0549fe8",
            role: "assistant",
            content: "Tienes quince días hábiles [1].",
            inputTokens: 20,
            outputTokens: 8,
            createdAt: "2026-07-31T12:01:00Z",
            citations: [
              {
                index: 1,
                chunkId: "d2060291-3d61-4a83-98fc-e67dc9c377e0",
                documentId: "b1632ab0-909a-4106-94a4-ab4f4e2cb90a",
                documentNumber: 1,
                documentTitle: "Manual laboral",
                versionId: "3af5ae00-21e1-4bd5-a701-bb49bfb27bf7",
                pageNumber: 7,
                content: "Cada empleado dispone de quince días hábiles.",
                score: 0.94,
              },
            ],
          },
        ],
      },
    });
  });
  await page.route("**/api/v1/documents**", async (route) => {
    await route.fulfill({
      json: { items: [], total: 0, limit: 100, offset: 0 },
    });
  });

  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill("owner@example.com");
  const passwordInput = page.getByLabel("Contraseña", { exact: true });
  await passwordInput.fill("a-secure-password");
  await page.getByRole("button", { name: "Mostrar contraseña" }).click();
  await expect(passwordInput).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Ocultar contraseña" }).click();
  await expect(passwordInput).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Ingresar" }).click();

  await expect(
    page.getByRole("heading", { name: "¿Qué quieres descubrir hoy?" }),
  ).toBeVisible();
  await expect(page.getByLabel("Organización")).toHaveValue(
    "e8209087-e14a-45d9-a35f-a91d531df933",
  );

  await page.getByRole("button", { name: /Política de vacaciones/ }).click();
  await expect(page.getByText("Tienes quince días hábiles [1].")).toBeVisible();
  await expect(page.getByText("[1] Manual laboral")).toBeVisible();

  await page.getByRole("link", { name: "Documentos" }).click();
  await expect(page.getByRole("heading", { name: "Documentos" })).toBeVisible();
  await expect(page.getByText("Tu biblioteca está vacía")).toBeVisible();
  const upload = page.getByRole("button", { name: "Subir documento" });
  await upload.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Cerrar", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(upload).toBeFocused();
});
