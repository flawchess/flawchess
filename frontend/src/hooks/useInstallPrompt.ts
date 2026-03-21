import { useState, useEffect } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const ANDROID_DISMISS_KEY = 'install-prompt-dismissed';
const IOS_DISMISS_KEY = 'ios-install-banner-dismissed';

export function useInstallPrompt() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [isAndroidDismissed, setIsAndroidDismissed] = useState(
    () => localStorage.getItem(ANDROID_DISMISS_KEY) === 'true'
  );
  const [isIOSDismissed, setIsIOSDismissed] = useState(
    () => localStorage.getItem(IOS_DISMISS_KEY) === 'true'
  );

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setPromptEvent(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const triggerInstall = async () => {
    if (!promptEvent) return;
    await promptEvent.prompt();
    const { outcome } = await promptEvent.userChoice;
    if (outcome === 'accepted') {
      setPromptEvent(null);
    }
  };

  const dismissAndroid = () => {
    setIsAndroidDismissed(true);
    localStorage.setItem(ANDROID_DISMISS_KEY, 'true');
    setPromptEvent(null);
  };

  const dismissIOS = () => {
    setIsIOSDismissed(true);
    localStorage.setItem(IOS_DISMISS_KEY, 'true');
  };

  const isIOS = typeof navigator !== 'undefined' && /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isStandalone = typeof window !== 'undefined' && window.matchMedia('(display-mode: standalone)').matches;
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

  return {
    showAndroidPrompt: !!promptEvent && !isAndroidDismissed && !isStandalone && isMobile,
    showIOSBanner: isIOS && !isStandalone && !isIOSDismissed,
    triggerInstall,
    dismissAndroid,
    dismissIOS,
  };
}
