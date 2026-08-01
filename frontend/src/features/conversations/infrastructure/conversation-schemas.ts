import { z } from "zod";

export const citationSchema = z.object({
  index: z.number().int().positive(),
  chunkId: z.uuid().nullable(),
  documentId: z.uuid(),
  documentNumber: z.number().int().positive(),
  documentTitle: z.string().min(1),
  versionId: z.uuid(),
  pageNumber: z.number().int().positive(),
  content: z.string().min(1),
  score: z.number(),
});

const messageSchema = z.object({
  messageId: z.uuid(),
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1),
  inputTokens: z.number().int().nonnegative(),
  outputTokens: z.number().int().nonnegative(),
  createdAt: z.iso.datetime({ offset: true }),
  citations: z.array(citationSchema),
});

const summarySchema = z.object({
  conversationId: z.uuid(),
  title: z.string().min(1),
  messageCount: z.number().int().nonnegative(),
  createdAt: z.iso.datetime({ offset: true }),
  updatedAt: z.iso.datetime({ offset: true }),
});

export const conversationPageSchema = z.object({
  items: z.array(summarySchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

export const conversationDetailSchema = z.object({
  conversationId: z.uuid(),
  title: z.string().min(1),
  createdAt: z.iso.datetime({ offset: true }),
  updatedAt: z.iso.datetime({ offset: true }),
  messages: z.array(messageSchema),
});

export const answerSchema = z.object({
  conversationId: z.uuid(),
  messageId: z.uuid(),
  answer: z.string().min(1),
  citations: z.array(citationSchema),
  inputTokens: z.number().int().nonnegative(),
  outputTokens: z.number().int().nonnegative(),
});
