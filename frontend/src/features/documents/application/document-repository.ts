import type {
  DocumentItem,
  DocumentPage,
  RetrievedChunk,
} from "../domain/document";

export interface DocumentRepository {
  list(organizationId: string): Promise<DocumentPage>;
  upload(
    organizationId: string,
    title: string,
    file: File,
  ): Promise<DocumentItem>;
  search(organizationId: string, query: string): Promise<RetrievedChunk[]>;
}
