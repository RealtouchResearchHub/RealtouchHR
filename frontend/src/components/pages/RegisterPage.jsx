import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Separator } from '../ui/separator';
import { Building2, ArrowRight, CheckCircle2, AlertTriangle, Loader2, Search, Tag } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function RegisterPage() {
    const navigate = useNavigate();
    const { register, loginWithGoogle } = useAuth();
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        company_name: '',
        company_number: '',
    });
    const [loading, setLoading] = useState(false);

    // Promo code state
    const [promoCode, setPromoCode] = useState('');
    const [promoStatus, setPromoStatus] = useState(null); // null | { valid, description, discount_percent, months }
    const [promoChecking, setPromoChecking] = useState(false);

    // Companies House lookup state
    const [chResults, setChResults] = useState([]);
    const [chDropdownOpen, setChDropdownOpen] = useState(false);
    const [chLoading, setChLoading] = useState(false);
    const [chSelected, setChSelected] = useState(null);   // confirmed CH company snapshot
    const [chWarning, setChWarning] = useState('');
    const debounceRef = useRef(null);
    const dropdownRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handler = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setChDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const searchCH = async (query) => {
        if (!query || query.trim().length < 2) {
            setChResults([]);
            setChDropdownOpen(false);
            return;
        }
        setChLoading(true);
        try {
            const res = await axios.get(`${API_URL}/api/company-lookup/search`, {
                params: { query: query.trim() }
            });
            const items = res.data.items || [];
            setChResults(items);
            setChDropdownOpen(items.length > 0);
        } catch {
            setChResults([]);
            setChDropdownOpen(false);
        } finally {
            setChLoading(false);
        }
    };

    const triggerSearch = (value) => {
        clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => searchCH(value), 450);
    };

    const handleCompanyNameChange = (e) => {
        const val = e.target.value;
        setFormData(prev => ({ ...prev, company_name: val }));
        if (chSelected) { setChSelected(null); setChWarning(''); }
        triggerSearch(val);
    };

    const handleCompanyNumberChange = (e) => {
        const val = e.target.value.toUpperCase();
        setFormData(prev => ({ ...prev, company_number: val }));
        if (chSelected) { setChSelected(null); setChWarning(''); }
        triggerSearch(val);
    };

    const handleChSelect = (item) => {
        setFormData(prev => ({
            ...prev,
            company_name: item.company_name,
            company_number: item.company_number,
        }));
        setChSelected(item);
        setChWarning(item.warning || '');
        setChResults([]);
        setChDropdownOpen(false);
    };

    const validatePromo = async (code) => {
        if (!code.trim()) { setPromoStatus(null); return; }
        setPromoChecking(true);
        try {
            const res = await axios.get(`${API_URL}/api/discount-codes/validate`, { params: { code } });
            setPromoStatus(res.data);
        } catch {
            setPromoStatus({ valid: false, message: 'Could not validate code' });
        } finally {
            setPromoChecking(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = {
                name: formData.name,
                email: formData.email,
                password: formData.password,
                company_name: formData.company_name || undefined,
                company_number: formData.company_number || undefined,
                ch_snapshot: chSelected || undefined,
                promo_code: (promoStatus?.valid && promoCode) ? promoCode.trim() : undefined,
            };
            await register(payload);
            toast.success('Account created successfully!');
            navigate('/dashboard');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    const features = [
        'Setup in under 10 minutes',
        'Add employees and run payroll preview',
        'Compliance checks from day one',
        'No credit card required'
    ];

    return (
        <div className="min-h-screen bg-background flex" data-testid="register-page">
            {/* Left Side - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-emerald-600 to-teal-700 p-12 flex-col justify-between text-white">
                <div>
                    <div className="flex items-center">
                        <img src="/logo-dark.png" alt="RealtouchHR" className="h-12 lg:h-16 w-auto" />
                    </div>
                </div>

                <div className="space-y-8">
                    <div>
                        <h1 className="text-4xl lg:text-5xl font-bold font-['Plus_Jakarta_Sans'] leading-tight">
                            Get Started<br />in Minutes
                        </h1>
                        <p className="mt-4 text-lg text-white/80 max-w-md">
                            Join hundreds of UK businesses that trust RealtouchHR for their HR and payroll needs.
                        </p>
                    </div>

                    <div className="space-y-3">
                        {features.map((feature, index) => (
                            <div key={index} className="flex items-center gap-3">
                                <CheckCircle2 className="w-5 h-5 text-emerald-300 flex-shrink-0" />
                                <span className="text-white/90">{feature}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <p className="text-white/60 text-sm">
                    © 2026 RealtouchHR. Built for UK SMBs.
                </p>
            </div>

            {/* Right Side - Register Form */}
            <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
                <Card className="w-full max-w-md border-0 shadow-none lg:shadow-lg lg:border">
                    <CardHeader className="text-center space-y-2">
                        <div className="lg:hidden flex items-center justify-center mb-4">
                            <img src="/logo-white.png" alt="RealtouchHR" className="h-10 sm:h-12 w-auto block dark:hidden" />
                            <img src="/logo-dark.png" alt="RealtouchHR" className="h-10 sm:h-12 w-auto hidden dark:block" />
                        </div>
                        <CardTitle className="text-2xl font-bold font-['Plus_Jakarta_Sans']">Create your account</CardTitle>
                        <CardDescription>Start your free trial - no credit card required</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Full Name</Label>
                                <Input
                                    id="name"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="John Smith"
                                    required
                                    data-testid="input-register-name"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">Work Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="you@company.com"
                                    required
                                    data-testid="input-register-email"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="password">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    placeholder="••••••••"
                                    required
                                    data-testid="input-register-password"
                                />
                            </div>

                            {/* Company section */}
                            <div className="space-y-3 pt-1">
                                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                    Company Details <span className="font-normal normal-case">(optional)</span>
                                </div>

                                {/* Company Name with CH lookup */}
                                <div className="space-y-2 relative" ref={dropdownRef}>
                                    <Label htmlFor="company_name">Company Name</Label>
                                    <div className="relative">
                                        <Input
                                            id="company_name"
                                            value={formData.company_name}
                                            onChange={handleCompanyNameChange}
                                            placeholder="Acme Ltd"
                                            autoComplete="off"
                                            data-testid="input-register-company"
                                            className="pr-8"
                                        />
                                        <div className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
                                            {chLoading
                                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                : <Search className="w-3.5 h-3.5" />
                                            }
                                        </div>
                                    </div>

                                    {/* Results dropdown */}
                                    {chDropdownOpen && chResults.length > 0 && (
                                        <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-lg max-h-56 overflow-y-auto">
                                            {chResults.map((item) => (
                                                <button
                                                    key={item.company_number}
                                                    type="button"
                                                    onClick={() => handleChSelect(item)}
                                                    className="w-full text-left px-3 py-2.5 hover:bg-accent transition-colors border-b border-border last:border-0"
                                                >
                                                    <div className="flex items-center justify-between gap-2">
                                                        <span className="text-sm font-medium text-foreground truncate">{item.company_name}</span>
                                                        <span className="text-xs text-muted-foreground flex-shrink-0">{item.company_number}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 mt-0.5">
                                                        <span className={`text-xs ${item.company_status === 'active' ? 'text-emerald-600' : 'text-amber-600'}`}>
                                                            {item.company_status || 'unknown'}
                                                        </span>
                                                        {item.registered_office_address_str && (
                                                            <span className="text-xs text-muted-foreground truncate">{item.registered_office_address_str}</span>
                                                        )}
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {/* Company Number */}
                                <div className="space-y-2">
                                    <Label htmlFor="company_number">
                                        Company Registration Number
                                        <span className="ml-1 text-xs text-muted-foreground font-normal">(Companies House)</span>
                                    </Label>
                                    <Input
                                        id="company_number"
                                        value={formData.company_number}
                                        onChange={handleCompanyNumberChange}
                                        placeholder="e.g. 12345678"
                                        autoComplete="off"
                                        maxLength={8}
                                    />
                                </div>

                                {/* Verified badge */}
                                {chSelected && !chWarning && (
                                    <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 rounded px-3 py-2">
                                        <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                                        <span>Verified via Companies House · {chSelected.company_type}</span>
                                    </div>
                                )}

                                {/* Warning for inactive company status */}
                                {chSelected && chWarning && (
                                    <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800 rounded px-3 py-2">
                                        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                        <span>{chWarning} You may still proceed.</span>
                                    </div>
                                )}
                            </div>

                            <Button
                                type="submit"
                                className="w-full bg-indigo-600 hover:bg-indigo-700"
                                disabled={loading}
                                data-testid="register-submit-btn"
                            >
                                {loading ? 'Creating account...' : 'Create account'}
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>
                        </form>

                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <Separator />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
                            </div>
                        </div>

                        <Button
                            variant="outline"
                            className="w-full"
                            onClick={loginWithGoogle}
                            data-testid="google-register-btn"
                        >
                            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Sign up with Google
                        </Button>

                        <p className="text-center text-sm text-muted-foreground">
                            Already have an account?{' '}
                            <Link to="/login" className="text-indigo-600 hover:underline font-medium" data-testid="login-link">
                                Sign in
                            </Link>
                        </p>

                        {/* Discount / promo code */}
                        <div className="space-y-1.5">
                            <Label htmlFor="promo_code" className="flex items-center gap-1.5 text-sm">
                                <Tag className="w-3.5 h-3.5" /> Discount Code <span className="text-muted-foreground font-normal">(optional)</span>
                            </Label>
                            <div className="flex gap-2">
                                <Input
                                    id="promo_code"
                                    value={promoCode}
                                    onChange={(e) => { setPromoCode(e.target.value.toUpperCase()); setPromoStatus(null); }}
                                    onBlur={() => validatePromo(promoCode)}
                                    placeholder="Enter discount code"
                                    className="uppercase"
                                    maxLength={20}
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="flex-shrink-0"
                                    onClick={() => validatePromo(promoCode)}
                                    disabled={promoChecking || !promoCode.trim()}
                                >
                                    {promoChecking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Apply'}
                                </Button>
                            </div>
                            {promoStatus?.valid && (
                                <div className="flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-400">
                                    <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                                    <span>{promoStatus.description} — applied at checkout</span>
                                </div>
                            )}
                            {promoStatus && !promoStatus.valid && (
                                <div className="flex items-center gap-1.5 text-xs text-rose-600">
                                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                                    <span>{promoStatus.message || 'Invalid code'}</span>
                                </div>
                            )}
                        </div>

                        <p className="text-center text-xs text-muted-foreground">
                            By signing up, you agree to our{' '}
                            <Link to="/privacy" className="text-indigo-600 hover:underline">Terms of Service and Privacy Policy</Link>
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
