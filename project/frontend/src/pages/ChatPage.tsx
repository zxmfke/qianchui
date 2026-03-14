import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageSquare, Plus, Search } from 'lucide-react';
import { useChatStore } from '@/stores/chatStore';
import { cn, truncate, formatDate } from '@/lib/utils';
import ChatInput from '@/components/chat/ChatInput';
import MessageList from '@/components/chat/MessageList';

export default function ChatPage() {
  const { t } = useTranslation();
  const {
    conversations,
    currentConversation,
    messages,
    isStreaming,
    streamingContent,
    loadConversations,
    selectConversation,
    createConversation,
    sendMessage,
  } = useChatStore();

  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const handleNewConversation = async () => {
    await createConversation();
  };

  const handleSend = (content: string) => {
    if (!currentConversation) {
      createConversation().then(() => {
        sendMessage(content);
      });
    } else {
      sendMessage(content);
    }
  };

  return (
    <div className="h-full flex">
      {/* Conversation list sidebar */}
      <div className="w-60 border-r border-slate-800 flex flex-col bg-slate-900/50">
        <div className="p-3 border-b border-slate-800">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-slate-200">{t('chat.conversationList')}</h2>
            <button
              onClick={handleNewConversation}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t('chat.searchPlaceholder')}
              className="input-field pl-9 text-sm py-2"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredConversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => selectConversation(conv)}
              className={cn(
                'w-full text-left px-3 py-2.5 rounded-lg transition-all',
                currentConversation?.id === conv.id
                  ? 'bg-indigo-600/20 border border-indigo-500/30'
                  : 'hover:bg-slate-800',
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <MessageSquare className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                <span className="text-sm text-slate-200 truncate">{conv.title}</span>
              </div>
              {conv.last_message && (
                <p className="text-xs text-slate-500 truncate pl-5.5">
                  {truncate(conv.last_message, 30)}
                </p>
              )}
              <p className="text-[10px] text-slate-600 pl-5.5 mt-0.5">
                {formatDate(conv.updated_at)}
              </p>
            </button>
          ))}

          {filteredConversations.length === 0 && (
            <div className="text-center py-8">
              <MessageSquare className="w-8 h-8 text-slate-700 mx-auto mb-2" />
              <p className="text-xs text-slate-600">{t('chat.noConversations')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-12 border-b border-slate-800 flex items-center px-4">
          <h2 className="text-sm font-semibold text-slate-200">
            {currentConversation ? currentConversation.title : t('chat.title')}
          </h2>
          <span className="ml-2 text-xs text-slate-600">
            {currentConversation ? t('chat.messageCount', { count: messages.length }) : t('chat.startNew')}
          </span>
        </div>

        {/* Messages */}
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />

        {/* Input */}
        <div className="border-t border-slate-800 p-3" data-tour="page-chat-input">
          <ChatInput onSend={handleSend} isStreaming={isStreaming} />
        </div>
      </div>
    </div>
  );
}
