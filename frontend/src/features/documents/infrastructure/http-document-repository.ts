import { apiRequest } from "../../../core/http/http-client";
import type { DocumentRepository } from "../application/document-repository";
import type {
  DocumentItem,
  DocumentPage,
  RetrievedChunk,
} from "../domain/document";
import {
  documentPageSchema,
  searchSchema,
  uploadedDocumentSchema,
} from "./document-schemas";

export class HttpDocumentRepository implements DocumentRepository {
  list(organizationId: string): Promise<DocumentPage> {
    return apiRequest(
      "/documents?limit=100&offset=0",
      { organizationId },
      documentPageSchema,
    );
  }

  upload(
    organizationId: string,
    title: string,
    file: File,
  ): Promise<Omit<DocumentItem, "createdAt">> {
    const body = new FormData();
    body.set("title", title);
    body.set("file", file);
    return apiRequest(
      "/documents",
      { method: "POST", body, organizationId },
      uploadedDocumentSchema,
    );
  }

  async search(
    organizationId: string,
    query: string,
  ): Promise<RetrievedChunk[]> {
    const response = await apiRequest<{ items: RetrievedChunk[] }>(
      `/documents/search/chunks?query=${encodeURIComponent(query)}&limit=8`,
      { organizationId },
      searchSchema,
    );
    return response.items;
  }
}
