import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { ShieldCheck, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function TrustVerifyPage() {
    const { badgeId } = useParams();
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await axios.get(`${API_URL}/api/trust-badge/${badgeId}/verify`);
                setData(res.data);
            } catch (e) {
                setError(e.response?.data?.detail || 'Badge not found');
            } finally {
                setLoading(false);
            }
        })();
    }, [badgeId]);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-200">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="min-h-screen bg-rose-950 text-rose-100 flex items-center justify-center p-6">
                <div className="text-center max-w-md">
                    <XCircle className="w-12 h-12 mx-auto mb-4" />
                    <h1 className="text-2xl font-bold">Trust badge not valid</h1>
                    <p className="mt-2 opacity-80">Badge ID <code className="bg-rose-900 px-2 py-0.5 rounded">{badgeId}</code> does not match any active RealtouchHR company.</p>
                </div>
            </div>
        );
    }

    const att = data.attestations || {};
    const rows = [
        ['UK GDPR / Data Protection Act 2018 compliant', att.gdpr_compliant, 'Article 15 export · Article 17 erasure'],
        ['Two-Factor Authentication (owner)', att.owner_2fa_enabled, att.owner_2fa_enabled ? 'TOTP enrolled' : 'Not enrolled'],
        ['Immutable audit log', att.audit_logged, `${att.audit_entries_count || 0} entries`],
        ['HMRC RTI 2025-26 configured', att.hmrc_rti_configured, ''],
        ['UKVI Sponsor Licence tracking', att.ukvi_sponsor_licence, ''],
        ['Pension Auto-Enrolment scheme', att.pension_auto_enrolment, ''],
        ['Active subscription', att.subscription_active, ''],
    ];

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 py-12 px-4" data-testid="trust-verify-page">
            <div className="max-w-2xl mx-auto">
                <div className="inline-block px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-[11px] tracking-[0.2em] uppercase font-medium">
                    RealtouchHR · Verified
                </div>
                <h1 className="text-4xl font-bold mt-4 font-['Plus_Jakarta_Sans']">{data.company_name}</h1>
                <p className="text-slate-400 mt-2">This company is an active customer of RealtouchHR — running UK payroll, HR, and compliance on a fully audited platform.</p>

                <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-7 text-center">
                    <img
                        src={`${API_URL}/api/trust-badge/${badgeId}/badge.svg`}
                        alt="RealtouchHR Trust Badge"
                        className="mx-auto max-w-full"
                        data-testid="trust-badge-svg"
                    />
                    <div className="mt-3 text-sm text-slate-400">
                        Verified level: <strong className="text-amber-400">{data.verified_level?.toUpperCase()}</strong>
                        {' · '}Badge ID <code className="text-slate-300">{badgeId}</code>
                    </div>
                </div>

                <div className="mt-6 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                    <div className="p-4 border-b border-slate-800 font-semibold flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-indigo-400" />
                        Compliance attestations
                    </div>
                    <ul className="divide-y divide-slate-800">
                        {rows.map(([label, ok, note]) => (
                            <li key={label} className="flex items-center justify-between px-4 py-3">
                                <span>
                                    {label}
                                    {note && <span className="text-xs text-slate-500 ml-2">· {note}</span>}
                                </span>
                                {ok
                                    ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                    : <XCircle className="w-5 h-5 text-rose-400" />}
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="mt-6 bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Regulator alignment</p>
                    <div className="flex flex-wrap gap-2">
                        {(data.platform?.regulator_alignment || []).map(r => (
                            <span key={r} className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300">{r}</span>
                        ))}
                    </div>
                </div>

                <p className="text-center text-xs text-slate-500 mt-8">
                    Verified live by <a href="/" className="text-indigo-400">RealtouchHR</a>. Attestations re-checked every page load. Companies cannot self-issue or forge badges.
                </p>
            </div>
        </div>
    );
}
