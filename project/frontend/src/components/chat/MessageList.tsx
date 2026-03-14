import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, User } from 'lucide-react';
import type { ConversationMessage, Card } from '@/types';
import { cn } from '@/lib/utils';
import ScriptCardInline from './cards/ScriptCardInline';
import DiagnosisCardInline from './cards/DiagnosisCardInline';
import TrainingCardInline from './cards/TrainingCardInline';
import DataCardInline from './cards/DataCardInline';
import OptimizeCardInline from './cards/OptimizeCardInline';
import AnnotationCardInline from './cards/AnnotationCardInline';
import ABTestCardInline from './cards/ABTestCardInline';
import DiagnosisRadarInline from './cards/DiagnosisRadarInline';

interface MessageListProps {
  messages: ConversationMessage[];
  streamingContent?: string;
  isStreaming?: boolean;
}

function renderCard(card: Card, index: number) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const d = card.data as any;
  switch (card.type) {
    case 'script':
      return <ScriptCardInline key={index} data={d} title={card.title} />;
    case 'diagnosis':
      return <DiagnosisCardInline key={index} data={d} title={card.title} />;
    case 'training':
      return <TrainingCardInline key={index} data={d} title={card.title} />;
    case 'data':
      return <DataCardInline key={index} data={d} title={card.title} />;
    case 'optimize-strategy':
      return <OptimizeCardInline key={index} data={d} />;
    case 'annotation-card':
      return <AnnotationCardInline key={index} data={d} />;
    case 'ab-test-card':
      return <ABTestCardInline key={index} data={d} />;
    case 'diagnosis-radar':
      return <DiagnosisRadarInline key={index} data={d} />;
    default:
      return null;
  }
}

export default function MessageList({ messages, streamingContent, isStreaming }: MessageListProps) {
  const { t } = useTranslation();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-14 h-14 mx-auto mb-3 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Bot className="w-7 h-7 text-indigo-400" />
          </div>
          <h3 className="text-base font-semibold text-slate-200 mb-2">
            {t('chat.welcomeTitle', { brand: t('brand.name'), subtitle: t('brand.subtitle') })}
          </h3>
          <p className="text-xs text-slate-500 mb-4 whitespace-pre-wrap">
            {t('chat.welcomeMessage', { cmd: t('chat.cmdRecommend') })}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={cn(
            'flex gap-2 animate-fade-in',
            msg.role === 'user' ? 'justify-end' : 'justify-start',
          )}
        >
          {msg.role === 'assistant' && (
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1">
              <Bot className="w-4 h-4 text-white" />
            </div>
          )}
          <div
            className={cn(
              'max-w-[70%] rounded-lg px-3 py-2',
              msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-slate-800 text-slate-200 rounded-bl-sm border border-slate-700/50',
            )}
          >
            <p className="text-xs whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            {msg.cards && msg.cards.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {msg.cards.map((card, i) => renderCard(card, i))}
              </div>
            )}
            {msg.suggested_actions && msg.suggested_actions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {msg.suggested_actions.map((action, i) => (
                  <button
                    key={i}
                    className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          {msg.role === 'user' && (
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0 mt-1">
              <User className="w-4 h-4 text-white" />
            </div>
          )}
        </div>
      ))}

      {/* Streaming message */}
      {isStreaming && streamingContent && (
        <div className="flex gap-3 animate-fade-in">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div className="max-w-[70%] rounded-lg rounded-bl-sm px-3 py-2 bg-slate-800 text-slate-200 border border-slate-700/50">
            <p className="text-xs whitespace-pre-wrap leading-relaxed">
              {streamingContent}
              <span className="inline-block w-2 h-4 bg-indigo-400 animate-pulse ml-0.5" />
            </p>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
