import { z } from "zod";

export const documentSchema = z.object({
  documentId: z.uuid(),
  documentNumber: z.number().int().positive(),
  title: z.string().min(1),
  versionId: z.uuid(),
  versionNumber: z.number().int().positive(),
  originalFilename: z.string().min(1),
  sizeBytes: z.number().int().positive(),
  status: z.enum(["pending", "processing", "ready", "failed"]),
  createdAt: z.iso.datetime({ offset: true }),
});

export const documentPageSchema = z.object({
  items: z.array(documentSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

export const uploadedDocumentSchema = documentSchema.omit({ createdAt: true });

export const chunkSchema = z.object({
  chunkId: z.uuid(),
  documentId: z.uuid(),
  documentNumber: z.number().int().positive(),
  documentTitle: z.string().min(1),
  versionId: z.uuid(),
  chunkIndex: z.number().int().nonnegative(),
  pageNumber: z.number().int().positive(),
  content: z.string().min(1),
  score: z.number(),
});

export const searchSchema = z.object({ items: z.array(chunkSchema) });
