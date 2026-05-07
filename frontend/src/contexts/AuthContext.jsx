import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [company, setCompany] = useState(null);

    const fetchUser = useCallback(async () => {
        try {
            const response = await axios.get(`${API_URL}/api/auth/me`, {
                withCredentials: true
            });
            setUser(response.data);
            
            // Fetch company
            const companyResponse = await axios.get(`${API_URL}/api/company`, {
                withCredentials: true
            });
            setCompany(companyResponse.data);
        } catch (error) {
            setUser(null);
            setCompany(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const login = async (email, password) => {
        const response = await axios.post(`${API_URL}/api/auth/login`, 
            { email, password },
            { withCredentials: true }
        );
        setUser(response.data.user);
        localStorage.setItem('token', response.data.token);
        await fetchUser();
        return response.data;
    };

    const register = async (data) => {
        const response = await axios.post(`${API_URL}/api/auth/register`, 
            data,
            { withCredentials: true }
        );
        setUser(response.data.user);
        localStorage.setItem('token', response.data.token);
        await fetchUser();
        return response.data;
    };

    const loginWithGoogle = () => {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        const redirectUrl = window.location.origin + '/dashboard';
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    };

    const processGoogleSession = async (sessionId) => {
        const response = await axios.post(`${API_URL}/api/auth/session`, {}, {
            headers: { 'X-Session-ID': sessionId },
            withCredentials: true
        });
        setUser(response.data.user);
        localStorage.setItem('token', response.data.token);
        await fetchUser();
        return response.data;
    };

    const logout = async () => {
        try {
            await axios.post(`${API_URL}/api/auth/logout`, {}, {
                withCredentials: true
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        setUser(null);
        setCompany(null);
        localStorage.removeItem('token');
    };

    const updatePreferences = async (preferences) => {
        await axios.put(`${API_URL}/api/auth/preferences`, preferences, {
            withCredentials: true
        });
        if (preferences.theme_preference) {
            setUser(prev => ({ ...prev, theme_preference: preferences.theme_preference }));
        }
    };

    const refreshCompany = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/company`, {
                withCredentials: true
            });
            setCompany(response.data);
        } catch (error) {
            console.error('Error fetching company:', error);
        }
    };

    // Get token from localStorage for components that need it
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    const value = {
        user,
        company,
        loading,
        login,
        register,
        loginWithGoogle,
        processGoogleSession,
        logout,
        updatePreferences,
        refreshCompany,
        refresh: fetchUser,
        isAuthenticated: !!user,
        token
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
