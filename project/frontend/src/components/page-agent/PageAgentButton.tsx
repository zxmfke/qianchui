import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, X, Send, Loader2, Minimize2, Maximize2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentMessage {
  role: 'user' | 'agent';
  content: string;
  timestamp: number;
}

export default function PageAgentButton() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [agentReady, setAgentReady] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const agentRef = useRef<any>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!open) return;

    async function initAgent() {
      try {
        const token = localStorage.getItem('token') || '';
        let modelId = '';
        try {
          const resp = await fetch('/api/proxy/llm/models', {
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await resp.json();
          modelId = data?.data?.[0]?.id || '';
        } catch {
          // fall through to default
        }

        const { PageAgent } = await import('page-agent');
        agentRef.current = new PageAgent({
          model: modelId || 'gpt-4',
          baseURL: '/api/proxy/llm',
          apiKey: token,
          language: 'zh-CN',
          ui: false,
        });
        setAgentReady(true);
      } catch {
        setAgentReady(false);
      }
    }

    initAgent();
  }, [open]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMsg: AgentMessage = { role: 'user', content: input.trim(), timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      if (agentRef.current) {
        await agentRef.current.execute(userMsg.content);
        setMessages((prev) => [
          ...prev,
          { role: 'agent', content: t('pageAgent.actionComplete'), timestamp: Date.now() },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'agent', content: t('pageAgent.notReady'), timestamp: Date.now() },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'agent', content: `${t('pageAgent.error')}: ${err.message || err}`, timestamp: Date.now() },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, t]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-[900] w-12 h-12 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/30 flex items-center justify-center text-white hover:scale-110 transition-transform group"
        title={t('pageAgent.title')}
      >
        <Bot className="w-5 h-5" />
        <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 border-2 border-slate-950 animate-pulse" />
      </button>
    );
  }

  if (minimized) {
    return (
      <div className="fixed bottom-6 right-6 z-[900] flex items-center gap-2">
        <button
          onClick={() => setMinimized(false)}
          className="flex items-center gap-2 px-3 py-2 rounded-full bg-slate-800 border border-slate-600 text-slate-200 text-xs shadow-xl hover:bg-slate-700 transition-colors"
        >
          <Bot className="w-4 h-4 text-indigo-400" />
          {t('pageAgent.title')}
          <Maximize2 className="w-3 h-3 text-slate-400" />
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-[900] w-80 h-[420px] flex flex-col bg-slate-800 border border-slate-600 rounded-2xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gradient-to-r from-indigo-600/40 to-purple-600/40 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-200">{t('pageAgent.title')}</span>
          <span className={cn('w-2 h-2 rounded-full', agentReady ? 'bg-emerald-400' : 'bg-amber-400')} />
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMinimized(true)}
            className="p-1 rounded hover:bg-slate-700/50 text-slate-400 hover:text-slate-200"
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-slate-700/50 text-slate-400 hover:text-slate-200"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {messages.length === 0 && (
          <div className="text-center py-6">
            <Bot className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-500">{t('pageAgent.placeholder')}</p>
            <div className="mt-3 space-y-1.5">
              {[
                t('pageAgent.example1'),
                t('pageAgent.example2'),
                t('pageAgent.example3'),
              ].map((ex, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(ex); }}
                  className="block w-full text-left text-xs px-3 py-1.5 rounded-lg bg-slate-700/50 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'flex',
              msg.role === 'user' ? 'justify-end' : 'justify-start',
            )}
          >
            <div
              className={cn(
                'max-w-[85%] px-3 py-1.5 rounded-xl text-xs',
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-slate-700 text-slate-200 rounded-bl-sm',
              )}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 text-slate-300 px-3 py-1.5 rounded-xl rounded-bl-sm">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 p-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('pageAgent.inputPlaceholder')}
            className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
