import { z } from "zod";

export const tokenSchema = z.object({
  accessToken: z.string().min(1),
  refreshToken: z.string().min(1),
  tokenType: z.string().optional(),
});

export const identitySchema = z.object({
  userId: z.uuid(),
  email: z.email(),
  displayName: z.string().min(1),
  memberships: z.array(
    z.object({
      organizationId: z.uuid(),
      organizationName: z.string().min(1),
      organizationSlug: z.string().min(1),
      role: z.enum(["owner", "editor", "viewer"]),
    }),
  ),
});
