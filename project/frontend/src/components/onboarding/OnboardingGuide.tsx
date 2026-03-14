import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';
import { X, ChevronLeft, ChevronRight, Sparkles, SkipForward } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface OnboardingStep {
  target: string;
  titleKey: string;
  descKey: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
  route?: string;
  pageTarget?: string;
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    target: '[data-tour="sidebar"]',
    titleKey: 'onboarding.steps.sidebar.title',
    descKey: 'onboarding.steps.sidebar.desc',
    position: 'right',
  },
  {
    target: '[data-tour="nav-chat"]',
    titleKey: 'onboarding.steps.chat.title',
    descKey: 'onboarding.steps.chat.desc',
    position: 'right',
    route: '/chat',
  },
  {
    target: '[data-tour="page-chat-input"]',
    titleKey: 'onboarding.steps.chatInput.title',
    descKey: 'onboarding.steps.chatInput.desc',
    position: 'top',
    route: '/chat',
    pageTarget: '[data-tour="page-chat-input"]',
  },
  {
    target: '[data-tour="nav-dashboard"]',
    titleKey: 'onboarding.steps.dashboard.title',
    descKey: 'onboarding.steps.dashboard.desc',
    position: 'right',
    route: '/dashboard',
  },
  {
    target: '[data-tour="page-dashboard-stats"]',
    titleKey: 'onboarding.steps.dashboardStats.title',
    descKey: 'onboarding.steps.dashboardStats.desc',
    position: 'bottom',
    route: '/dashboard',
    pageTarget: '[data-tour="page-dashboard-stats"]',
  },
  {
    target: '[data-tour="nav-scripts"]',
    titleKey: 'onboarding.steps.scripts.title',
    descKey: 'onboarding.steps.scripts.desc',
    position: 'right',
    route: '/scripts',
  },
  {
    target: '[data-tour="nav-training"]',
    titleKey: 'onboarding.steps.training.title',
    descKey: 'onboarding.steps.training.desc',
    position: 'right',
    route: '/training',
  },
  {
    target: '[data-tour="nav-simulation"]',
    titleKey: 'onboarding.steps.simulation.title',
    descKey: 'onboarding.steps.simulation.desc',
    position: 'right',
    route: '/simulation',
  },
  {
    target: '[data-tour="nav-diagnosis"]',
    titleKey: 'onboarding.steps.diagnosis.title',
    descKey: 'onboarding.steps.diagnosis.desc',
    position: 'right',
    route: '/diagnosis',
  },
  {
    target: '[data-tour="nav-optimization"]',
    titleKey: 'onboarding.steps.optimization.title',
    descKey: 'onboarding.steps.optimization.desc',
    position: 'right',
    route: '/optimization',
  },
  {
    target: '[data-tour="nav-channel-materials"]',
    titleKey: 'onboarding.steps.channelMaterials.title',
    descKey: 'onboarding.steps.channelMaterials.desc',
    position: 'right',
    route: '/channel-materials',
  },
  {
    target: '[data-tour="nav-flywheel"]',
    titleKey: 'onboarding.steps.flywheel.title',
    descKey: 'onboarding.steps.flywheel.desc',
    position: 'right',
    route: '/flywheel',
  },
  {
    target: '[data-tour="nav-memory"]',
    titleKey: 'onboarding.steps.memory.title',
    descKey: 'onboarding.steps.memory.desc',
    position: 'right',
    route: '/memory',
  },
  {
    target: '[data-tour="nav-settings"]',
    titleKey: 'onboarding.steps.settings.title',
    descKey: 'onboarding.steps.settings.desc',
    position: 'right',
    route: '/settings',
  },
];

const STORAGE_KEY = 'qianchui_onboarding_completed';

interface TooltipPos {
  top: number;
  left: number;
  arrowDir: 'top' | 'bottom' | 'left' | 'right';
}

function calcTooltipPos(
  rect: DOMRect,
  position: 'top' | 'bottom' | 'left' | 'right',
  tooltipW: number,
  tooltipH: number,
): TooltipPos {
  const gap = 16;
  switch (position) {
    case 'right':
      return {
        top: rect.top + rect.height / 2 - tooltipH / 2,
        left: rect.right + gap,
        arrowDir: 'left',
      };
    case 'left':
      return {
        top: rect.top + rect.height / 2 - tooltipH / 2,
        left: rect.left - tooltipW - gap,
        arrowDir: 'right',
      };
    case 'bottom':
      return {
        top: rect.bottom + gap,
        left: rect.left + rect.width / 2 - tooltipW / 2,
        arrowDir: 'top',
      };
    case 'top':
    default:
      return {
        top: rect.top - tooltipH - gap,
        left: rect.left + rect.width / 2 - tooltipW / 2,
        arrowDir: 'bottom',
      };
  }
}

interface Props {
  onComplete?: () => void;
}

export default function OnboardingGuide({ onComplete }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const [tooltipPos, setTooltipPos] = useState<TooltipPos | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [animating, setAnimating] = useState(false);

  const currentStep = ONBOARDING_STEPS[step];
  const totalSteps = ONBOARDING_STEPS.length;
  const progressPct = ((step + 1) / totalSteps) * 100;

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      const timer = setTimeout(() => setVisible(true), 800);
      return () => clearTimeout(timer);
    }
  }, []);

  const highlightTarget = useCallback(() => {
    if (!currentStep) return;
    const targetSelector = currentStep.pageTarget || currentStep.target;
    const el = document.querySelector(targetSelector);
    if (el) {
      const rect = el.getBoundingClientRect();
      setTargetRect(rect);

      requestAnimationFrame(() => {
        const tw = tooltipRef.current?.offsetWidth || 400;
        const th = tooltipRef.current?.offsetHeight || 200;
        const pos = calcTooltipPos(rect, currentStep.position || 'right', tw, th);
        pos.top = Math.max(12, Math.min(window.innerHeight - th - 12, pos.top));
        pos.left = Math.max(12, Math.min(window.innerWidth - tw - 12, pos.left));
        setTooltipPos(pos);
      });
    } else {
      const navEl = document.querySelector(currentStep.target);
      if (navEl) {
        const rect = navEl.getBoundingClientRect();
        setTargetRect(rect);
        requestAnimationFrame(() => {
          const tw = tooltipRef.current?.offsetWidth || 400;
          const th = tooltipRef.current?.offsetHeight || 200;
          const pos = calcTooltipPos(rect, 'right', tw, th);
          pos.top = Math.max(12, Math.min(window.innerHeight - th - 12, pos.top));
          pos.left = Math.max(12, Math.min(window.innerWidth - tw - 12, pos.left));
          setTooltipPos(pos);
        });
      }
    }
  }, [currentStep]);

  useEffect(() => {
    if (!visible) return;
    if (currentStep?.route && location.pathname !== currentStep.route) {
      navigate(currentStep.route);
      const timer = setTimeout(highlightTarget, 500);
      return () => clearTimeout(timer);
    }
    const timer = setTimeout(highlightTarget, 100);
    return () => clearTimeout(timer);
  }, [visible, step, currentStep, location.pathname, navigate, highlightTarget]);

  useEffect(() => {
    if (!visible) return;
    const onResize = () => highlightTarget();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [visible, highlightTarget]);

  const goNext = useCallback(() => {
    if (step < totalSteps - 1) {
      setAnimating(true);
      setTimeout(() => {
        setStep((s) => s + 1);
        setAnimating(false);
      }, 200);
    } else {
      finish();
    }
  }, [step, totalSteps]);

  const goPrev = useCallback(() => {
    if (step > 0) {
      setAnimating(true);
      setTimeout(() => {
        setStep((s) => s - 1);
        setAnimating(false);
      }, 200);
    }
  }, [step]);

  const finish = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setVisible(false);
    onComplete?.();
  }, [onComplete]);

  if (!visible) return null;

  return (
    <>
      <div className="fixed inset-0 z-[9998]" onClick={finish}>
        <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
          <defs>
            <mask id="onboarding-mask">
              <rect x="0" y="0" width="100%" height="100%" fill="white" />
              {targetRect && (
                <rect
                  x={targetRect.left - 6}
                  y={targetRect.top - 6}
                  width={targetRect.width + 12}
                  height={targetRect.height + 12}
                  rx="8"
                  fill="black"
                />
              )}
            </mask>
          </defs>
          <rect
            x="0" y="0" width="100%" height="100%"
            fill="rgba(0,0,0,0.65)"
            mask="url(#onboarding-mask)"
            style={{ pointerEvents: 'all' }}
          />
        </svg>

        {targetRect && (
          <div
            className="absolute rounded-lg pointer-events-none"
            style={{
              top: targetRect.top - 6,
              left: targetRect.left - 6,
              width: targetRect.width + 12,
              height: targetRect.height + 12,
              boxShadow: '0 0 0 2px rgba(129, 140, 248, 0.8), 0 0 20px 4px rgba(99, 102, 241, 0.3)',
            }}
          />
        )}
      </div>

      {tooltipPos && (
        <div
          ref={tooltipRef}
          className={cn(
            'fixed z-[9999] w-[400px] max-w-[calc(100vw-24px)] transition-all duration-200',
            animating ? 'opacity-0 scale-95' : 'opacity-100 scale-100',
          )}
          style={{ top: tooltipPos.top, left: tooltipPos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className={cn(
              'absolute w-3 h-3 rotate-45',
              'bg-slate-800/95 border-slate-600/80',
              tooltipPos.arrowDir === 'left' && 'left-[-7px] top-1/2 -translate-y-1/2 border-l border-b',
              tooltipPos.arrowDir === 'right' && 'right-[-7px] top-1/2 -translate-y-1/2 border-r border-t',
              tooltipPos.arrowDir === 'top' && 'top-[-7px] left-1/2 -translate-x-1/2 border-l border-t',
              tooltipPos.arrowDir === 'bottom' && 'bottom-[-7px] left-1/2 -translate-x-1/2 border-r border-b',
            )}
          />

          <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-600/80 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden">
            {/* Progress bar at top */}
            <div className="h-1 bg-slate-700/60">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500 ease-out rounded-r-full"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-5 py-2.5">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-semibold text-indigo-300">
                  {t('onboarding.title')}
                </span>
              </div>
              <button
                onClick={finish}
                className="p-1 rounded-md hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Content */}
            <div className="px-5 pb-4">
              <h3 className="text-[15px] font-bold text-slate-50 mb-2 leading-snug">
                {t(currentStep.titleKey)}
              </h3>
              <p className="text-sm text-slate-300/90 leading-relaxed whitespace-pre-line max-h-[40vh] overflow-y-auto">
                {t(currentStep.descKey)}
              </p>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-700/60 bg-slate-900/40">
              <span className="text-xs font-medium text-slate-400 tabular-nums">
                {step + 1} / {totalSteps}
              </span>

              <div className="flex items-center gap-2">
                {step === 0 ? (
                  <button
                    onClick={finish}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition-colors"
                  >
                    <SkipForward className="w-3 h-3" />
                    {t('onboarding.skip')}
                  </button>
                ) : (
                  <button
                    onClick={goPrev}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition-colors"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    {t('onboarding.prev')}
                  </button>
                )}

                <button
                  onClick={goNext}
                  className="flex items-center gap-1 px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-lg shadow-indigo-600/20"
                >
                  {step < totalSteps - 1 ? (
                    <>
                      {t('onboarding.next')}
                      <ChevronRight className="w-3.5 h-3.5" />
                    </>
                  ) : (
                    t('onboarding.finish')
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function resetOnboarding() {
  localStorage.removeItem(STORAGE_KEY);
}

export function isOnboardingCompleted() {
  return !!localStorage.getItem(STORAGE_KEY);
}
