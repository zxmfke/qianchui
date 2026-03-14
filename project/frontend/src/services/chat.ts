import api from './api';
import type { Conversation, ConversationMessage, AIResponse } from '@/types';

export const chatService = {
  async getConversations(): Promise<Conversation[]> {
    const res = await api.get<Conversation[]>('/conversations');
    return res.data;
  },

  async createConversation(title?: string): Promise<Conversation> {
    const res = await api.post<Conversation>('/conversations', { title });
    return res.data;
  },

  async getMessages(conversationId: string): Promise<ConversationMessage[]> {
    const res = await api.get<ConversationMessage[]>(
      `/conversations/${conversationId}/messages`,
    );
    return res.data;
  },

  async sendMessage(
    conversationId: string,
    content: string,
  ): Promise<AIResponse> {
    const res = await api.post<AIResponse>(
      `/conversations/${conversationId}/messages`,
      { content },
    );
    return res.data;
  },

  streamMessage(
    conversationId: string,
    content: string,
    onChunk: (chunk: string) => void,
    onCard?: (card: AIResponse) => void,
    onDone?: () => void,
    onError?: (error: Error) => void,
  ): AbortController {
    const controller = new AbortController();
    const token = localStorage.getItem('token');

    fetch(`/api/conversations/${conversationId}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No reader available');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              try {
                const parsed = JSON.parse(data);
                if (parsed.type === 'chunk') {
                  onChunk(parsed.content);
                } else if (parsed.type === 'card') {
                  onCard?.(parsed);
                } else if (parsed.type === 'end') {
                  onDone?.();
                  return;
                }
              } catch {
                onChunk(data);
              }
            }
          }
        }
        onDone?.();
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          onError?.(error);
        }
      });

    return controller;
  },
};
