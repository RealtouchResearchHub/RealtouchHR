import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Lock, ArrowRight, Sparkles, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Routes that remain accessible even when trial has expired
const ALLOWED_PATHS = ['/billing', '/settings', '/settings/billing'];

export default function SubscriptionWall() {
    const [expired, setExpired] = useState(false);
    const location = useLocation();

    useEffect(() => {
        (async () => {
            try {
                const token = localStorage.getItem('token');
                if (!token) return;
                const res = await axios.get(`${API_URL}/api/trial/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                    withCredentials: true,
                });
                setExpired(!!res.data?.trial_expired);
            } catch (e) { /* ignore */ }
        })();
    }, [location.pathname]);

    const isAllowedPath = ALLOWED_PATHS.some(p => location.pathname.startsWith(p));
    if (!expired || isAllowedPath) return null;

    return (
        <div
            className="fixed inset-0 z-[9000] flex items-center justify-center bg-slate-950/95 backdrop-blur-sm"
            data-testid="subscription-wall"
        >
            <div className="max-w-md w-full mx-4 text-center space-y-6">
                {/* Icon */}
                <div className="flex justify-center">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center">
                        <Lock className="w-9 h-9 text-indigo-400" />
                    </div>
                </div>

                {/* Headline */}
                <div>
                    <h2 className="text-2xl font-bold text-white mb-2">
                        Your free trial has ended
                    </h2>
                    <p className="text-white/65 leading-relaxed">
                        Your 14-day free trial has expired. Subscribe to a plan to restore full access to your payroll, HR and compliance tools.
                    </p>
                </div>

                {/* Feature reminder */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-left space-y-2">
                    {[
                        'HMRC RTI readiness support',
                        'Payroll, PAYE and payslips',
                        'UKVI compliance & alerts',
                        'HR records and documents',
                    ].map(f => (
                        <div key={f} className="flex items-center gap-2 text-sm text-white/80">
                            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                            {f}
                        </div>
                    ))}
                </div>

                {/* CTA */}
                <div className="space-y-3">
                    <Link to="/billing">
                        <Button
                            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold py-6 rounded-xl text-base"
                            data-testid="subscription-wall-upgrade-btn"
                        >
                            <Sparkles className="w-4 h-4 mr-2" />
                            Choose a plan
                            <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                    </Link>
                    <p className="text-xs text-white/40">
                        From £29/month · Cancel any time · No setup fee
                    </p>
                </div>

                {/* Settings link */}
                <p className="text-xs text-white/35">
                    Need help?{' '}
                    <a href="mailto:support@realtouchhr.com" className="text-indigo-400 hover:text-indigo-300 underline">
                        Contact support
                    </a>
                    {' '}or{' '}
                    <Link to="/settings" className="text-indigo-400 hover:text-indigo-300 underline">
                        manage your account
                    </Link>
                </p>
            </div>
        </div>
    );
}
