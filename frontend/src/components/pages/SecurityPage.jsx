import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { ShieldCheck, Smartphone, Copy, Loader2, AlertCircle, Lock, Unlock } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function SecurityPage() {
    const [status, setStatus] = useState({ enabled: false });
    const [loading, setLoading] = useState(true);
    const [setup, setSetup] = useState(null); // { qr_png_base64, secret, otp_uri }
    const [verifyCode, setVerifyCode] = useState('');
    const [backupCodes, setBackupCodes] = useState(null); // list of codes after enable
    const [disableCode, setDisableCode] = useState('');
    const [actionLoading, setActionLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_URL}/api/2fa/status`, auth());
            setStatus(res.data);
        } catch (e) {
            toast.error('Failed to load 2FA status');
        } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const beginSetup = async () => {
        setActionLoading(true);
        try {
            const res = await axios.post(`${API_URL}/api/2fa/setup/begin`, {}, auth());
            setSetup(res.data);
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed to start setup');
        } finally { setActionLoading(false); }
    };

    const verifySetup = async (e) => {
        e.preventDefault();
        setActionLoading(true);
        try {
            const res = await axios.post(`${API_URL}/api/2fa/setup/verify`, { code: verifyCode.trim() }, auth());
            setBackupCodes(res.data.backup_codes);
            setSetup(null);
            setVerifyCode('');
            toast.success('2FA enabled successfully');
            load();
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Invalid code');
        } finally { setActionLoading(false); }
    };

    const disable = async (e) => {
        e.preventDefault();
        setActionLoading(true);
        try {
            await axios.post(`${API_URL}/api/2fa/disable`, { code: disableCode.trim() }, auth());
            toast.success('2FA disabled');
            setDisableCode('');
            setBackupCodes(null);
            load();
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed');
        } finally { setActionLoading(false); }
    };

    const copyBackup = () => {
        if (!backupCodes) return;
        navigator.clipboard.writeText(backupCodes.join('\n'));
        toast.success('Backup codes copied');
    };

    return (
        <div className="space-y-6 max-w-3xl" data-testid="security-page">
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Account Security</h1>
                <p className="text-muted-foreground mt-1">Strengthen sign-in with two-factor authentication (TOTP).</p>
            </div>

            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2"><ShieldCheck className="w-5 h-5" />Two-Factor Authentication</CardTitle>
                        <CardDescription>Time-based one-time passwords from your authenticator app.</CardDescription>
                    </div>
                    {!loading && (
                        <Badge variant={status.enabled ? 'default' : 'outline'} className={status.enabled ? 'bg-emerald-600' : ''} data-testid="2fa-status-badge">
                            {status.enabled ? <><Lock className="w-3 h-3 mr-1" />Enabled</> : <><Unlock className="w-3 h-3 mr-1" />Disabled</>}
                        </Badge>
                    )}
                </CardHeader>
                <CardContent className="space-y-4">
                    {loading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : status.enabled ? (
                        <>
                            <Alert>
                                <ShieldCheck className="h-4 w-4" />
                                <AlertDescription>
                                    2FA is active. {status.backup_codes_remaining > 0 && `You have ${status.backup_codes_remaining} backup code${status.backup_codes_remaining === 1 ? '' : 's'} remaining.`}
                                    {status.enrolled_at && ` Enrolled on ${new Date(status.enrolled_at).toLocaleDateString('en-GB')}.`}
                                </AlertDescription>
                            </Alert>
                            <form onSubmit={disable} className="space-y-3">
                                <Label htmlFor="disable-code">To disable, enter a current 6-digit code or backup code</Label>
                                <Input
                                    id="disable-code"
                                    value={disableCode}
                                    onChange={(e) => setDisableCode(e.target.value)}
                                    placeholder="000000"
                                    required
                                    data-testid="input-disable-2fa-code"
                                />
                                <Button type="submit" variant="destructive" disabled={actionLoading} data-testid="disable-2fa-btn">
                                    Disable 2FA
                                </Button>
                            </form>
                        </>
                    ) : setup ? (
                        <>
                            <Alert>
                                <Smartphone className="h-4 w-4" />
                                <AlertDescription>
                                    Scan the QR code with Google Authenticator, 1Password, Authy, or any TOTP app. Then enter the 6-digit code below to confirm.
                                </AlertDescription>
                            </Alert>
                            <div className="flex flex-col md:flex-row gap-6 items-start">
                                <div className="bg-white p-3 rounded-lg border">
                                    <img src={`data:image/png;base64,${setup.qr_png_base64}`} alt="QR code" className="w-48 h-48" data-testid="2fa-qr-code" />
                                </div>
                                <div className="flex-1 space-y-3">
                                    <div>
                                        <Label className="text-xs text-muted-foreground">Or enter this secret manually:</Label>
                                        <div className="flex items-center gap-2 mt-1">
                                            <code className="px-2 py-1 rounded bg-muted text-sm break-all" data-testid="2fa-secret">{setup.secret}</code>
                                            <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(setup.secret); toast.success('Copied'); }}>
                                                <Copy className="w-3 h-3" />
                                            </Button>
                                        </div>
                                    </div>
                                    <form onSubmit={verifySetup} className="space-y-3">
                                        <Label htmlFor="verify-code">Enter 6-digit code from app</Label>
                                        <Input
                                            id="verify-code"
                                            value={verifyCode}
                                            onChange={(e) => setVerifyCode(e.target.value)}
                                            placeholder="000000"
                                            inputMode="numeric"
                                            required
                                            data-testid="input-verify-2fa-code"
                                        />
                                        <div className="flex gap-2">
                                            <Button type="submit" disabled={actionLoading} data-testid="verify-2fa-setup-btn">
                                                Verify & Enable
                                            </Button>
                                            <Button type="button" variant="outline" onClick={() => setSetup(null)}>Cancel</Button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            <Alert>
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>
                                    Recommended for owner and admin accounts. Adds a second sign-in step using a code from your phone.
                                </AlertDescription>
                            </Alert>
                            <Button onClick={beginSetup} disabled={actionLoading} data-testid="enable-2fa-btn">
                                <ShieldCheck className="w-4 h-4 mr-2" />
                                Enable Two-Factor Authentication
                            </Button>
                        </>
                    )}
                </CardContent>
            </Card>

            {backupCodes && (
                <Card className="border-emerald-200 bg-emerald-50/50 dark:bg-emerald-950/20">
                    <CardHeader>
                        <CardTitle className="text-emerald-700 dark:text-emerald-300">Save your backup codes</CardTitle>
                        <CardDescription>Each can be used once if you lose access to your authenticator app. These are shown only once.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-2 font-mono text-sm" data-testid="backup-codes">
                            {backupCodes.map((c, i) => (
                                <div key={i} className="p-2 rounded bg-card border text-center">{c}</div>
                            ))}
                        </div>
                        <Button onClick={copyBackup} variant="outline" size="sm" data-testid="copy-backup-codes-btn">
                            <Copy className="w-3 h-3 mr-2" />Copy all
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
