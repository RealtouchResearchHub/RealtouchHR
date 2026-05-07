import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { Building2, UserCheck, Loader2, AlertCircle, Mail } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function InviteAcceptPage() {
    const { token } = useParams();
    const navigate = useNavigate();
    const [invite, setInvite] = useState(null);
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        (async () => {
            try {
                const res = await axios.get(`${API_URL}/api/users/invite/${token}`);
                setInvite(res.data);
            } catch (err) {
                setError(err.response?.data?.detail || 'Invitation not found');
            } finally {
                setLoading(false);
            }
        })();
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            toast.error('Passwords do not match');
            return;
        }
        if (password.length < 8) {
            toast.error('Password must be at least 8 characters');
            return;
        }
        setSubmitting(true);
        try {
            const res = await axios.post(`${API_URL}/api/users/invite/accept`, {
                invite_token: token,
                password,
            });
            localStorage.setItem('token', res.data.token);
            toast.success(`Welcome aboard, ${res.data.user.name}!`);
            // Hard reload so AuthContext picks up new session
            window.location.href = '/dashboard';
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Could not accept invitation');
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-950 via-indigo-950 to-purple-950">
                <Loader2 className="w-10 h-10 text-white animate-spin" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-950 via-indigo-950 to-purple-950 p-4">
                <Card className="max-w-md w-full bg-white">
                    <CardContent className="p-8 text-center">
                        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
                        <h2 className="text-xl font-bold">Invitation unavailable</h2>
                        <p className="text-muted-foreground mt-2 text-sm">{error}</p>
                        <Button className="mt-6" onClick={() => navigate('/')}>Back to home</Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-950 via-indigo-950 to-purple-950 p-4" data-testid="invite-accept-page">
            <Card className="max-w-lg w-full bg-white shadow-2xl">
                <CardHeader className="text-center pb-2">
                    <div className="inline-flex items-center justify-center w-16 h-16 mx-auto bg-gradient-to-br from-indigo-500 to-purple-500 rounded-2xl text-white mb-4">
                        <UserCheck className="w-8 h-8" />
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900">You're invited!</h1>
                    <p className="text-slate-600 text-sm mt-1">
                        <strong>{invite.invited_by_name}</strong> invited you to join <strong>{invite.company_name}</strong>
                    </p>
                </CardHeader>
                <CardContent className="pt-4">
                    <div className="bg-slate-50 rounded-lg p-4 mb-6 space-y-2 text-sm">
                        <Row icon={<Mail className="w-4 h-4" />} label="Email" value={invite.email} />
                        <Row icon={<UserCheck className="w-4 h-4" />} label="Your role" value={
                            <Badge className="bg-indigo-100 text-indigo-700 border-indigo-200">
                                {invite.role?.replace(/_/g, ' ').toUpperCase()}
                            </Badge>
                        } />
                        <Row icon={<Building2 className="w-4 h-4" />} label="Company" value={invite.company_name} />
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <Label>Create a password</Label>
                            <Input
                                type="password"
                                placeholder="At least 8 characters"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                minLength={8}
                                data-testid="invite-password"
                            />
                        </div>
                        <div>
                            <Label>Confirm password</Label>
                            <Input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                minLength={8}
                                data-testid="invite-confirm-password"
                            />
                        </div>
                        <Button
                            type="submit"
                            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white"
                            disabled={submitting}
                            data-testid="accept-invite-btn"
                        >
                            {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                            Accept &amp; create account
                        </Button>
                    </form>

                    <p className="text-xs text-center text-muted-foreground mt-4">
                        By accepting, you agree to RealtouchHR's terms of service.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}

function Row({ icon, label, value }) {
    return (
        <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-slate-500">{icon} {label}</span>
            <span className="font-medium text-slate-900">{value}</span>
        </div>
    );
}
