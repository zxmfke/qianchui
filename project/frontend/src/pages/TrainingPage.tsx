import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  GraduationCap,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Trophy,
  Target,
  Zap,
  BarChart2,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { trainingService } from '@/services/training';
import type { TrainingProgress } from '@/services/training';
import type { TrainingQuiz } from '@/types';

export default function TrainingPage() {
  const { t } = useTranslation();
  const [questions, setQuestions] = useState<TrainingQuiz[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [progress, setProgress] = useState<TrainingProgress | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [resultData, setResultData] = useState<{
    isCorrect: boolean;
    explanation: string;
    correctAnswer: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProgress = useCallback(async () => {
    try {
      const p = await trainingService.getProgress();
      setProgress(p);
    } catch {
      setProgress(null);
    }
  }, []);

  const loadQuestions = useCallback(async () => {
    setError(null);
    try {
      const qs = await trainingService.getQuiz();
      setQuestions(qs);
      setCurrentIdx(0);
    } catch {
      setQuestions([]);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([loadProgress(), loadQuestions()]);
      setLoading(false);
    };
    init();
  }, [loadProgress, loadQuestions]);

  const quiz = questions[currentIdx] ?? null;

  const handleAnswer = async (key: string) => {
    if (!quiz || showResult) return;
    setSelectedAnswer(key);
    try {
      const res = await trainingService.submitAnswer(quiz as unknown as Record<string, unknown>, key);
      const expObj = res.explanation;
      const expText = expObj
        ? `心理分析: ${expObj.psychology}\n策略: ${expObj.strategy}\n话术参考: ${expObj.script}`
        : '';
      setResultData({
        isCorrect: res.is_correct,
        explanation: expText,
        correctAnswer: res.correct_answer,
      });
      setShowResult(true);
      await loadProgress();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('training.submitFailed'));
    }
  };

  const handleNext = () => {
    setSelectedAnswer(null);
    setShowResult(false);
    setResultData(null);
    if (currentIdx < questions.length - 1) {
      setCurrentIdx((i) => i + 1);
    } else {
      loadQuestions();
    }
  };

  const completed = progress?.completed ?? 0;
  const total = progress?.total_quizzes ?? 100;
  const accuracy = progress?.accuracy ?? 0;
  const streak = progress?.streak ?? 0;
  const correct = progress?.correct ?? 0;
  const weakAreas = progress?.weak_areas ?? [];
  const difficultyLabel =
    quiz?.difficulty === 'easy' || quiz?.difficulty === (1 as unknown)
      ? t('training.easy')
      : quiz?.difficulty === 'hard' || quiz?.difficulty === (3 as unknown)
        ? t('training.hard')
        : t('training.medium');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-slate-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-100">{t('pages.training')}</h1>
        <span className="text-xs text-slate-500">{t('training.dailyPractice')}，{t('training.scriptImprovement')}</span>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-2.5 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-4 gap-3">
        {[
          { icon: Target, color: 'indigo', value: `${completed}`, labelKey: 'training.completed' },
          { icon: CheckCircle2, color: 'emerald', value: `${(accuracy * 100).toFixed(1)}%`, labelKey: 'training.accuracy' },
          { icon: Zap, color: 'amber', value: `${streak}`, labelKey: 'training.streakDays' },
          { icon: Trophy, color: 'cyan', value: `${correct}`, labelKey: 'training.totalCorrect' },
        ].map((s) => (
          <div key={s.labelKey} className="glass-card p-3 flex items-center gap-2.5">
            <div className={`p-1.5 rounded-md bg-${s.color}-500/10 border border-${s.color}-500/30`}>
              <s.icon className={`w-4 h-4 text-${s.color}-400`} />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-100">{s.value}</p>
              <p className="text-[10px] text-slate-500">{t(s.labelKey)}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="glass-card p-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-400">{t('training.learningProgress')}</span>
          <span className="text-xs text-indigo-400 font-medium">{completed}/{total}</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
            style={{ width: `${total > 0 ? (completed / total) * 100 : 0}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <GraduationCap className="w-4 h-4 text-indigo-400" />
            <h2 className="text-xs font-semibold text-slate-200">
              {t('training.dailyPractice')} {questions.length > 0 && `(${currentIdx + 1}/${questions.length})`}
            </h2>
            {quiz && (
              <>
                <span className="badge bg-slate-700 text-slate-400 text-[10px]">{quiz.category}</span>
                <span
                  className={cn(
                    'badge text-[10px]',
                    difficultyLabel === t('training.easy') && 'bg-emerald-500/20 text-emerald-400',
                    difficultyLabel === t('training.medium') && 'bg-amber-500/20 text-amber-400',
                    difficultyLabel === t('training.hard') && 'bg-red-500/20 text-red-400',
                  )}
                >
                  {difficultyLabel}
                </span>
              </>
            )}
          </div>

          {!quiz ? (
            <div className="text-center py-8">
              <Trophy className="w-10 h-10 text-amber-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-200 mb-1">{t('training.allDone')}</p>
              <p className="text-xs text-slate-500">{t('training.moreTomorrow')}</p>
            </div>
          ) : (
            <>
              <p className="text-sm text-slate-200 mb-4 leading-relaxed">{quiz.question}</p>

              <div className="space-y-2">
                {quiz.options.map((opt) => {
                  const isSelected = selectedAnswer === opt.key;
                  const correctKey = resultData?.correctAnswer || quiz.correct_answer;
                  const isCorrectOpt = opt.key === correctKey;
                  return (
                    <button
                      key={opt.key}
                      onClick={() => handleAnswer(opt.key)}
                      disabled={showResult}
                      className={cn(
                        'w-full text-left px-3 py-2.5 rounded-lg border transition-all flex items-center gap-2.5 text-xs',
                        !showResult && 'bg-slate-800 border-slate-700 hover:border-indigo-500/50 hover:bg-slate-700/80',
                        showResult && isCorrectOpt && 'bg-emerald-500/10 border-emerald-500/50',
                        showResult && isSelected && !isCorrectOpt && 'bg-red-500/10 border-red-500/50',
                        showResult && !isSelected && !isCorrectOpt && 'bg-slate-800/50 border-slate-700/50 opacity-50',
                      )}
                    >
                      <span
                        className={cn(
                          'w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border flex-shrink-0',
                          !showResult && 'bg-slate-700 border-slate-600 text-slate-300',
                          showResult && isCorrectOpt && 'bg-emerald-500/20 border-emerald-500 text-emerald-400',
                          showResult && isSelected && !isCorrectOpt && 'bg-red-500/20 border-red-500 text-red-400',
                        )}
                      >
                        {opt.key}
                      </span>
                      <span className="text-slate-200 flex-1">{opt.text}</span>
                      {showResult && isCorrectOpt && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                      {showResult && isSelected && !isCorrectOpt && <XCircle className="w-4 h-4 text-red-400" />}
                    </button>
                  );
                })}
              </div>

              {showResult && resultData && (
                <div
                  className={cn(
                    'mt-4 p-3 rounded-lg border animate-fade-in text-xs',
                    resultData.isCorrect
                      ? 'bg-emerald-500/10 border-emerald-500/30'
                      : 'bg-amber-500/10 border-amber-500/30',
                  )}
                >
                  <p className={cn('font-medium mb-1.5', resultData.isCorrect ? 'text-emerald-400' : 'text-amber-400')}>
                    {resultData.isCorrect ? t('training.correct') : t('training.wrong')}
                  </p>
                  <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">{resultData.explanation}</p>
                </div>
              )}

              {showResult && (
                <button onClick={handleNext} className="btn-primary mt-3 text-xs flex items-center gap-1.5 px-3 py-1.5">
                  {currentIdx < questions.length - 1 ? t('training.next') : t('training.newSet')}
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}
            </>
          )}
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 className="w-4 h-4 text-amber-400" />
            <h2 className="text-xs font-semibold text-slate-200">{t('training.weakAreas')}</h2>
          </div>
          {weakAreas.length > 0 ? (
            <div className="space-y-3">
              {weakAreas.map((area, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-300">{area.category}</span>
                    <span className="text-[10px] text-slate-500">{(area.accuracy * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        area.accuracy < 0.65 ? 'bg-red-500' : area.accuracy < 0.75 ? 'bg-amber-500' : 'bg-emerald-500',
                      )}
                      style={{ width: `${area.accuracy * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 text-center py-4">{t('common.noData')}</p>
          )}

          <div className="mt-4 p-2.5 bg-slate-800 rounded-lg">
            <p className="text-[10px] text-slate-400 leading-relaxed">
              {t('training.weakTip')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
