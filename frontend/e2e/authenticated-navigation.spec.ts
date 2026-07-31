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
    await route.fulfill({
      json: { items: [], total: 0, limit: 100, offset: 0 },
    });
  });
  await page.route("**/api/v1/documents**", async (route) => {
    await route.fulfill({
      json: { items: [], total: 0, limit: 100, offset: 0 },
    });
  });

  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill("owner@example.com");
  await page.getByLabel("Contraseña").fill("a-secure-password");
  await page.getByRole("button", { name: "Ingresar" }).click();

  await expect(
    page.getByRole("heading", { name: "¿Qué quieres descubrir hoy?" }),
  ).toBeVisible();
  await expect(page.getByLabel("Organización")).toHaveValue(
    "e8209087-e14a-45d9-a35f-a91d531df933",
  );

  await page.getByRole("link", { name: "Documentos" }).click();
  await expect(page.getByRole("heading", { name: "Documentos" })).toBeVisible();
  await expect(page.getByText("Tu biblioteca está vacía")).toBeVisible();
});
