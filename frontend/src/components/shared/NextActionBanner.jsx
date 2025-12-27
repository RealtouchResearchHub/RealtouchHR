import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../ui/button';
import { ArrowRight, AlertTriangle, CheckCircle2, Users, FileText, CreditCard } from 'lucide-react';

const actionIcons = {
    onboarding: Users,
    compliance: AlertTriangle,
    employee: FileText,
    payroll: CreditCard,
    default: CheckCircle2
};

export default function NextActionBanner({ action }) {
    if (!action) {
        return (
            <div className="rounded-2xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white p-6 lg:p-8 shadow-xl shadow-emerald-500/20 relative overflow-hidden" data-testid="next-action-banner">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                <div className="relative">
                    <div className="flex items-center gap-3 mb-2">
                        <CheckCircle2 className="w-6 h-6" />
                        <span className="text-sm font-medium uppercase tracking-wide opacity-90">All Caught Up</span>
                    </div>
                    <h2 className="text-2xl lg:text-3xl font-bold font-['Plus_Jakarta_Sans'] mb-2">
                        Everything looks great!
                    </h2>
                    <p className="text-white/80 max-w-lg">
                        Your HR and payroll are up to date. No immediate actions required.
                    </p>
                </div>
            </div>
        );
    }

    const Icon = actionIcons[action.type] || actionIcons.default;
    const isUrgent = action.type === 'compliance';

    const getLink = () => {
        switch (action.type) {
            case 'onboarding':
                return '/employees/new';
            case 'employee':
                return `/employees/${action.employee_id}`;
            case 'compliance':
                return '/settings';
            case 'payroll':
                return '/payroll';
            default:
                return '/dashboard';
        }
    };

    return (
        <div 
            className={`rounded-2xl p-6 lg:p-8 shadow-xl relative overflow-hidden ${
                isUrgent 
                    ? 'bg-gradient-to-r from-rose-500 to-rose-600 shadow-rose-500/20' 
                    : 'bg-gradient-to-r from-indigo-600 to-indigo-700 shadow-indigo-500/20'
            } text-white`}
            data-testid="next-action-banner"
        >
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="relative flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <Icon className="w-6 h-6" />
                        <span className="text-sm font-medium uppercase tracking-wide opacity-90">
                            {isUrgent ? 'Action Required' : 'Next Best Action'}
                        </span>
                    </div>
                    <h2 className="text-2xl lg:text-3xl font-bold font-['Plus_Jakarta_Sans'] mb-2">
                        {action.title}
                    </h2>
                    <p className="text-white/80 max-w-lg">
                        {isUrgent 
                            ? 'This needs your attention to maintain compliance.'
                            : 'Complete this to keep your HR running smoothly.'
                        }
                    </p>
                </div>
                <Link to={getLink()}>
                    <Button 
                        size="lg" 
                        className="bg-white text-indigo-700 hover:bg-white/90 shadow-lg group"
                        data-testid="next-action-btn"
                    >
                        Take Action
                        <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </Button>
                </Link>
            </div>
        </div>
    );
}
