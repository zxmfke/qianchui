import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  isStreaming?: boolean;
}

const QUICK_COMMANDS = [
  { cmd: '/推荐', descKey: 'chat.cmdRecommendDesc' },
  { cmd: '/诊断', descKey: 'chat.cmdDiagnoseDesc' },
  { cmd: '/刷题', descKey: 'chat.cmdQuizDesc' },
  { cmd: '/演练', descKey: 'chat.cmdDrillDesc' },
  { cmd: '/看板', descKey: 'chat.cmdDashboardDesc' },
  { cmd: '/周报', descKey: 'chat.cmdReportDesc' },
];

export default function ChatInput({ onSend, disabled, isStreaming }: ChatInputProps) {
  const { t } = useTranslation();
  const [content, setContent] = useState('');
  const [showCommands, setShowCommands] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [content]);

  const handleSend = () => {
    const trimmed = content.trim();
    if (!trimmed || disabled || isStreaming) return;
    onSend(trimmed);
    setContent('');
    setShowCommands(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setContent(val);
    setShowCommands(val === '/');
  };

  const handleCommand = (cmd: string) => {
    setContent(cmd + ' ');
    setShowCommands(false);
    textareaRef.current?.focus();
  };

  return (
    <div className="relative">
      {/* Quick commands dropdown */}
      {showCommands && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-slate-800 border border-slate-700 rounded-lg p-2 shadow-xl animate-fade-in">
          <p className="text-xs text-slate-500 px-2 pb-2">{t('chat.quickCommands')}</p>
          <div className="grid grid-cols-3 gap-1">
            {QUICK_COMMANDS.map((item) => (
              <button
                key={item.cmd}
                onClick={() => handleCommand(item.cmd)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition-colors text-left"
              >
                <span className="text-indigo-400 font-mono text-xs">{item.cmd}</span>
                <span className="text-slate-500 text-xs">{t(item.descKey)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quick command bar */}
      <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
        {QUICK_COMMANDS.map((item) => (
          <button
            key={item.cmd}
            onClick={() => handleCommand(item.cmd)}
            className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium
                       bg-slate-800 text-slate-400 border border-slate-700
                       hover:border-indigo-500/50 hover:text-indigo-400 transition-all"
          >
            {item.cmd}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="flex items-end gap-2 bg-slate-800 border border-slate-700 rounded-lg p-2 focus-within:border-indigo-500/50 transition-colors">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.inputPlaceholder')}
          rows={1}
          className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 resize-none focus:outline-none text-sm leading-relaxed"
          disabled={disabled || isStreaming}
        />
        <button
          onClick={handleSend}
          disabled={!content.trim() || disabled || isStreaming}
          className={cn(
            'p-2 rounded-lg transition-all flex-shrink-0',
            content.trim() && !disabled && !isStreaming
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
              : 'bg-slate-700 text-slate-500 cursor-not-allowed',
          )}
        >
          {isStreaming ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}
