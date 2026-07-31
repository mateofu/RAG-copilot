export type Citation = {
  index: number;
  chunkId: string | null;
  documentId: string;
  documentNumber: number;
  documentTitle: string;
  versionId: string;
  pageNumber: number;
  content: string;
  score: number;
};
export type Message = {
  messageId: string;
  role: "user" | "assistant";
  content: string;
  inputTokens: number;
  outputTokens: number;
  createdAt: string;
  citations: Citation[];
};
export type ConversationSummary = {
  conversationId: string;
  title: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
};
export type ConversationDetail = {
  conversationId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
};
export type Answer = {
  conversationId: string;
  messageId: string;
  answer: string;
  citations: Citation[];
  inputTokens: number;
  outputTokens: number;
};
