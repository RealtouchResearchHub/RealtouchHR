import React from 'react';
import { cn, getComplianceColor, getComplianceBg } from '../../lib/utils';

export default function ComplianceScore({ score = 100, size = 'lg', showLabel = true }) {
    // Ensure score is a valid number between 0-100
    const validScore = typeof score === 'number' && !isNaN(score) ? Math.max(0, Math.min(100, score)) : 100;
    
    const circumference = 2 * Math.PI * 45;
    const strokeDashoffset = circumference - (validScore / 100) * circumference;

    const sizes = {
        sm: { ring: 60, stroke: 6, text: 'text-lg' },
        md: { ring: 80, stroke: 8, text: 'text-2xl' },
        lg: { ring: 120, stroke: 10, text: 'text-4xl' }
    };

    const { ring, stroke, text } = sizes[size];

    return (
        <div className="relative inline-flex flex-col items-center">
            <div className="compliance-ring relative" style={{ width: ring, height: ring }}>
                <svg width={ring} height={ring} className="transform -rotate-90">
                    {/* Background circle */}
                    <circle
                        cx={ring / 2}
                        cy={ring / 2}
                        r={45 * (ring / 120)}
                        strokeWidth={stroke}
                        fill="none"
                        className="stroke-muted"
                    />
                    {/* Progress circle */}
                    <circle
                        cx={ring / 2}
                        cy={ring / 2}
                        r={45 * (ring / 120)}
                        strokeWidth={stroke}
                        fill="none"
                        strokeLinecap="round"
                        className={cn(
                            "transition-all duration-1000 ease-out",
                            score >= 90 ? "stroke-emerald-500" : score >= 70 ? "stroke-amber-500" : "stroke-rose-500"
                        )}
                        style={{
                            strokeDasharray: circumference * (ring / 120),
                            strokeDashoffset: strokeDashoffset * (ring / 120)
                        }}
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className={cn("font-bold font-['Plus_Jakarta_Sans']", text, getComplianceColor(validScore))}>
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
