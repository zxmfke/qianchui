import { useState, useCallback, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MessageSquareText,
  Send,
  Loader2,
  Bot,
  User,
  Sparkles,
  Building2,
  Users,
  BookOpen,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { adminService, type DataQueryResponse } from '@/services/admin';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  data?: Record<string, unknown> | null;
  timestamp: number;
}

const QUICK_QUESTIONS = [
  'admin.query.quick.overview',
  'admin.query.quick.yesterdayEnterprises',
  'admin.query.quick.totalUsers',
  'admin.query.quick.todayScripts',
  'admin.query.quick.yesterdayConversations',
];

function DataCard({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  const iconMap: Record<string, React.ElementType> = {
    enterprise: Building2,
    user: Users,
    script: BookOpen,
    conversation: MessageSquare,
  };

  return (
    <div className="mt-2 grid grid-cols-2 gap-2">
      {entries.map(([key, value]) => {
        const matchedIcon = Object.entries(iconMap).find(([k]) => key.toLowerCase().includes(k));
        const Icon = matchedIcon ? matchedIcon[1] : Sparkles;
        return (
          <div key={key} className="bg-slate-700/40 rounded-lg p-2.5 flex items-center gap-2">
            <Icon className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <div>
              <p className="text-[10px] text-slate-400 leading-tight">
                {key.replace(/_/g, ' ')}
              </p>
              <p className="text-sm font-semibold text-slate-100 tabular-nums">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AdminQueryPage() {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendQuestion = useCallback(async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: ChatMessage = {
      role: 'user', content: question.trim(), timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res: DataQueryResponse = await adminService.queryData(question);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          data: res.data,
          timestamp: Date.now(),
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: t('admin.query.error') + ': ' + (err.message || err),
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [loading, t]);

  const handleSend = () => sendQuestion(input);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 sm:px-6 py-4 border-b border-slate-800 pt-14 lg:pt-4">
        <div className="flex items-center gap-2">
          <MessageSquareText className="w-5 h-5 text-amber-400" />
          <h1 className="text-lg font-bold text-slate-100">{t('admin.query.title')}</h1>
        </div>
        <p className="text-sm text-slate-400 mt-1">{t('admin.query.subtitle')}</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-amber-400" />
            </div>
            <h2 className="text-lg font-semibold text-slate-200 mb-2">{t('admin.query.welcomeTitle')}</h2>
            <p className="text-sm text-slate-400 mb-6 text-center max-w-md">{t('admin.query.welcomeDesc')}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {QUICK_QUESTIONS.map((qKey) => (
                <button
                  key={qKey}
                  onClick={() => sendQuestion(t(qKey))}
                  className="text-left text-xs px-4 py-2.5 rounded-xl bg-slate-800/60 border border-slate-700/50 text-slate-300 hover:text-slate-100 hover:border-amber-500/30 hover:bg-slate-800 transition-colors"
                >
                  {t(qKey)}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'flex gap-3 max-w-3xl',
              msg.role === 'user' ? 'ml-auto flex-row-reverse' : '',
            )}
          >
            <div className={cn(
              'w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0',
              msg.role === 'user'
                ? 'bg-gradient-to-br from-blue-500 to-indigo-600'
                : 'bg-gradient-to-br from-amber-500 to-orange-600',
            )}>
              {msg.role === 'user'
                ? <User className="w-4 h-4 text-white" />
                : <Bot className="w-4 h-4 text-white" />}
            </div>
            <div className={cn(
              'rounded-2xl px-4 py-3 max-w-[80%]',
              msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-md'
                : 'bg-slate-800/80 border border-slate-700/50 text-slate-200 rounded-bl-md',
            )}>
              <p className="text-sm whitespace-pre-line leading-relaxed">{msg.content}</p>
              {msg.data && <DataCard data={msg.data} />}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 max-w-3xl">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-2xl rounded-bl-md px-4 py-3">
              <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 sm:px-6 py-4 border-t border-slate-800">
        <div className="flex items-center gap-3 max-w-3xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('admin.query.inputPlaceholder')}
            className="flex-1 bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
