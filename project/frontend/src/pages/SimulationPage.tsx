import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Theater,
  Send,
  Loader2,
  Star,
  Lightbulb,
  RotateCcw,
  Play,
  Bot,
  User,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { simulationService } from '@/services/simulation';
import type { SimulationMessage } from '@/types';

const SCENARIOS = [
  { id: '1', name: '价格异议处理', nameKey: 'simulation.scenarios.priceObjection', descKey: 'simulation.scenarios.priceObjectionDesc', difficulty: 'easy' as const, icon: '💰' },
  { id: '2', name: '竞品对比', nameKey: 'simulation.scenarios.competitorCompare', descKey: 'simulation.scenarios.competitorCompareDesc', difficulty: 'medium' as const, icon: '⚔️' },
  { id: '3', name: '犹豫不决', nameKey: 'simulation.scenarios.hesitation', descKey: 'simulation.scenarios.hesitationDesc', difficulty: 'medium' as const, icon: '🤔' },
  { id: '4', name: '售后投诉', nameKey: 'simulation.scenarios.complaint', descKey: 'simulation.scenarios.complaintDesc', difficulty: 'hard' as const, icon: '😤' },
  { id: '5', name: '需求模糊', nameKey: 'simulation.scenarios.vagueNeeds', descKey: 'simulation.scenarios.vagueNeedsDesc', difficulty: 'easy' as const, icon: '❓' },
  { id: '6', name: '强势砍价', nameKey: 'simulation.scenarios.hardBargain', descKey: 'simulation.scenarios.hardBargainDesc', difficulty: 'hard' as const, icon: '🔥' },
];

const DIFFICULTY_MAP = { easy: 1, medium: 2, hard: 3 };

function toSimulationMessage(
  role: 'customer' | 'agent' | 'coach',
  content: string,
  id: string,
  score?: number,
): SimulationMessage {
  return {
    id,
    role,
    content,
    score,
    created_at: new Date().toISOString(),
  };
}

export default function SimulationPage() {
  const { t } = useTranslation();
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SimulationMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [score, setScore] = useState<{
    overall: number;
    dimensions: { label: string; score: number }[];
  } | null>(null);
  const [hints, setHints] = useState<string[]>([
    t('simulation.hints.hint1'),
    t('simulation.hints.hint2'),
    t('simulation.hints.hint3'),
  ]);
  const [error, setError] = useState<string | null>(null);
  const [startLoading, setStartLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleStart = async () => {
    if (!selectedScenario) return;
    const scenario = SCENARIOS.find((s) => s.id === selectedScenario);
    if (!scenario) return;

    setStartLoading(true);
    setError(null);
    try {
      const res = await simulationService.createSession({
        scenario: scenario.name,
        difficulty: DIFFICULTY_MAP[scenario.difficulty],
      });
      const id = res?.id ?? (res as Record<string, unknown>)?.id;
      const sid = typeof id === 'string' ? id : id != null ? String(id) : null;
      if (!sid) {
        throw new Error(t('simulation.createSessionNoId'));
      }
      setSessionId(sid);

      const rawMessages = res?.messages ?? (res as Record<string, unknown>)?.messages ?? [];
      const list = Array.isArray(rawMessages) ? rawMessages : [];
      const initial: SimulationMessage[] = list.map((m: { role?: string; content?: string }, i: number) =>
        toSimulationMessage(
          (m.role === 'customer' ? 'customer' : 'agent') as 'customer' | 'agent',
          m.content ?? '',
          `init-${i}-${Date.now()}`,
        ),
      );
      if (initial.length === 0 && list.length === 0) {
        const opening = (res as Record<string, unknown>)?.opening ?? (res as Record<string, unknown>)?.customer_opening;
        if (typeof opening === 'string' && opening) {
          initial.push(toSimulationMessage('customer', opening, `init-0-${Date.now()}`));
        }
      }
      setMessages(initial.length > 0 ? initial : []);
      setIsActive(true);
      setScore(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('simulation.createSessionFailed'));
    } finally {
      setStartLoading(false);
    }
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isTyping || !sessionId) return;

    const agentMsg = toSimulationMessage('agent', trimmed, `agent-${Date.now()}`);
    setMessages((prev) => [...prev, agentMsg]);
    setInput('');
    setIsTyping(true);
    setError(null);

    try {
      const res = await simulationService.sendMessage(sessionId, trimmed);
      const aiResponse = res?.ai_response ?? (res as Record<string, unknown>)?.ai_response ?? '';
      const hintData = res?.hint ?? (res as Record<string, unknown>)?.hint;

      const newMessages: SimulationMessage[] = [];
      if (typeof aiResponse === 'string' && aiResponse) {
        newMessages.push(toSimulationMessage('customer', aiResponse, `customer-${Date.now()}`));
      }
      if (hintData && typeof hintData === 'object') {
        const h = hintData as { customer_psychology?: string; suggested_strategy?: string };
        const parts = [h.customer_psychology, h.suggested_strategy].filter(Boolean);
        if (parts.length > 0) {
          newMessages.push(
            toSimulationMessage('coach', parts.join('\n'), `coach-${Date.now()}`, (res as Record<string, unknown>)?.score as number | undefined),
          );
        }
      } else if (Array.isArray((res as Record<string, unknown>)?.messages)) {
        const msgs = (res as Record<string, unknown>).messages as Array<{ role?: string; content?: string; score?: number }>;
        for (const m of msgs) {
          const role = m.role === 'customer' ? 'customer' : m.role === 'coach' ? 'coach' : 'agent';
          newMessages.push(
            toSimulationMessage(role as 'customer' | 'agent' | 'coach', m.content ?? '', `msg-${Date.now()}-${Math.random()}`, m.score),
          );
        }
      }

      setMessages((prev) => [...prev, ...newMessages]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('simulation.sendFailed'));
    } finally {
      setIsTyping(false);
    }
  };

  const handleEnd = async () => {
    if (!sessionId) {
      setIsActive(false);
      return;
    }

    setIsTyping(true);
    setError(null);
    try {
      const res = await simulationService.completeSession(sessionId);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const r = res as any;
      const overall = r?.overall_score ?? r?.score?.overall ?? 0;
      const dims = r?.dimensions ?? r?.score?.dimensions ?? [];
      const dimList = Array.isArray(dims)
        ? dims.map((d: { dimension?: string; name?: string; score?: number }) => ({
            label: d.dimension ?? d.name ?? '',
            score: typeof d.score === 'number' ? d.score : 0,
          }))
        : [];

      setScore({
        overall: typeof overall === 'number' ? overall : 0,
        dimensions: dimList.length > 0 ? dimList : [
          { label: t('simulation.defaultDimensions.scriptUsage'), score: 85 },
          { label: t('simulation.defaultDimensions.communicationSkills'), score: 80 },
          { label: t('simulation.defaultDimensions.emotionManagement'), score: 78 },
        ],
      });
      setIsActive(false);
      setSessionId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('simulation.endFailed'));
      setIsActive(false);
      setSessionId(null);
    } finally {
      setIsTyping(false);
    }
  };

  const handleReset = () => {
    setIsActive(false);
    setSessionId(null);
    setMessages([]);
    setScore(null);
    setSelectedScenario(null);
    setError(null);
  };

  return (
    <div className="h-full flex">
      {/* Left: Scenario selection / Chat */}
      <div className="flex-1 flex flex-col">
        <div className="h-12 border-b border-slate-800 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Theater className="w-4 h-4 text-indigo-400" />
            <h1 className="text-sm font-semibold text-slate-200">{t('simulation.title')}</h1>
          </div>
          {isActive && (
            <div className="flex items-center gap-2">
              <button onClick={handleEnd} disabled={isTyping} className="btn-primary text-sm py-1.5">
                {t('simulation.endDrill')}
              </button>
              <button onClick={handleReset} className="btn-secondary text-sm py-1.5 flex items-center gap-1">
                <RotateCcw className="w-3.5 h-3.5" /> {t('common.reset')}
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="flex items-center gap-2 px-4 py-1.5 bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {!isActive ? (
          <div className="flex-1 p-4">
            <h2 className="text-base font-semibold text-slate-200 mb-2">{t('simulation.selectScenario')}</h2>
            <p className="text-xs text-slate-500 mb-4">{t('simulation.scenarioDesc')}</p>

            <div className="grid grid-cols-3 gap-4">
              {SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedScenario(s.id)}
                  className={cn(
                    'glass-card p-4 text-left transition-all hover:border-indigo-500/50',
                    selectedScenario === s.id && 'border-indigo-500/50 bg-indigo-500/5',
                  )}
                >
                  <span className="text-2xl">{s.icon}</span>
                  <h3 className="text-sm font-semibold text-slate-200 mt-2">{t(s.nameKey)}</h3>
                  <p className="text-xs text-slate-500 mt-1">{t(s.descKey)}</p>
                  <span
                    className={cn(
                      'badge mt-2',
                      s.difficulty === 'easy' && 'bg-emerald-500/20 text-emerald-400',
                      s.difficulty === 'medium' && 'bg-amber-500/20 text-amber-400',
                      s.difficulty === 'hard' && 'bg-red-500/20 text-red-400',
                    )}
                  >
                    {t(`simulation.${s.difficulty}`)}
                  </span>
                </button>
              ))}
            </div>

            {selectedScenario && (
              <button
                onClick={handleStart}
                disabled={startLoading}
                className="btn-primary mt-4 flex items-center gap-2"
              >
                {startLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {t('simulation.startDrill')}
              </button>
            )}

            {/* Score display */}
            {score !== null && (
              <div className="mt-4 glass-card p-4 max-w-md animate-slide-up">
                <div className="flex items-center gap-2 mb-3">
                  <Star className="w-5 h-5 text-amber-400" />
                  <h3 className="text-base font-semibold text-slate-200">{t('simulation.drillScore')}</h3>
                </div>
                <div className="text-center py-3">
                  <p className="text-4xl font-bold text-gradient">{score.overall}</p>
                  <p className="text-xs text-slate-500 mt-1">{t('simulation.overallScore')}</p>
                </div>
                <div className="space-y-1.5 mt-3">
                  {score.dimensions.map((d) => (
                    <div key={d.label} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-20">{d.label}</span>
                      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${d.score}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-300 w-8 text-right">{d.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Chat area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    'flex gap-3 animate-fade-in',
                    msg.role === 'agent' ? 'justify-end' : 'justify-start',
                  )}
                >
                  {msg.role !== 'agent' && (
                    <div
                      className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                        msg.role === 'customer'
                          ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                          : 'bg-gradient-to-br from-cyan-500 to-blue-600',
                      )}
                    >
                      {msg.role === 'customer' ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Lightbulb className="w-4 h-4 text-white" />
                      )}
                    </div>
                  )}
                  <div
                    className={cn(
                      'max-w-[65%] rounded-lg px-3 py-2',
                      msg.role === 'agent' && 'bg-indigo-600 text-white rounded-br-sm',
                      msg.role === 'customer' && 'bg-slate-800 text-slate-200 rounded-bl-sm border border-slate-700/50',
                      msg.role === 'coach' && 'bg-cyan-500/10 text-cyan-200 rounded-bl-sm border border-cyan-500/30',
                    )}
                  >
                    {msg.role === 'coach' && (
                      <p className="text-[10px] text-cyan-400 font-medium mb-1">{t('simulation.aiCoach')}</p>
                    )}
                    <p className="text-xs leading-relaxed">{msg.content}</p>
                    {msg.score != null && (
                      <p className="text-xs text-cyan-300 mt-1">{t('simulation.scoreLabel')}{msg.score}</p>
                    )}
                  </div>
                  {msg.role === 'agent' && (
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}
              {isTyping && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-slate-800 rounded-lg rounded-bl-sm px-3 py-2 border border-slate-700/50">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t border-slate-800 p-3">
              <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg p-2 focus-within:border-indigo-500/50">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={t('simulation.inputPlaceholder')}
                  className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 focus:outline-none text-sm"
                  disabled={isTyping}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isTyping}
                  className={cn(
                    'p-2 rounded-lg transition-all',
                    input.trim() && !isTyping
                      ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
                      : 'bg-slate-700 text-slate-500',
                  )}
                >
                  {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Right: Hints panel */}
      {isActive && (
        <div className="w-64 border-l border-slate-800 bg-slate-900/50 p-3 space-y-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-slate-200">{t('simulation.hintPanel')}</h3>
          </div>
          <div className="space-y-2">
            {hints.map((hint, i) => (
              <div key={i} className="bg-slate-800 rounded-lg p-3 border border-slate-700/50">
                <p className="text-xs text-slate-400 leading-relaxed">💡 {hint}</p>
              </div>
            ))}
          </div>

          <div className="glass-card p-3">
            <h4 className="text-xs font-medium text-slate-400 mb-1">{t('simulation.currentScenario')}</h4>
            {(() => {
              const s = SCENARIOS.find((sc) => sc.id === selectedScenario);
              if (!s) return null;
              return (
                <>
                  <p className="text-xs text-slate-200">{t(s.nameKey)}</p>
                  <p className="text-xs text-slate-500 mt-1">{t(s.descKey)}</p>
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
