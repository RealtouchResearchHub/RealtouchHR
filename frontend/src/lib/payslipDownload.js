/**
 * Helpers to download files with trial + paywall support.
 * 
 * Flow for payslip downloads:
 *   1. Try fetching the PDF.
 *   2. On 402 (payment required) → initiate Stripe checkout for £5, redirect.
 *   3. On 403 (trial blocked) → show "upgrade plan" toast and redirect to /billing.
 *   4. On 200 → save file locally.
 * 
 * On return from Stripe with ?status=success&session_id=..., the app should:
 *   - Poll /api/payments/checkout/status until paid
 *   - Re-attempt the download (server has issued a 30-minute download pass)
 */
import axios from 'axios';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export async function downloadPayslipWithPaywall({
    payrunId,
    employeeId,
    filename,
    originUrl = window.location.origin,
    onPaywall,
}) {
    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };

    try {
        const res = await axios.get(
            `${API_URL}/api/payroll/runs/${payrunId}/payslips/${employeeId}/pdf`,
            { headers, withCredentials: true, responseType: 'blob' }
        );
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || `payslip_${employeeId}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        toast.success('Payslip downloaded');
        return { status: 'downloaded' };
    } catch (err) {
        const status = err.response?.status;
        // Blob error responses can't be parsed as JSON directly
        let detail = '';
        if (err.response?.data instanceof Blob) {
            try { detail = JSON.parse(await err.response.data.text()).detail; }
            catch { detail = 'Download failed'; }
        } else {
            detail = err.response?.data?.detail || 'Download failed';
        }

        if (status === 403) {
            toast.error(detail || 'Downloads disabled during trial');
            return { status: 'trial_blocked', detail };
        }
        if (status === 402) {
            // Paywall — create checkout
            // First try the new bulk upsell modal if onPaywall returns 'bulk'
            if (onPaywall) {
                const choice = await onPaywall(detail);
                if (choice === false || choice === 'cancel') return { status: 'cancelled' };
                if (choice === 'bulk') {
                    // Buy 30-day unlimited downloads instead
                    try {
                        const co = await axios.post(
                            `${API_URL}/api/payments/checkout/addon`,
                            {
                                addon_id: 'bulk_downloads_monthly',
                                origin_url: originUrl,
                                quantity: 1,
                            },
                            { headers, withCredentials: true }
                        );
                        if (co.data?.checkout_url) {
                            sessionStorage.setItem('pending_payslip_download', JSON.stringify({
                                payrunId, employeeId, filename,
                                session_id: co.data.session_id,
                                isBulk: true,
                            }));
                            window.location.href = co.data.checkout_url;
                            return { status: 'redirecting' };
                        }
                    } catch (coErr) {
                        toast.error(coErr.response?.data?.detail || 'Could not start bulk checkout');
                        return { status: 'error' };
                    }
                }
                // choice === 'single' or true → default single £5 flow
            }
            try {
                const co = await axios.post(
                    `${API_URL}/api/payments/checkout/payslip`,
                    {
                        payslip_id: `${payrunId}:${employeeId}`,
                        origin_url: originUrl,
                    },
                    { headers, withCredentials: true }
                );
                sessionStorage.setItem('pending_payslip_download', JSON.stringify({
                    payrunId, employeeId, filename,
                    session_id: co.data.session_id,
                }));
                if (co.data?.checkout_url) {
                    window.location.href = co.data.checkout_url;
                    return { status: 'redirecting' };
                }
            } catch (coErr) {
                toast.error(coErr.response?.data?.detail || 'Could not start checkout');
                return { status: 'error' };
            }
        }
        toast.error(detail);
        return { status: 'error' };
    }
}

/**
 * Called on return from Stripe. Poll the session status, then re-attempt the download.
 */
export async function resumePendingPayslipDownload(sessionId) {
    const stored = sessionStorage.getItem('pending_payslip_download');
    if (!stored) return;
    const pending = JSON.parse(stored);
    if (pending.session_id !== sessionId) return;

    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };

    // Poll until paid (max 12 attempts × 1.5s ≈ 18s)
    let paid = false;
    for (let i = 0; i < 12; i++) {
        try {
            const res = await axios.post(
                `${API_URL}/api/payments/checkout/status`,
                { session_id: sessionId, origin_url: window.location.origin },
                { headers, withCredentials: true }
            );
            if (res.data.payment_status === 'paid') { paid = true; break; }
        } catch (e) { /* ignore */ }
        await new Promise(r => setTimeout(r, 1500));
    }
    if (!paid) {
        toast.warning('Payment still processing — try the download again in a minute.');
        sessionStorage.removeItem('pending_payslip_download');
        return;
    }
    // Re-attempt download (server has a 30-min pass now)
    await downloadPayslipWithPaywall(pending);
    sessionStorage.removeItem('pending_payslip_download');
}
