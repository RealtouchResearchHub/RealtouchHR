import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Building2 } from 'lucide-react';

export default function AuthCallback() {
    const navigate = useNavigate();
    const location = useLocation();
    const { processGoogleSession } = useAuth();
    const hasProcessed = useRef(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Prevent double processing in StrictMode
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const processSession = async () => {
            try {
                // Extract session_id from URL fragment
                const hash = location.hash;
                const sessionIdMatch = hash.match(/session_id=([^&]+)/);
                
                if (!sessionIdMatch) {
                    throw new Error('No session ID found');
                }

                const sessionId = sessionIdMatch[1];
                await processGoogleSession(sessionId);
                
                // Navigate to dashboard on success
                navigate('/dashboard', { replace: true });
            } catch (err) {
                console.error('Auth callback error:', err);
                setError(err.message);
                setTimeout(() => navigate('/login', { replace: true }), 3000);
            }
        };

        processSession();
    }, [location, navigate, processGoogleSession]);

    return (
        <div className="min-h-screen bg-background flex items-center justify-center" data-testid="auth-callback-page">
            <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-6">
                    <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center">
                        <Building2 className="w-7 h-7 text-white" />
                    </div>
                    <span className="text-2xl font-bold font-['Plus_Jakarta_Sans']">RealtouchHR</span>
                </div>
                
                {error ? (
                    <div className="text-center">
                        <p className="text-rose-600 mb-2">Authentication failed</p>
                        <p className="text-muted-foreground text-sm">{error}</p>
                        <p className="text-muted-foreground text-sm mt-2">Redirecting to login...</p>
                    </div>
                ) : (
                    <div>
                        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                        <p className="text-muted-foreground">Completing sign in...</p>
                    </div>
                )}
            </div>
        </div>
    );
}
