import { apiRequest } from "../../../core/http/http-client";
import type { DocumentRepository } from "../application/document-repository";
import type {
  DocumentItem,
  DocumentPage,
  RetrievedChunk,
} from "../domain/document";

export class HttpDocumentRepository implements DocumentRepository {
  list(organizationId: string): Promise<DocumentPage> {
    return apiRequest("/documents?limit=100&offset=0", { organizationId });
  }

  upload(
    organizationId: string,
    title: string,
    file: File,
  ): Promise<DocumentItem> {
    const body = new FormData();
    body.set("title", title);
    body.set("file", file);
    return apiRequest("/documents", { method: "POST", body, organizationId });
  }

  async search(
    organizationId: string,
    query: string,
  ): Promise<RetrievedChunk[]> {
    const response = await apiRequest<{ items: RetrievedChunk[] }>(
      `/documents/search/chunks?query=${encodeURIComponent(query)}&limit=8`,
      { organizationId },
    );
    return response.items;
  }
}
