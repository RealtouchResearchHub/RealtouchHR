import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Cookie, X, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '../ui/button';

const STORAGE_KEY = 'rhr_cookie_consent';

export default function CookieConsent() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) setVisible(true);
    }, []);

    const accept = () => {
        localStorage.setItem(STORAGE_KEY, 'accepted');
        setVisible(false);
    };

    const decline = () => {
        localStorage.setItem(STORAGE_KEY, 'declined');
        setVisible(false);
    };

    if (!visible) return null;

    return (
        <div
            className="fixed bottom-0 left-0 right-0 z-[9999] p-4 md:p-6"
            role="dialog"
            aria-label="Cookie consent"
            data-testid="cookie-consent-banner"
        >
            <div className="max-w-4xl mx-auto bg-slate-900 border border-white/10 rounded-xl shadow-2xl p-5 md:p-6">
                <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
                        <Cookie className="w-4.5 h-4.5 text-indigo-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-white mb-1">
                            Cookies &amp; Privacy
                        </h3>
                        <p className="text-xs text-white/70 leading-relaxed">
                            We use strictly necessary cookies to keep you logged in and remember your preferences.
                            We also use analytics cookies to understand how the platform is used — these are only
                            set with your consent, as required by UK PECR and UK GDPR.
                            {' '}
                            <Link to="/privacy#cookies" className="text-indigo-400 hover:text-indigo-300 underline">
                                Read our Cookie Policy
                            </Link>
                            .
                        </p>
                    </div>
                    <button
                        onClick={decline}
                        className="flex-shrink-0 text-white/40 hover:text-white/80 transition-colors"
                        aria-label="Dismiss"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 justify-end">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={decline}
                        className="text-white/60 hover:text-white hover:bg-white/10 text-xs border border-white/10"
                        data-testid="cookie-decline-btn"
                    >
                        <XCircle className="w-3.5 h-3.5 mr-1.5" />
                        Decline optional cookies
                    </Button>
                    <Button
                        size="sm"
                        onClick={accept}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs"
                        data-testid="cookie-accept-btn"
                    >
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                        Accept all cookies
                    </Button>
                </div>
            </div>
        </div>
    );
}
