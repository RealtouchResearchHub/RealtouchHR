import React from 'react';
import { cn, getComplianceColor } from '../../lib/utils';
import { ShieldQuestion } from 'lucide-react';

const STATE_LABELS = {
    not_assessed: 'Not Assessed',
    demo_data_only: 'Demo Data Only',
    setup_incomplete: 'Setup Incomplete',
    needs_attention: 'Needs Attention',
    high_risk: 'High Risk',
    compliant: 'Compliant',
};

export default function ComplianceScore({ score = null, state = null, size = 'lg', showLabel = true }) {
    const isAssessed = score !== null && score !== undefined && !isNaN(score);
    const validScore = isAssessed ? Math.max(0, Math.min(100, Math.round(Number(score)))) : 0;

    const sizes = {
        sm: { ring: 60, stroke: 6, text: 'text-base', iconSize: 20 },
        md: { ring: 80, stroke: 8, text: 'text-xl', iconSize: 28 },
        lg: { ring: 140, stroke: 10, text: 'text-3xl', iconSize: 44 },
    };

    const { ring, stroke, text, iconSize } = sizes[size] || sizes.lg;
    const radius = (ring - stroke * 2) / 2;
    const circumference = 2 * Math.PI * radius;

    if (!isAssessed) {
        return (
            <div className="relative inline-flex flex-col items-center">
                <div className="relative" style={{ width: ring, height: ring }}>
                    <svg width={ring} height={ring} className="transform -rotate-90">
                        <circle
                            cx={ring / 2}
                            cy={ring / 2}
                            r={radius}
                            strokeWidth={stroke}
                            fill="none"
                            className="stroke-muted"
                            strokeDasharray={`${circumference * 0.2} ${circumference * 0.8}`}
                            strokeDashoffset={0}
                            strokeLinecap="round"
                        />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <ShieldQuestion
                            style={{ width: iconSize, height: iconSize }}
                            className="text-muted-foreground"
                        />
                    </div>
                </div>
                {showLabel && (
                    <p className="mt-2 text-sm text-muted-foreground text-center">
                        {STATE_LABELS[state] || 'Not Assessed'}
                    </p>
                )}
            </div>
        );
    }

    return (
        <div className="relative inline-flex flex-col items-center">
            <div className="compliance-ring relative" style={{ width: ring, height: ring }}>
                <svg width={ring} height={ring} className="transform -rotate-90">
                    <circle
                        cx={ring / 2}
                        cy={ring / 2}
                        r={radius}
                        strokeWidth={stroke}
                        fill="none"
                        className="stroke-muted"
                    />
                    <circle
                        cx={ring / 2}
                        cy={ring / 2}
                        r={radius}
                        strokeWidth={stroke}
                        fill="none"
                        strokeLinecap="round"
                        className={cn(
                            'transition-all duration-1000 ease-out',
                            validScore >= 90 ? 'stroke-emerald-500' : validScore >= 70 ? 'stroke-amber-500' : 'stroke-rose-500'
                        )}
                        style={{
                            strokeDasharray: circumference,
                            strokeDashoffset: (1 - validScore / 100) * circumference,
                        }}
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center" style={{ width: ring, height: ring }}>
                    <span className={cn("font-bold font-['Plus_Jakarta_Sans'] whitespace-nowrap", text, getComplianceColor(validScore))}>
                        {validScore}%
                    </span>
                </div>
            </div>
            {showLabel && (
                <p className="mt-2 text-sm text-muted-foreground">Compliance Score</p>
            )}
        </div>
    );
}
