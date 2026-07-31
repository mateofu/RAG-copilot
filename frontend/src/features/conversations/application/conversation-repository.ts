import type {
  Answer,
  ConversationDetail,
  ConversationSummary,
} from "../domain/conversation";

export interface ConversationRepository {
  list(organizationId: string): Promise<ConversationSummary[]>;
  get(
    organizationId: string,
    conversationId: string,
  ): Promise<ConversationDetail>;
  ask(
    organizationId: string,
    question: string,
    conversationId?: string,
  ): Promise<Answer>;
}
