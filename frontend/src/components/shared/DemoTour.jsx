import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
    PlayCircle, X, ChevronLeft, ChevronRight, RefreshCw, CheckCircle2, Sparkles
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Demo tour overlay — shown after demo seed; walks user through key features
export default function DemoTour({ open, onClose, steps, onComplete }) {
    const navigate = useNavigate();
    const [stepIdx, setStepIdx] = useState(0);

    useEffect(() => {
        if (open && steps?.length > 0) {
            navigate(steps[0].route);
            setStepIdx(0);
        }
    }, [open]); // eslint-disable-line

    if (!open || !steps?.length) return null;
    const step = steps[stepIdx];

    const next = () => {
        if (stepIdx + 1 >= steps.length) {
            onComplete?.();
            onClose?.();
            toast.success('Tour complete! Continue exploring or upgrade to a paid plan.');
            return;
        }
        const newIdx = stepIdx + 1;
        setStepIdx(newIdx);
        navigate(steps[newIdx].route);
    };

    const prev = () => {
        if (stepIdx === 0) return;
        const newIdx = stepIdx - 1;
        setStepIdx(newIdx);
        navigate(steps[newIdx].route);
    };

    return (
        <div className="fixed inset-x-0 bottom-6 z-[60] flex justify-center pointer-events-none px-4" data-testid="demo-tour-overlay">
            <Card className="pointer-events-auto w-full max-w-2xl shadow-2xl border-indigo-200 bg-gradient-to-br from-white to-indigo-50/50 dark:from-slate-900 dark:to-indigo-950/30">
                <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <Badge className="bg-indigo-600 text-white">
                                    Step {stepIdx + 1} / {steps.length}
                                </Badge>
                                <span className="text-xs uppercase tracking-wider text-indigo-700 dark:text-indigo-300 font-semibold">
                                    Guided Demo
                                </span>
                            </div>
                            <h3 className="text-xl font-bold mt-1">{step.title}</h3>
                            <p className="text-sm text-muted-foreground mt-1">{step.description}</p>
                        </div>
                        <button onClick={onClose} className="p-1 rounded hover:bg-accent" data-testid="tour-close-btn">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="mt-4 flex items-center justify-between">
                        <div className="flex items-center gap-1">
                            {steps.map((_, i) => (
                                <div
                                    key={i}
                                    className={`h-1.5 rounded-full transition-all ${
                                        i === stepIdx ? 'bg-indigo-600 w-8' :
                                        i < stepIdx ? 'bg-indigo-400 w-4' : 'bg-slate-200 dark:bg-slate-700 w-4'
                                    }`}
                                />
                            ))}
                        </div>
                        <div className="flex gap-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={prev}
                                disabled={stepIdx === 0}
                                data-testid="tour-prev-btn"
                            >
                                <ChevronLeft className="w-4 h-4 mr-1" /> Back
                            </Button>
                            <Button
                                size="sm"
                                onClick={next}
                                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white"
                                data-testid="tour-next-btn"
                            >
                                {stepIdx + 1 === steps.length ? 'Finish' : 'Next'} <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

// Card that user clicks to start the demo (placed on Dashboard)
export function DemoLauncherCard({ onStart, isSeeded, onReset }) {
    const [loading, setLoading] = useState(false);

    const handleSeed = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(`${API_URL}/api/demo/seed`, {}, {
                headers: { Authorization: `Bearer ${token}` },
                withCredentials: true,
            });
            toast.success(`Demo data ready — ${res.data.employee_count} employees seeded`);
            onStart?.(res.data.tour_steps || []);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to seed demo');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        if (!window.confirm('This will delete all demo-seeded data for your company. Continue?')) return;
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await axios.post(`${API_URL}/api/demo/reset`, {}, {
                headers: { Authorization: `Bearer ${token}` },
                withCredentials: true,
            });
            toast.success('Demo data cleared');
            onReset?.();
        } catch {
            toast.error('Failed to reset');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="overflow-hidden border-0 bg-gradient-to-r from-indigo-600 via-purple-600 to-fuchsia-600 text-white" data-testid="demo-launcher-card">
            <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                            <Sparkles className="w-5 h-5" />
                            <span className="text-xs uppercase tracking-wider font-bold opacity-90">
                                {isSeeded ? 'Demo Active' : 'Try the demo'}
                            </span>
                        </div>
                        <h3 className="text-2xl font-bold">
                            {isSeeded ? 'Continue your guided tour' : 'Experience the full platform in 60 seconds'}
                        </h3>
                        <p className="text-sm opacity-90 mt-1 max-w-xl">
                            We'll seed sample employees, a draft payroll run, statutory calculations, UKVI alerts and a
                            Stripe test checkout — then walk you through the key screens. No real data created.
                        </p>
                    </div>
                    {isSeeded && <CheckCircle2 className="w-10 h-10 flex-shrink-0 opacity-80" />}
                </div>
                <div className="flex gap-2 mt-5">
                    <Button
                        onClick={handleSeed}
                        disabled={loading}
                        className="bg-white text-indigo-700 hover:bg-indigo-50 font-semibold"
                        data-testid="start-demo-btn"
                    >
                        <PlayCircle className="w-4 h-4 mr-2" />
                        {isSeeded ? 'Restart Tour' : 'Start Demo Tour'}
                    </Button>
                    {isSeeded && (
                        <Button
                            variant="outline"
                            onClick={handleReset}
                            disabled={loading}
                            className="border-white/40 text-white hover:bg-white/10"
                            data-testid="reset-demo-btn"
                        >
                            <RefreshCw className="w-4 h-4 mr-2" /> Clear Demo Data
                        </Button>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
