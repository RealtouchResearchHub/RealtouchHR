import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function ResetPasswordPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [loading, setLoading] = useState(false);
    const [done, setDone] = useState(false);

    useEffect(() => {
        if (!token) navigate('/login');
    }, [token, navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password !== confirm) {
            toast.error('Passwords do not match');
            return;
        }
        if (password.length < 8) {
            toast.error('Password must be at least 8 characters');
            return;
        }
        setLoading(true);
        try {
            await axios.post(`${API_URL}/api/auth/reset-password`, { token, password });
            setDone(true);
            setTimeout(() => navigate('/login'), 3000);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Reset failed — the link may have expired');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-6">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <div className="flex items-center justify-center mb-4">
                        <img src="/logo-white.png" alt="RealtouchHR" className="h-12 w-auto block dark:hidden" />
                        <img src="/logo-dark.png" alt="RealtouchHR" className="h-12 w-auto hidden dark:block" />
                    </div>
                    <CardTitle className="text-2xl font-bold font-['Plus_Jakarta_Sans']">Set new password</CardTitle>
                    <CardDescription>Choose a strong password for your account</CardDescription>
                </CardHeader>
                <CardContent>
                    {done ? (
                        <div className="text-center space-y-4">
                            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
                            <p className="font-semibold">Password updated!</p>
                            <p className="text-sm text-muted-foreground">Redirecting to sign in…</p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label>New password</Label>
                                <Input
                                    type="password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="Minimum 8 characters"
                                    required
                                    minLength={8}
                                    autoFocus
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Confirm password</Label>
                                <Input
                                    type="password"
                                    value={confirm}
                                    onChange={e => setConfirm(e.target.value)}
                                    placeholder="Repeat new password"
                                    required
                                />
                            </div>
                            <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700" disabled={loading}>
                                {loading ? 'Updating…' : 'Update password'}
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                            <p className="text-center text-sm">
                                <Link to="/login" className="text-indigo-600 hover:underline">Back to sign in</Link>
                            </p>
                        </form>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
