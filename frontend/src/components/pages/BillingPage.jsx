import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import {
    CreditCard, CheckCircle2, Sparkles, Zap, Building2,
    Loader2, AlertCircle, Receipt, Plus, Crown, Download, Infinity as InfinityIcon
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PLAN_STYLES = {
    starter: {
        icon: Zap,
        gradient: 'from-blue-500 to-cyan-500',
        accent: 'bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300',
    },
    professional: {
        icon: Sparkles,
        gradient: 'from-indigo-500 to-purple-500',
        accent: 'bg-indigo-50 dark:bg-indigo-950/30 text-indigo-700 dark:text-indigo-300',
        featured: true,
    },
    enterprise: {
        icon: Crown,
        gradient: 'from-amber-500 to-orange-500',
        accent: 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300',
    },
};

export default function BillingPage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const [billing, setBilling] = useState(null);
    const [usage, setUsage] = useState(null);
    const [loading, setLoading] = useState(true);
    const [checkoutLoading, setCheckoutLoading] = useState(null);
    const [pollStatus, setPollStatus] = useState(null);

    const fetchBilling = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${API_URL}/api/payments/billing`, {
                headers: { Authorization: `Bearer ${token}` },
                withCredentials: true,
            });
            setBilling(res.data);
            const usageRes = await axios.get(`${API_URL}/api/payments/usage/this-month`, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
            }).catch(() => ({ data: null }));
            setUsage(usageRes.data);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to load billing info');
        } finally {
            setLoading(false);
        }
    };

    const fetchReceipt = async (transactionId) => {
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${API_URL}/api/payments/transactions/${transactionId}/receipt`, {
                headers: { Authorization: `Bearer ${token}` }, withCredentials: true,
            });
            if (res.data?.receipt_url) {
                window.open(res.data.receipt_url, '_blank', 'noopener');
            } else {
                toast.info('Receipt not yet available');
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Receipt unavailable');
        }
    };

    useEffect(() => {
        fetchBilling();
    }, []);

    // Poll payment status after returning from Stripe
    useEffect(() => {
        const sessionId = searchParams.get('session_id');
        const status = searchParams.get('status');
        if (!sessionId) return;

        if (status === 'cancelled') {
            toast.error('Checkout cancelled');
            setSearchParams({});
            return;
        }

        const poll = async (attempts = 0) => {
            if (attempts >= 6) {
                setPollStatus('timeout');
                toast.warning('Payment status check timed out. Please refresh.');
                return;
            }
            try {
                const token = localStorage.getItem('token');
                const res = await axios.post(
                    `${API_URL}/api/payments/checkout/status`,
                    { session_id: sessionId, origin_url: window.location.origin },
                    { headers: { Authorization: `Bearer ${token}` }, withCredentials: true }
                );
                if (res.data.payment_status === 'paid') {
                    setPollStatus('paid');
                    toast.success('Payment successful! Your plan is now active.');
                    setSearchParams({});
                    fetchBilling();
                    return;
                }
                if (res.data.status === 'expired') {
                    setPollStatus('expired');
                    toast.error('Payment session expired.');
                    return;
                }
                setPollStatus('pending');
                setTimeout(() => poll(attempts + 1), 2000);
            } catch (err) {
                setPollStatus('error');
                toast.error('Error verifying payment.');
            }
        };
        setPollStatus('pending');
        poll();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams.get('session_id')]);

    const handleSubscribe = async (planId) => {
        setCheckoutLoading(planId);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(
                `${API_URL}/api/payments/checkout/subscription`,
                { plan_id: planId, origin_url: window.location.origin },
                { headers: { Authorization: `Bearer ${token}` }, withCredentials: true }
            );
            if (res.data?.checkout_url) {
                window.location.href = res.data.checkout_url;
            } else {
                toast.error('No checkout URL received');
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to start checkout');
        } finally {
            setCheckoutLoading(null);
        }
    };

    const handleAddon = async (addonId) => {
        setCheckoutLoading(addonId);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(
                `${API_URL}/api/payments/checkout/addon`,
                { addon_id: addonId, origin_url: window.location.origin, quantity: 1 },
                { headers: { Authorization: `Bearer ${token}` }, withCredentials: true }
            );
            if (res.data?.checkout_url) {
                window.location.href = res.data.checkout_url;
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to start checkout');
        } finally {
            setCheckoutLoading(null);
        }
    };

    const handleManageSubscription = async () => {
        setCheckoutLoading('portal');
        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(
                `${API_URL}/api/payments/portal`,
                { return_url: `${window.location.origin}/billing` },
                { headers: { Authorization: `Bearer ${token}` }, withCredentials: true }
            );
            if (res.data?.portal_url) {
                window.location.href = res.data.portal_url;
            }
        } catch (err) {
            toast.error(
                err.response?.data?.detail ||
                'Customer portal unavailable — complete a subscription checkout first'
            );
        } finally {
            setCheckoutLoading(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    const currentPlanId = billing?.current_plan?.id || null;

    return (
        <div className="space-y-8" data-testid="billing-page">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Billing & Subscription</h1>
                <p className="text-muted-foreground mt-1">
                    Manage your RealtouchHR plan, add-ons and payment history.
                </p>
            </div>

            {/* Poll status banner */}
            {pollStatus === 'pending' && (
                <Card className="border-indigo-200 bg-indigo-50 dark:bg-indigo-950/30">
                    <CardContent className="p-4 flex items-center gap-3">
                        <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                        <p className="text-sm text-indigo-900 dark:text-indigo-100">
                            Verifying your payment with Stripe…
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Current plan */}
            <Card className="overflow-hidden" data-testid="current-plan-card">
                <div className={`h-2 bg-gradient-to-r ${
                    currentPlanId
                        ? PLAN_STYLES[currentPlanId]?.gradient || 'from-indigo-500 to-purple-500'
                        : 'from-slate-300 to-slate-400'
                }`} />
                <CardContent className="p-6">
                    <div className="flex items-start justify-between flex-wrap gap-4">
                        <div>
                            <p className="text-sm text-muted-foreground">Current Plan</p>
                            <h2 className="text-2xl font-bold mt-1">
                                {billing?.current_plan?.name || 'No active subscription'}
                            </h2>
                            <p className="text-sm text-muted-foreground mt-1">
                                Employee limit:{' '}
                                <span className="font-semibold">
                                    {billing?.employee_limit === -1 ? 'Unlimited' : billing?.employee_limit}
                                </span>
                            </p>
                        </div>
                        <Badge
                            variant="outline"
                            className={billing?.subscription_active
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/30'
                                : 'bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-900/30'}
                        >
                            {billing?.subscription_active ? 'ACTIVE' : 'INACTIVE'}
                        </Badge>
                    </div>
                    {billing?.subscription_active && (
                        <div className="mt-4 pt-4 border-t flex justify-end">
                            <Button
                                variant="outline"
                                onClick={handleManageSubscription}
                                disabled={checkoutLoading === 'portal'}
                                data-testid="manage-subscription-btn"
                            >
                                {checkoutLoading === 'portal' ? (
                                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Opening…</>
                                ) : (
                                    <>Manage subscription &amp; payment methods <CreditCard className="w-4 h-4 ml-2" /></>
                                )}
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Download usage / bulk pass status */}
            {usage && (
                <Card data-testid="download-usage-card">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                            <CardTitle className="flex items-center gap-2 text-base">
                                <Download className="w-4 h-4 text-indigo-600" />
                                Download usage — {usage.month}
                            </CardTitle>
                            {usage.bulk_downloads_active && (
                                <Badge className="bg-indigo-600 text-white">
                                    <InfinityIcon className="w-3 h-3 mr-1" /> Unlimited until {(usage.bulk_downloads_until || '').slice(0, 10)}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/30 border">
                                <p className="text-xs text-muted-foreground">Plan quota</p>
                                <p className="font-bold text-lg">
                                    {usage.quota === -1 ? '∞' : usage.quota || 0} / month
                                </p>
                            </div>
                            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/30 border">
                                <p className="text-xs text-muted-foreground">Used this month</p>
                                <p className="font-bold text-lg">{usage.used_this_month}</p>
                            </div>
                            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/30 border">
                                <p className="text-xs text-muted-foreground">Remaining free</p>
                                <p className="font-bold text-lg">
                                    {usage.remaining === -1 ? '∞' : usage.remaining}
                                </p>
                            </div>
                        </div>
                        {!usage.bulk_downloads_active && usage.quota !== -1 && (
                            <p className="text-xs text-muted-foreground mt-3">
                                After your free quota, each payslip download costs £{usage.price_per_download} —
                                or buy <strong>unlimited 30 days for £{usage.bulk_offer_price}</strong>.
                            </p>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Plans */}
            <div>
                <h2 className="text-2xl font-bold mb-2">Choose a plan</h2>
                <p className="text-muted-foreground mb-6 text-sm">
                    All plans are billed in GBP. Test keys are active — use Stripe test cards like
                    <code className="mx-1 px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-xs whitespace-nowrap">
                        4242 4242 4242 4242
                    </code>
                </p>
                {(!billing?.available_plans || Object.keys(billing.available_plans).length === 0) ? (
                    <Card className="border-amber-200 bg-amber-50/40 dark:bg-amber-950/20">
                        <CardContent className="p-6 text-center">
                            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-amber-600" />
                            <p className="font-medium">Plans could not load.</p>
                            <Button onClick={() => { setLoading(true); fetchBilling(); }} variant="outline" size="sm" className="mt-3">Retry</Button>
                        </CardContent>
                    </Card>
                ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
                    {Object.entries(billing.available_plans).map(([planId, plan]) => {
                        const style = PLAN_STYLES[planId] || PLAN_STYLES.starter;
                        const Icon = style.icon;
                        const isCurrent = currentPlanId === planId;
                        return (
                            <Card
                                key={planId}
                                className={`relative overflow-hidden transition-all min-w-0 ${
                                    style.featured ? 'ring-2 ring-indigo-500 shadow-xl' : ''
                                }`}
                                data-testid={`plan-${planId}`}
                            >
                                {style.featured && (
                                    <div className="absolute top-0 right-0 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">
                                        MOST POPULAR
                                    </div>
                                )}
                                <CardHeader>
                                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${style.gradient} text-white mb-3`}>
                                        <Icon className="w-6 h-6" />
                                    </div>
                                    <CardTitle className="text-2xl">{plan.name}</CardTitle>
                                    <div className="flex items-baseline gap-1 mt-2">
                                        <span className="text-4xl font-bold">£{plan.price}</span>
                                        <span className="text-muted-foreground text-sm">/month</span>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <ul className="space-y-2">
                                        {plan.features?.map((feature, idx) => (
                                            <li key={idx} className="flex items-start gap-2 text-sm">
                                                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                                                <span>{feature}</span>
                                            </li>
                                        ))}
                                    </ul>
                                    <Button
                                        className={`w-full ${style.featured ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white' : ''}`}
                                        variant={style.featured ? 'default' : 'outline'}
                                        disabled={isCurrent || checkoutLoading === planId}
                                        onClick={() => handleSubscribe(planId)}
                                        data-testid={`subscribe-${planId}-btn`}
                                    >
                                        {checkoutLoading === planId ? (
                                            <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Redirecting…</>
                                        ) : isCurrent ? (
                                            'Current Plan'
                                        ) : (
                                            <>Subscribe <CreditCard className="w-4 h-4 ml-2" /></>
                                        )}
                                    </Button>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
                )}
            </div>

            {/* Add-ons */}
            {billing?.available_addons && Object.keys(billing.available_addons).length > 0 && (
                <div>
                    <h2 className="text-2xl font-bold mb-4">Add-ons</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {Object.entries(billing.available_addons).map(([addonId, addon]) => (
                            <Card key={addonId} data-testid={`addon-${addonId}`}>
                                <CardContent className="p-5">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Plus className="w-4 h-4 text-indigo-600" />
                                        <h3 className="font-semibold">{addon.name}</h3>
                                    </div>
                                    <p className="text-2xl font-bold mb-4">£{addon.price}</p>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="w-full"
                                        disabled={checkoutLoading === addonId}
                                        onClick={() => handleAddon(addonId)}
                                        data-testid={`buy-${addonId}-btn`}
                                    >
                                        {checkoutLoading === addonId ? (
                                            <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> …</>
                                        ) : 'Buy now'}
                                    </Button>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            )}

            {/* Transaction history */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Receipt className="w-5 h-5 text-indigo-600" />
                        <CardTitle>Transaction History</CardTitle>
                    </div>
                    <CardDescription>Recent payments and subscription changes</CardDescription>
                </CardHeader>
                <CardContent>
                    {!billing?.transactions?.length ? (
                        <div className="text-center py-10 text-muted-foreground">
                            <AlertCircle className="w-10 h-10 mx-auto mb-2 opacity-40" />
                            <p>No transactions yet</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-muted-foreground text-xs uppercase tracking-wide">
                                        <th className="text-left p-3">Date</th>
                                        <th className="text-left p-3">Type</th>
                                        <th className="text-left p-3">Description</th>
                                        <th className="text-right p-3">Amount</th>
                                        <th className="text-center p-3">Status</th>
                                        <th className="text-right p-3"></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {billing.transactions.map((tx) => (
                                        <tr
                                            key={tx.transaction_id}
                                            className="border-b hover:bg-accent/50"
                                            data-testid={`tx-${tx.transaction_id}`}
                                        >
                                            <td className="p-3 text-muted-foreground">
                                                {new Date(tx.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="p-3 capitalize">{tx.type}</td>
                                            <td className="p-3">{tx.plan_name || tx.addon_name || '—'}</td>
                                            <td className="p-3 text-right font-semibold">
                                                £{Number(tx.amount || 0).toFixed(2)}
                                            </td>
                                            <td className="p-3 text-center">
                                                <Badge
                                                    variant="outline"
                                                    className={
                                                        tx.payment_status === 'paid'
                                                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/30'
                                                            : tx.payment_status === 'pending'
                                                            ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/30'
                                                            : 'bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-900/30'
                                                    }
                                                >
                                                    {(tx.payment_status || tx.status || '').toUpperCase()}
                                                </Badge>
                                            </td>
                                            <td className="p-3 text-right">
                                                {tx.payment_status === 'paid' && (
                                                    <button
                                                        className="text-xs text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1 underline"
                                                        onClick={() => fetchReceipt(tx.transaction_id)}
                                                        data-testid={`receipt-${tx.transaction_id}`}
                                                    >
                                                        <Download className="w-3 h-3" /> Receipt
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
