import React from 'react';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import {
    PoundSterling, Infinity as InfinityIcon, CheckCircle2, X, FileDown, Sparkles,
} from 'lucide-react';

/**
 * PaywallModal — shown when the user attempts to download but has no
 * pass / quota / bulk pack. Offers two paths: pay £5 single OR £29 unlimited.
 */
export default function PaywallModal({ open, onChoice, message }) {
    return (
        <Dialog open={open} onOpenChange={(v) => !v && onChoice('cancel')}>
            <DialogContent className="max-w-2xl" data-testid="paywall-modal">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FileDown className="w-5 h-5 text-indigo-600" /> Pay-per-download
                    </DialogTitle>
                    <DialogDescription>
                        {message || 'Choose how you want to download this payslip.'}
                    </DialogDescription>
                </DialogHeader>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                    {/* Single download */}
                    <Card className="border-slate-200 hover:border-indigo-400 transition cursor-pointer" data-testid="paywall-single-card">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-2 mb-2">
                                <PoundSterling className="w-4 h-4 text-slate-500" />
                                <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Single payslip</p>
                            </div>
                            <p className="text-3xl font-bold">£5.00</p>
                            <p className="text-xs text-slate-500 mt-1">One-time payment for this payslip only</p>
                            <ul className="mt-4 space-y-1.5 text-sm">
                                <li className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" /> 30-min download window
                                </li>
                                <li className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" /> Receipt via Stripe email
                                </li>
                            </ul>
                            <Button
                                className="w-full mt-5"
                                variant="outline"
                                onClick={() => onChoice('single')}
                                data-testid="paywall-pay-single-btn"
                            >
                                Pay £5 for this payslip
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Bulk unlimited */}
                    <Card className="border-2 border-indigo-500 shadow-xl shadow-indigo-500/20 relative cursor-pointer" data-testid="paywall-bulk-card">
                        <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white border-0">
                            <Sparkles className="w-3 h-3 mr-1" /> Best value
                        </Badge>
                        <CardContent className="p-5">
                            <div className="flex items-center gap-2 mb-2">
                                <InfinityIcon className="w-4 h-4 text-indigo-500" />
                                <p className="text-xs uppercase tracking-wider text-indigo-700 dark:text-indigo-400 font-semibold">Unlimited 30 days</p>
                            </div>
                            <p className="text-3xl font-bold">£29.00</p>
                            <p className="text-xs text-slate-500 mt-1">All payslip + tax-doc downloads, free for 30 days</p>
                            <ul className="mt-4 space-y-1.5 text-sm">
                                <li className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" /> Unlimited payslip downloads
                                </li>
                                <li className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" /> P45 / P60 / P11D included
                                </li>
                                <li className="flex items-start gap-2 text-slate-700 dark:text-slate-300">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" /> Stacks if you already have time
                                </li>
                            </ul>
                            <Button
                                className="w-full mt-5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white"
                                onClick={() => onChoice('bulk')}
                                data-testid="paywall-buy-bulk-btn"
                            >
                                Buy unlimited £29
                            </Button>
                        </CardContent>
                    </Card>
                </div>

                <div className="text-center mt-2">
                    <button
                        className="text-xs text-slate-500 hover:text-slate-700"
                        onClick={() => onChoice('cancel')}
                        data-testid="paywall-cancel-btn"
                    >
                        Cancel — don't download right now
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
