import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription } from '../ui/alert';
import { toast } from 'sonner';
import { ShieldCheck, Copy, ExternalLink, Loader2, Award, Code2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }, withCredentials: true });

export default function TrustBadgePage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    const load = async () => {
        try {
            const res = await axios.get(`${API_URL}/api/trust-badge/me`, auth());
            setData(res.data);
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed to load badge');
        } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const copy = (text, label) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied`);
    };

    if (loading) {
        return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>;
    }
    if (!data) return <p className="p-8">Could not load badge.</p>;

    const att = data.attestations || {};
    const levelColor = {
        gold: 'bg-amber-100 text-amber-800 border-amber-300',
        silver: 'bg-slate-100 text-slate-800 border-slate-300',
        bronze: 'bg-orange-100 text-orange-800 border-orange-300',
    }[data.verified_level] || 'bg-slate-100 text-slate-800';

    return (
        <div className="space-y-6 max-w-4xl" data-testid="trust-badge-page">
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Compliance Trust Badge</h1>
                <p className="text-muted-foreground mt-1">Embed your live verification badge on your website to signal regulatory trust to customers and partners.</p>
            </div>

            <Alert>
                <ShieldCheck className="h-4 w-4" />
                <AlertDescription>
                    Your badge is auto-issued and signed against your company ID. Visitors who click it land on a public verification page that re-checks your live compliance status — so the badge can't be faked.
                </AlertDescription>
            </Alert>

            <Card>
                <CardHeader className="flex flex-row items-start justify-between gap-3">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Award className="w-5 h-5 text-amber-500" />
                            Your badge
                        </CardTitle>
                        <CardDescription>Live preview — what visitors will see.</CardDescription>
                    </div>
                    <Badge className={levelColor} data-testid="trust-badge-level">{(data.verified_level || '').toUpperCase()} TIER</Badge>
                </CardHeader>
                <CardContent>
                    <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-6 border flex items-center justify-center">
                        <a href={data.verify_url} target="_blank" rel="noopener noreferrer">
                            <img
                                src={data.badge_svg_url}
                                alt="Compliance Trust Badge"
                                className="hover:scale-105 transition-transform"
                                data-testid="trust-badge-preview"
                            />
                        </a>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                        <a href={data.verify_url} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-600 hover:underline inline-flex items-center gap-1" data-testid="open-verify-page-link">
                            Open verification page <ExternalLink className="w-3 h-3" />
                        </a>
                        <span className="text-xs text-muted-foreground">Badge ID: <code>{data.badge_id}</code></span>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Code2 className="w-5 h-5" />Embed snippets</CardTitle>
                    <CardDescription>Paste one of these into your website or README.</CardDescription>
                </CardHeader>
                <CardContent>
                    <Tabs defaultValue="html">
                        <TabsList>
                            <TabsTrigger value="html">HTML</TabsTrigger>
                            <TabsTrigger value="markdown">Markdown</TabsTrigger>
                            <TabsTrigger value="image">Image URL</TabsTrigger>
                            <TabsTrigger value="link">Verify URL</TabsTrigger>
                        </TabsList>
                        <TabsContent value="html" className="space-y-2">
                            <pre className="text-xs bg-muted rounded p-3 overflow-x-auto" data-testid="embed-html">{data.embed_html}</pre>
                            <Button size="sm" variant="outline" onClick={() => copy(data.embed_html, 'HTML embed')} data-testid="copy-embed-html"><Copy className="w-3 h-3 mr-1" />Copy HTML</Button>
                        </TabsContent>
                        <TabsContent value="markdown" className="space-y-2">
                            <pre className="text-xs bg-muted rounded p-3 overflow-x-auto" data-testid="embed-markdown">{data.embed_markdown}</pre>
                            <Button size="sm" variant="outline" onClick={() => copy(data.embed_markdown, 'Markdown')} data-testid="copy-embed-markdown"><Copy className="w-3 h-3 mr-1" />Copy Markdown</Button>
                        </TabsContent>
                        <TabsContent value="image" className="space-y-2">
                            <pre className="text-xs bg-muted rounded p-3 overflow-x-auto" data-testid="embed-image">{data.badge_svg_url}</pre>
                            <Button size="sm" variant="outline" onClick={() => copy(data.badge_svg_url, 'Image URL')}><Copy className="w-3 h-3 mr-1" />Copy URL</Button>
                        </TabsContent>
                        <TabsContent value="link" className="space-y-2">
                            <pre className="text-xs bg-muted rounded p-3 overflow-x-auto" data-testid="embed-link">{data.verify_url}</pre>
                            <Button size="sm" variant="outline" onClick={() => copy(data.verify_url, 'Verify URL')}><Copy className="w-3 h-3 mr-1" />Copy URL</Button>
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Live compliance attestations</CardTitle>
                    <CardDescription>These checks determine your badge tier. Improve them to upgrade.</CardDescription>
                </CardHeader>
                <CardContent>
                    <ul className="space-y-2 text-sm" data-testid="attestation-list">
                        <AttRow label="UK GDPR compliant (Article 15/17)" ok={att.gdpr_compliant} note="Self-service data export + erasure" />
                        <AttRow label="Owner 2FA enabled" ok={att.owner_2fa_enabled} note={att.owner_2fa_enabled ? 'TOTP active' : 'Enable in /security for Silver/Gold'} />
                        <AttRow label="Audit log active" ok={att.audit_logged} note={`${att.audit_entries_count || 0} entries`} />
                        <AttRow label="HMRC RTI configured" ok={att.hmrc_rti_configured} note={att.hmrc_rti_configured ? '' : 'Add PAYE reference in Settings'} />
                        <AttRow label="UKVI Sponsor Licence tracked" ok={att.ukvi_sponsor_licence} note={att.ukvi_sponsor_licence ? '' : 'Optional (only if you sponsor visa holders)'} />
                        <AttRow label="Pension Auto-Enrolment scheme" ok={att.pension_auto_enrolment} note={att.pension_auto_enrolment ? '' : 'Set one up in /pensions'} />
                        <AttRow label="Active subscription" ok={att.subscription_active} note={att.subscription_active ? '' : 'Subscribe to unlock Gold tier'} />
                    </ul>
                    <div className="mt-4 p-3 rounded-lg bg-muted text-xs text-muted-foreground">
                        Tiers: <strong>Bronze</strong> (default) · <strong>Silver</strong> (3+ checks) · <strong>Gold</strong> (5+ checks). Enabling 2FA on the owner account is worth 2 points.
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

function AttRow({ label, ok, note }) {
    return (
        <li className="flex items-center justify-between p-3 rounded-lg border">
            <div>
                <p className="font-medium">{label}</p>
                {note && <p className="text-xs text-muted-foreground">{note}</p>}
            </div>
            <Badge className={ok ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}>
                {ok ? 'PASS' : 'PENDING'}
            </Badge>
        </li>
    );
}
