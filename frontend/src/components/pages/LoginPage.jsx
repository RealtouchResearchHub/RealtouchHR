import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Separator } from '../ui/separator';
import { CheckCircle2, ShieldCheck, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

function ForgotPasswordForm({ onBack }) {
    const [email, setEmail] = useState('');
    const [sent, setSent] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await axios.post(`${API_URL}/api/auth/forgot-password`, { email });
            setSent(true);
        } catch {
            // Always show success to prevent email enumeration
            setSent(true);
        } finally {
            setLoading(false);
        }
    };

    if (sent) {
        return (
            <div className="text-center space-y-4">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
                <h3 className="font-semibold text-lg">Check your email</h3>
                <p className="text-sm text-muted-foreground">
                    If an account exists for <strong>{email}</strong>, a password reset link has been sent.
                </p>
                <Button variant="ghost" onClick={onBack} className="w-full">Back to sign in</Button>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                    Enter your email and we'll send you a reset link.
                </p>
                <Label htmlFor="reset-email">Email</Label>
                <Input
                    id="reset-email"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    autoFocus
                />
            </div>
            <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700" disabled={loading}>
                {loading ? 'Sending…' : 'Send reset link'}
                <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={onBack}>Back to sign in</Button>
        </form>
    );
}

export default function LoginPage() {
    const navigate = useNavigate();
    const { login, verifyTwoFactor, loginWithGoogle } = useAuth();
    const [formData, setFormData] = useState({ email: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [twoFactorState, setTwoFactorState] = useState(null);
    const [twoFactorCode, setTwoFactorCode] = useState('');
    const [showForgot, setShowForgot] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const result = await login(formData.email, formData.password);
            if (result?.two_factor_required) {
                setTwoFactorState({ pending_token: result.pending_token });
                toast.info('Two-factor authentication required');
            } else {
                toast.success('Welcome back!');
                navigate('/dashboard');
            }
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyTwoFactor = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await verifyTwoFactor(twoFactorState.pending_token, twoFactorCode.trim());
            toast.success('Welcome back!');
            navigate('/dashboard');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Invalid code');
        } finally {
            setLoading(false);
        }
    };

    const features = [
        'Compliance Autopilot with confidence scoring',
        'Guided payroll flow for UK businesses',
        'AI-powered HR assistant',
        'Immutable audit trail for GDPR',
    ];

    return (
        <div className="min-h-screen bg-background flex" data-testid="login-page">
            {/* Left Side - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-indigo-600 to-purple-700 p-12 flex-col justify-between text-white">
                <div>
                    <img src="/logo-dark.png" alt="RealtouchHR" className="h-24 w-auto" />
                </div>

                <div className="space-y-8">
                    <div>
                        <h1 className="text-4xl lg:text-5xl font-bold font-['Plus_Jakarta_Sans'] leading-tight">
                            UK Payroll, HR<br />and Compliance
                        </h1>
                        <p className="mt-4 text-lg text-white/80 max-w-md">
                            The HR & Payroll platform that gives you peace of mind with automated compliance checks and audit-ready records.
                        </p>
                    </div>

                    <div className="space-y-3">
                        {features.map((feature, index) => (
                            <div key={index} className="flex items-center gap-3">
                                <CheckCircle2 className="w-5 h-5 text-emerald-300 flex-shrink-0" />
                                <span className="text-white/90">{feature}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <p className="text-white/60 text-sm">© 2026 RealtouchHR. Built for UK SMBs.</p>
            </div>

            {/* Right Side - Login Form */}
            <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
                <Card className="w-full max-w-md border-0 shadow-none lg:shadow-lg lg:border">
                    <CardHeader className="text-center space-y-2">
                        {/* Logo shown on all screen sizes at top of form */}
                        <div className="flex items-center justify-center mb-2">
                            <img src="/logo-white.png" alt="RealtouchHR" className="h-14 w-auto block dark:hidden" />
                            <img src="/logo-dark.png" alt="RealtouchHR" className="h-14 w-auto hidden dark:block" />
                        </div>
                        {!showForgot && (
                            <>
                                <CardTitle className="text-2xl font-bold font-['Plus_Jakarta_Sans']">Welcome back</CardTitle>
                                <CardDescription>Sign in to your account to continue</CardDescription>
                            </>
                        )}
                        {showForgot && (
                            <CardTitle className="text-2xl font-bold font-['Plus_Jakarta_Sans']">Reset your password</CardTitle>
                        )}
                    </CardHeader>

                    <CardContent className="space-y-6">
                        {showForgot ? (
                            <ForgotPasswordForm onBack={() => setShowForgot(false)} />
                        ) : twoFactorState ? (
                            <form onSubmit={handleVerifyTwoFactor} className="space-y-4" data-testid="2fa-verify-form">
                                <div className="flex items-center gap-2 p-3 rounded-lg bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-900">
                                    <ShieldCheck className="w-5 h-5 text-indigo-600" />
                                    <p className="text-sm text-indigo-900 dark:text-indigo-100">
                                        Enter the 6-digit code from your authenticator app, or a backup code.
                                    </p>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="2fa-code">Authentication code</Label>
                                    <Input
                                        id="2fa-code"
                                        type="text"
                                        autoComplete="one-time-code"
                                        inputMode="numeric"
                                        value={twoFactorCode}
                                        onChange={e => setTwoFactorCode(e.target.value)}
                                        placeholder="000000"
                                        required
                                        autoFocus
                                        data-testid="input-2fa-code"
                                    />
                                </div>
                                <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700" disabled={loading} data-testid="2fa-verify-submit-btn">
                                    {loading ? 'Verifying...' : 'Verify & Sign in'}
                                    <ArrowRight className="w-4 h-4 ml-2" />
                                </Button>
                                <Button type="button" variant="ghost" className="w-full" onClick={() => { setTwoFactorState(null); setTwoFactorCode(''); }} data-testid="2fa-cancel-btn">
                                    Cancel
                                </Button>
                            </form>
                        ) : (
                            <>
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="email">Email</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            value={formData.email}
                                            onChange={e => setFormData({ ...formData, email: e.target.value })}
                                            placeholder="you@company.com"
                                            required
                                            data-testid="input-login-email"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <Label htmlFor="password">Password</Label>
                                            <button
                                                type="button"
                                                className="text-xs text-indigo-600 hover:underline"
                                                onClick={() => setShowForgot(true)}
                                            >
                                                Forgot password?
                                            </button>
                                        </div>
                                        <Input
                                            id="password"
                                            type="password"
                                            value={formData.password}
                                            onChange={e => setFormData({ ...formData, password: e.target.value })}
                                            placeholder="••••••••"
                                            required
                                            data-testid="input-login-password"
                                        />
                                    </div>
                                    <Button
                                        type="submit"
                                        className="w-full bg-indigo-600 hover:bg-indigo-700"
                                        disabled={loading}
                                        data-testid="login-submit-btn"
                                    >
                                        {loading ? 'Signing in...' : 'Sign in'}
                                        <ArrowRight className="w-4 h-4 ml-2" />
                                    </Button>
                                </form>

                                <div className="relative">
                                    <div className="absolute inset-0 flex items-center">
                                        <Separator />
                                    </div>
                                    <div className="relative flex justify-center text-xs uppercase">
                                        <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
                                    </div>
                                </div>

                                <Button variant="outline" className="w-full" onClick={loginWithGoogle} data-testid="google-login-btn">
                                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                                        <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                        <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                        <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                        <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                    </svg>
                                    Sign in with Google
                                </Button>

                                <p className="text-center text-sm text-muted-foreground">
                                    Don't have an account?{' '}
                                    <Link to="/register" className="text-indigo-600 hover:underline font-medium" data-testid="register-link">
                                        Sign up
                                    </Link>
                                </p>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
