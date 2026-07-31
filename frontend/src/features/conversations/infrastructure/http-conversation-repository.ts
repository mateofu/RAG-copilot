import { apiRequest } from "../../../core/http/http-client";
import type { ConversationRepository } from "../application/conversation-repository";
import type {
  Answer,
  ConversationDetail,
  ConversationSummary,
} from "../domain/conversation";

export class HttpConversationRepository implements ConversationRepository {
  async list(organizationId: string): Promise<ConversationSummary[]> {
    const response = await apiRequest<{ items: ConversationSummary[] }>(
      "/conversations?limit=100&offset=0",
      { organizationId },
    );
    return response.items;
  }

  get(
    organizationId: string,
    conversationId: string,
  ): Promise<ConversationDetail> {
    return apiRequest(`/conversations/${conversationId}`, { organizationId });
  }

  ask(
    organizationId: string,
    question: string,
    conversationId?: string,
  ): Promise<Answer> {
    const path = conversationId
      ? `/conversations/${conversationId}/messages`
      : "/conversations";
    return apiRequest(path, {
      method: "POST",
      organizationId,
      body: JSON.stringify({ question }),
    });
  }
}
