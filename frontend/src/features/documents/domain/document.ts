export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export type DocumentItem = {
  documentId: string;
  documentNumber: number;
  title: string;
  versionId: string;
  versionNumber: number;
  originalFilename: string;
  sizeBytes: number;
  status: DocumentStatus;
  createdAt: string;
};

export type DocumentPage = {
  items: DocumentItem[];
  total: number;
  limit: number;
  offset: number;
};
export type RetrievedChunk = {
  chunkId: string;
  documentId: string;
  documentNumber: number;
  documentTitle: string;
  versionId: string;
  chunkIndex: number;
  pageNumber: number;
  content: string;
  score: number;
};
