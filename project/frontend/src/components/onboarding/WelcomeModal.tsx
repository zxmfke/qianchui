import { useTranslation } from 'react-i18next';
import { Sparkles, ArrowRight, X } from 'lucide-react';

interface Props {
  onStartTour: () => void;
  onSkip: () => void;
}

export default function WelcomeModal({ onStartTour, onSkip }: Props) {
  const { t } = useTranslation();

  return (
    <div className="fixed inset-0 z-[9997] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[420px] bg-slate-800 border border-slate-600 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* Decorative header */}
        <div className="relative h-32 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center overflow-hidden">
          <div className="absolute inset-0 opacity-30">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="absolute rounded-full bg-white/20"
                style={{
                  width: Math.random() * 30 + 10,
                  height: Math.random() * 30 + 10,
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                  animationDelay: `${Math.random() * 2}s`,
                }}
              />
            ))}
          </div>
          <div className="relative text-center">
            <div className="w-14 h-14 mx-auto mb-2 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">{t('onboarding.welcome.title')}</h2>
          </div>
          <button
            onClick={onSkip}
            className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          <p className="text-sm text-slate-300 leading-relaxed mb-4">
            {t('onboarding.welcome.desc')}
          </p>

          <div className="space-y-2 mb-5">
            {(['feature1', 'feature2', 'feature3', 'feature4'] as const).map((key) => (
              <div key={key} className="flex items-start gap-2">
                <div className="w-5 h-5 mt-0.5 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                </div>
                <span className="text-xs text-slate-400">{t(`onboarding.welcome.${key}`)}</span>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <button
              onClick={onSkip}
              className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              {t('onboarding.welcome.skipBtn')}
            </button>
            <button
              onClick={onStartTour}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
            >
              {t('onboarding.welcome.startBtn')}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
