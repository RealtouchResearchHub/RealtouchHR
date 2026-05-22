import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { useAuth } from '../../contexts/AuthContext';
import {
    Building2, Sparkles, ShieldCheck, Zap, ArrowRight, CheckCircle2,
    PoundSterling, Users, FileCheck2, HeartPulse, Clock, Loader2,
    PlayCircle, Star, Cpu,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function LandingPage() {
    const navigate = useNavigate();
    const { refresh } = useAuth();
    const [loading, setLoading] = useState(false);

    const startSandboxDemo = async () => {
        setLoading(true);
        try {
            const res = await axios.post(`${API_URL}/api/demo/sandbox`, {}, {
                withCredentials: true,
            });
            const { token, tour_steps } = res.data;
            // Persist sandbox token
            localStorage.setItem('token', token);
            // Persist tour state
            localStorage.setItem('demo_tour_steps', JSON.stringify(tour_steps));
            localStorage.setItem('demo_tour_active', 'true');
            // Refresh auth context
            await refresh?.();
            toast.success('Demo environment ready — your tour starts now');
            // Hard navigation so AuthContext re-checks /api/auth/me with fresh token
            window.location.href = '/dashboard';
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Could not launch demo. Try again.');
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-purple-950 text-white" data-testid="landing-page">
            {/* Nav */}
            <header className="border-b border-white/5 backdrop-blur-md bg-slate-950/30">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                            <Building2 className="w-5 h-5" />
                        </div>
                        <span className="font-bold text-lg tracking-tight">RealtouchHR</span>
                    </div>
                    <nav className="hidden md:flex items-center gap-6 text-sm">
                        <a href="#features" className="text-white/80 hover:text-white transition">Features</a>
                        <a href="#pricing" className="text-white/80 hover:text-white transition">Pricing</a>
                        <a href="#compliance" className="text-white/80 hover:text-white transition">Compliance</a>
                    </nav>
                    <div className="flex items-center gap-2">
                        <Link to="/login" className="text-sm text-white/80 hover:text-white px-3 py-1.5">
                            Sign in
                        </Link>
                        <Link
                            to="/register"
                            className="text-sm bg-white text-slate-900 hover:bg-slate-100 px-4 py-2 rounded-md font-semibold transition"
                            data-testid="landing-signup-link"
                        >
                            Sign up
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero */}
            <section className="max-w-7xl mx-auto px-6 pt-20 pb-24 relative overflow-hidden">
                <div className="absolute -top-20 -right-20 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute -bottom-20 -left-20 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl pointer-events-none" />

                <div className="relative">
                    <Badge className="mb-6 bg-white/10 hover:bg-white/15 border border-white/20 backdrop-blur" data-testid="landing-hero-badge">
                        <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Tax year 2025-26 ready · HMRC RTI · UKVI
                    </Badge>
                    <h1 className="text-5xl md:text-7xl font-bold tracking-tight max-w-4xl leading-[1.05]" data-testid="landing-hero-title">
                        UK Payroll, HR & Compliance —{' '}
                        <span className="bg-gradient-to-r from-indigo-300 via-purple-300 to-fuchsia-300 bg-clip-text text-transparent">
                            on autopilot
                        </span>
                    </h1>
                    <p className="mt-6 text-lg md:text-xl text-white/70 max-w-2xl leading-relaxed">
                        From RTI submissions to UKVI sponsor licence monitoring, statutory pay calculators
                        and Stripe-powered billing — RealtouchHR replaces a stack of spreadsheets and
                        consultants for under £39/month.
                    </p>

                    <div className="mt-10 flex flex-wrap gap-3">
                        <Button
                            size="lg"
                            onClick={startSandboxDemo}
                            disabled={loading}
                            className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white text-base font-semibold px-8 py-6 rounded-xl shadow-2xl shadow-indigo-500/30"
                            data-testid="try-demo-btn"
                        >
                            {loading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <PlayCircle className="w-5 h-5 mr-2" />}
                            Try the live demo (no signup)
                        </Button>
                        <Link to="/register">
                            <Button
                                size="lg"
                                variant="outline"
                                className="bg-transparent border-white/30 text-white hover:bg-white/10 text-base px-8 py-6 rounded-xl"
                                data-testid="landing-create-account-btn"
                            >
                                Create an account <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                        </Link>
                    </div>
                    <p className="mt-3 text-xs text-white/50">
                        ⚡ The demo seeds 6 fake employees + a sample pay run + UKVI alerts. Sandbox accounts auto-expire after 24 hours.
                    </p>

                    {/* Trust strip */}
                    <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                        {[
                            { value: '92%', label: 'Average compliance score uplift' },
                            { value: '60s', label: 'From signup to first pay run' },
                            { value: '£0', label: 'Setup or onboarding fee' },
                            { value: 'GDPR', label: 'Audit-ready by default' },
                        ].map((s) => (
                            <div key={s.label} className="border-l-2 border-white/20 pl-4">
                                <div className="text-3xl font-bold">{s.value}</div>
                                <div className="text-white/60 mt-1">{s.label}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features */}
            <section id="features" className="max-w-7xl mx-auto px-6 py-20">
                <div className="text-center mb-14">
                    <Badge className="mb-3 bg-white/10 border border-white/20">What's included</Badge>
                    <h2 className="text-4xl md:text-5xl font-bold">
                        One platform, <span className="text-indigo-300">everything UK payroll</span>
                    </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {[
                        { icon: Users, title: 'Core HR + Self-Service', desc: 'Employee records, leave, documents, onboarding wizard. RBAC + audit log baked in.' },
                        { icon: PoundSterling, title: 'Guided Payroll Flow', desc: 'PAYE, NI, pension, student loans (Plans 1/2/4/5 + Postgrad). Payslip PDF and HMRC RTI/FPS submission included.' },
                        { icon: ShieldCheck, title: 'UKVI Sponsor Licence', desc: 'Right-to-Work checks, CoS register, visa expiry alerts, salary threshold monitoring.' },
                        { icon: HeartPulse, title: 'Statutory Payments', desc: 'SSP / SMP / SPP / ShPP / SAP calculators with 92%/103% recovery built in.' },
                        { icon: FileCheck2, title: 'P45 / P60 / P11D', desc: 'Auto-generated tax documents on offboarding, on-demand, or year-end.' },
                        { icon: Cpu, title: 'AI Copilot', desc: 'GPT-4o powered assistant answers payroll, compliance and HR questions in plain English.' },
                    ].map((f, i) => (
                        <Card
                            key={i}
                            className="bg-white/5 border-white/10 backdrop-blur hover:bg-white/[0.07] transition group"
                        >
                            <CardContent className="p-6">
                                <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center mb-4 group-hover:scale-105 transition">
                                    <f.icon className="w-5 h-5 text-indigo-300" />
                                </div>
                                <h3 className="text-xl font-semibold">{f.title}</h3>
                                <p className="text-sm text-white/60 mt-2 leading-relaxed">{f.desc}</p>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </section>

            {/* Pricing */}
            <section id="pricing" className="max-w-7xl mx-auto px-6 py-20 border-t border-white/5">
                <div className="text-center mb-12">
                    <Badge className="mb-3 bg-white/10 border border-white/20">Pricing</Badge>
                    <h2 className="text-4xl md:text-5xl font-bold">Simple, all-in-GBP</h2>
                    <p className="mt-3 text-white/60">No per-user surprise charges. Cancel any time.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-5xl mx-auto">
                    {[
                        { name: 'Starter', price: 39, employees: '10', features: ['Core HR + Payroll', 'HMRC RTI', 'UKVI checks', 'Email support'] },
                        { name: 'Professional', price: 59, employees: '50', featured: true, features: ['Everything in Starter', 'Statutory pay automation', 'AI Copilot', 'Priority chat support'] },
                        { name: 'Enterprise', price: 149, employees: 'Unlimited', features: ['Multi-entity', 'SCIM/SAML SSO', 'Dedicated CSM', 'Sponsor licence health'] },
                    ].map((p) => (
                        <Card
                            key={p.name}
                            className={`relative ${
                                p.featured
                                    ? 'bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border-indigo-400/50 shadow-2xl shadow-indigo-500/20 scale-105'
                                    : 'bg-white/5 border-white/10'
                            }`}
                        >
                            {p.featured && (
                                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-500 border-0">Most popular</Badge>
                            )}
                            <CardContent className="p-6">
                                <h3 className="text-2xl font-bold">{p.name}</h3>
                                <div className="mt-4 flex items-baseline gap-1">
                                    <span className="text-5xl font-bold">£{p.price}</span>
                                    <span className="text-white/60">/month</span>
                                </div>
                                <p className="text-sm text-white/60 mt-1">Up to {p.employees} employees</p>
                                <ul className="mt-6 space-y-2 text-sm">
                                    {p.features.map((f) => (
                                        <li key={f} className="flex items-start gap-2">
                                            <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" /> {f}
                                        </li>
                                    ))}
                                </ul>
                                <Link to="/register" className="block mt-6">
                                    <Button
                                        className={`w-full ${
                                            p.featured
                                                ? 'bg-white text-indigo-700 hover:bg-indigo-50'
                                                : 'bg-white/10 text-white border border-white/20 hover:bg-white/20'
                                        }`}
                                    >
                                        Start {p.name}
                                    </Button>
                                </Link>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </section>

            {/* Compliance */}
            <section id="compliance" className="max-w-7xl mx-auto px-6 py-20 border-t border-white/5">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
                    <div>
                        <Badge className="mb-3 bg-white/10 border border-white/20">Compliance Autopilot</Badge>
                        <h2 className="text-4xl font-bold leading-tight">
                            HMRC, UKVI &amp; GDPR — handled before you noticed.
                        </h2>
                        <p className="mt-4 text-white/70 leading-relaxed">
                            Our compliance score updates in real time as your team grows. Visa expiries, sponsor
                            licence ratings, statutory pay deadlines, RTI cut-offs — all tracked, scored, and queued
                            before they become problems.
                        </p>
                        <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                            {[
                                'Live HMRC sandbox + production SOAP', 'UKVI sponsor licence monitoring',
                                'Right-to-Work share-code lookup', 'GDPR-grade audit log',
                                'P45/P60/P11D auto-generation', '7-year HMRC record retention',
                            ].map((c) => (
                                <div key={c} className="flex items-start gap-2">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-white/80">{c}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                    <Card className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border-white/10">
                        <CardContent className="p-8">
                            <div className="flex items-center gap-3 mb-4">
                                <ShieldCheck className="w-8 h-8 text-emerald-400" />
                                <div>
                                    <p className="text-sm text-white/60">Compliance score</p>
                                    <p className="text-4xl font-bold">96%</p>
                                </div>
                            </div>
                            <div className="space-y-3 text-sm">
                                {[
                                    { label: 'Visa documentation', value: 100, color: 'bg-emerald-400' },
                                    { label: 'Payroll data quality', value: 95, color: 'bg-indigo-400' },
                                    { label: 'Document retention', value: 92, color: 'bg-amber-400' },
                                ].map((b) => (
                                    <div key={b.label}>
                                        <div className="flex justify-between text-white/70 mb-1">
                                            <span>{b.label}</span>
                                            <span>{b.value}%</span>
                                        </div>
                                        <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                            <div className={`h-full ${b.color}`} style={{ width: `${b.value}%` }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </section>

            {/* CTA */}
            <section className="max-w-7xl mx-auto px-6 py-24 border-t border-white/5">
                <Card className="bg-gradient-to-br from-indigo-600 to-purple-700 border-0 overflow-hidden relative">
                    <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,.3),transparent_60%)]" />
                    <CardContent className="p-10 md:p-16 relative">
                        <div className="max-w-2xl">
                            <Star className="w-7 h-7 text-yellow-300 mb-4" />
                            <h2 className="text-3xl md:text-5xl font-bold leading-tight">
                                See it in action — without giving us your email.
                            </h2>
                            <p className="mt-4 text-white/80 text-lg">
                                Click below and you're inside a real RealtouchHR tenant in under 5 seconds.
                                Sample employees, draft pay run, UKVI alerts, Stripe checkout — explore the lot.
                            </p>
                            <Button
                                size="lg"
                                onClick={startSandboxDemo}
                                disabled={loading}
                                className="mt-6 bg-white text-indigo-700 hover:bg-indigo-50 font-bold px-8 py-6 rounded-xl"
                                data-testid="cta-try-demo-btn"
                            >
                                {loading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <Zap className="w-5 h-5 mr-2" />}
                                Launch sandbox demo
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </section>

            {/* Footer */}
            <footer className="border-t border-white/5 py-10 text-sm text-white/50">
                <div className="max-w-7xl mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
                    <p>© 2026 RealtouchHR. Built for UK SMBs.</p>
                    <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Sandbox demos auto-expire after 24h</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
