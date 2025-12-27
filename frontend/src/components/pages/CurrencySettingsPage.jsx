import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { 
    Globe,
    ArrowRight,
    RefreshCw,
    DollarSign,
    Check
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function CurrencySettingsPage() {
    const [currencies, setCurrencies] = useState([]);
    const [companyCurrency, setCompanyCurrency] = useState('GBP');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    
    // Conversion calculator
    const [fromCurrency, setFromCurrency] = useState('USD');
    const [toCurrency, setToCurrency] = useState('GBP');
    const [amount, setAmount] = useState('1000');
    const [conversionResult, setConversionResult] = useState(null);
    const [converting, setConverting] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [currenciesRes, companyRes] = await Promise.all([
                axios.get(`${API_URL}/api/currencies`, { withCredentials: true }),
                axios.get(`${API_URL}/api/company`, { withCredentials: true })
            ]);
            setCurrencies(currenciesRes.data);
            if (companyRes.data?.default_currency) {
                setCompanyCurrency(companyRes.data.default_currency);
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveCurrency = async () => {
        setSaving(true);
        try {
            await axios.put(`${API_URL}/api/company/currency`, { currency: companyCurrency }, { withCredentials: true });
            toast.success('Default currency updated');
        } catch (error) {
            toast.error('Failed to update currency');
        } finally {
            setSaving(false);
        }
    };

    const handleConvert = async () => {
        if (!amount || isNaN(parseFloat(amount))) {
            toast.error('Please enter a valid amount');
            return;
        }

        setConverting(true);
        try {
            const response = await axios.post(
                `${API_URL}/api/currencies/convert`,
                null,
                { 
                    params: {
                        from_currency: fromCurrency,
                        to_currency: toCurrency,
                        amount: parseFloat(amount)
                    },
                    withCredentials: true 
                }
            );
            setConversionResult(response.data);
        } catch (error) {
            toast.error('Conversion failed');
        } finally {
            setConverting(false);
        }
    };

    const getCurrencySymbol = (code) => {
        const currency = currencies.find(c => c.code === code);
        return currency?.symbol || code;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="currency-settings-page">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Currency Settings</h1>
                <p className="text-muted-foreground mt-1">Configure multi-currency support for international operations</p>
            </div>

            {/* Default Currency */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Globe className="w-5 h-5" />
                        Default Currency
                    </CardTitle>
                    <CardDescription>Set your company's primary operating currency</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-end gap-4">
                        <div className="flex-1 space-y-2">
                            <Label>Select Currency</Label>
                            <Select value={companyCurrency} onValueChange={setCompanyCurrency}>
                                <SelectTrigger data-testid="select-default-currency">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {currencies.map(currency => (
                                        <SelectItem key={currency.code} value={currency.code}>
                                            <span className="flex items-center gap-2">
                                                <span className="font-mono">{currency.symbol}</span>
                                                <span>{currency.code} - {currency.name}</span>
                                            </span>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <Button onClick={handleSaveCurrency} disabled={saving} data-testid="save-currency-btn">
                            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
                            Save
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Currency Converter */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <DollarSign className="w-5 h-5" />
                        Currency Converter
                    </CardTitle>
                    <CardDescription>Convert amounts between currencies</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-7 gap-4 items-end">
                        <div className="md:col-span-2 space-y-2">
                            <Label>Amount</Label>
                            <Input
                                type="number"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="Enter amount"
                                data-testid="input-amount"
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <Label>From</Label>
                            <Select value={fromCurrency} onValueChange={setFromCurrency}>
                                <SelectTrigger data-testid="select-from-currency">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {currencies.map(currency => (
                                        <SelectItem key={currency.code} value={currency.code}>
                                            {currency.symbol} {currency.code}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-center justify-center">
                            <ArrowRight className="w-5 h-5 text-muted-foreground" />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <Label>To</Label>
                            <Select value={toCurrency} onValueChange={setToCurrency}>
                                <SelectTrigger data-testid="select-to-currency">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {currencies.map(currency => (
                                        <SelectItem key={currency.code} value={currency.code}>
                                            {currency.symbol} {currency.code}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    
                    <Button onClick={handleConvert} disabled={converting} data-testid="convert-btn">
                        {converting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
                        Convert
                    </Button>

                    {conversionResult && (
                        <div className="p-6 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30">
                            <div className="grid grid-cols-2 gap-8">
                                <div>
                                    <p className="text-sm text-muted-foreground">From</p>
                                    <p className="text-2xl font-bold">
                                        {getCurrencySymbol(conversionResult.from_currency)}{conversionResult.amount.toLocaleString()}
                                    </p>
                                    <p className="text-sm text-muted-foreground">{conversionResult.from_currency}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">To</p>
                                    <p className="text-2xl font-bold text-indigo-600">
                                        {getCurrencySymbol(conversionResult.to_currency)}{conversionResult.converted_amount.toLocaleString()}
                                    </p>
                                    <p className="text-sm text-muted-foreground">{conversionResult.to_currency}</p>
                                </div>
                            </div>
                            <p className="text-xs text-muted-foreground mt-4">
                                Exchange rate: 1 {conversionResult.from_currency} = {conversionResult.rate.toFixed(6)} {conversionResult.to_currency}
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Supported Currencies */}
            <Card>
                <CardHeader>
                    <CardTitle>Supported Currencies</CardTitle>
                    <CardDescription>All currencies available for multi-currency operations</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
                        {currencies.map(currency => (
                            <div 
                                key={currency.code}
                                className="p-3 rounded-lg border hover:border-indigo-300 transition-colors"
                            >
                                <div className="flex items-center gap-2">
                                    <span className="text-lg font-mono">{currency.symbol}</span>
                                    <span className="font-semibold">{currency.code}</span>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">{currency.name}</p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
