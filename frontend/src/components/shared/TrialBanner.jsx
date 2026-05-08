import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { AlertCircle, Sparkles, X } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function TrialBanner() {
    const [status, setStatus] = useState(null);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const token = localStorage.getItem('token');
                if (!token) return;
                const res = await axios.get(`${API_URL}/api/trial/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                    withCredentials: true,
                });
                setStatus(res.data);
            } catch (e) { /* ignore */ }
        })();
    }, []);

    if (!status || !status.trial_active || dismissed) return null;

    const urgent = status.days_remaining <= 3;
    return (
        <div
            className={`px-4 py-2 text-xs flex items-center justify-between ${
                urgent
                    ? 'bg-gradient-to-r from-rose-600 to-orange-600 text-white'
                    : 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white'
            }`}
            data-testid="trial-banner"
        >
            <div className="flex items-center gap-2 flex-1">
                {urgent ? <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> : <Sparkles className="w-3.5 h-3.5 flex-shrink-0" />}
                <span>
                    <strong>Free trial — {status.days_remaining} day{status.days_remaining === 1 ? '' : 's'} remaining.</strong>{' '}
                    Downloads are disabled during the trial.{' '}
                    <Link to="/billing" className="underline font-semibold">Upgrade to unlock</Link>
                    .
                </span>
            </div>
            <button onClick={() => setDismissed(true)} className="ml-2 opacity-80 hover:opacity-100" data-testid="dismiss-trial-banner">
                <X className="w-3.5 h-3.5" />
            </button>
        </div>
    );
}
