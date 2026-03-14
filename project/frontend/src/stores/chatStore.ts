import { create } from 'zustand';
import type { Conversation, ConversationMessage, Card, SuggestedAction } from '@/types';
import { chatService } from '@/services/chat';

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: ConversationMessage[];
  isStreaming: boolean;
  streamingContent: string;
  isLoading: boolean;

  loadConversations: () => Promise<void>;
  selectConversation: (conv: Conversation) => Promise<void>;
  createConversation: (title?: string) => Promise<Conversation>;
  loadMessages: (conversationId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  addLocalMessage: (msg: ConversationMessage) => void;
  clearStreaming: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  isLoading: false,

  loadConversations: async () => {
    try {
      const conversations = await chatService.getConversations();
      set({ conversations });
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  },

  selectConversation: async (conv) => {
    set({ currentConversation: conv, messages: [], isLoading: true });
    await get().loadMessages(conv.id);
    set({ isLoading: false });
  },

  createConversation: async (title) => {
    const conv = await chatService.createConversation(title || '新对话');
    set((state) => ({
      conversations: [conv, ...state.conversations],
      currentConversation: conv,
      messages: [],
    }));
    return conv;
  },

  loadMessages: async (conversationId) => {
    try {
      const messages = await chatService.getMessages(conversationId);
      set({ messages });
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  },

  sendMessage: async (content) => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    const userMsg: ConversationMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: currentConversation.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    get().addLocalMessage(userMsg);

    set({ isStreaming: true, streamingContent: '' });

    let fullContent = '';
    const cards: Card[] = [];
    const suggestedActions: SuggestedAction[] = [];

    chatService.streamMessage(
      currentConversation.id,
      content,
      (chunk) => {
        fullContent += chunk;
        set({ streamingContent: fullContent });
      },
      (cardData) => {
        if (cardData.cards) cards.push(...cardData.cards);
        if (cardData.suggested_actions) suggestedActions.push(...cardData.suggested_actions);
      },
      () => {
        const aiMsg: ConversationMessage = {
          id: `ai-${Date.now()}`,
          conversation_id: currentConversation.id,
          role: 'assistant',
          content: fullContent,
          cards: cards.length > 0 ? cards : undefined,
          suggested_actions: suggestedActions.length > 0 ? suggestedActions : undefined,
          created_at: new Date().toISOString(),
        };
        set((state) => ({
          messages: [...state.messages, aiMsg],
          isStreaming: false,
          streamingContent: '',
        }));
      },
      (error) => {
        console.error('Stream error:', error);
        set({ isStreaming: false, streamingContent: '' });
      },
    );
  },

  addLocalMessage: (msg) => {
    set((state) => ({ messages: [...state.messages, msg] }));
  },

  clearStreaming: () => {
    set({ isStreaming: false, streamingContent: '' });
  },
}));
