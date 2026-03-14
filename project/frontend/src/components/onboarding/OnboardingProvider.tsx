import { useState, useCallback, useEffect } from 'react';
import WelcomeModal from './WelcomeModal';
import OnboardingGuide, { isOnboardingCompleted, resetOnboarding } from './OnboardingGuide';

const STORAGE_KEY = 'qianchui_onboarding_completed';

export default function OnboardingProvider() {
  const [phase, setPhase] = useState<'idle' | 'welcome' | 'tour' | 'done'>('idle');

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      const timer = setTimeout(() => setPhase('welcome'), 600);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleStartTour = useCallback(() => {
    setPhase('tour');
  }, []);

  const handleSkip = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setPhase('done');
  }, []);

  const handleTourComplete = useCallback(() => {
    setPhase('done');
  }, []);

  if (phase === 'welcome') {
    return <WelcomeModal onStartTour={handleStartTour} onSkip={handleSkip} />;
  }

  if (phase === 'tour') {
    return <OnboardingGuide onComplete={handleTourComplete} />;
  }

  return null;
}

export { resetOnboarding, isOnboardingCompleted };
