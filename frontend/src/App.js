import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { Toaster } from './components/ui/sonner';

// Global axios interceptor — attach Bearer token from localStorage on every request
axios.interceptors.request.use((config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token && !config.headers?.Authorization) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Pages
import LoginPage from './components/pages/LoginPage';
import RegisterPage from './components/pages/RegisterPage';
import ResetPasswordPage from './components/pages/ResetPasswordPage';
import AuthCallback from './components/pages/AuthCallback';
import GoogleCallbackPage from './components/pages/GoogleCallbackPage';
import Dashboard from './components/pages/Dashboard';
import EmployeesPage from './components/pages/EmployeesPage';
import EmployeeDetail from './components/pages/EmployeeDetail';
import LeavePage from './components/pages/LeavePage';
import DocumentsPage from './components/pages/DocumentsPage';
import SchedulingPage from './components/pages/SchedulingPage';
import PayrollPage from './components/pages/PayrollPage';
import PayRunDetail from './components/pages/PayRunDetail';
import AuditPage from './components/pages/AuditPage';
import SettingsPage from './components/pages/SettingsPage';
import BulkImportPage from './components/pages/BulkImportPage';
import OnboardingWizard from './components/pages/OnboardingWizard';
import SelfServicePortal from './components/pages/SelfServicePortal';
import HMRCDashboard from './components/pages/HMRCDashboard';
import HMRCSubmissionPage from './components/pages/HMRCSubmissionPage';
import UKVICompliancePage from './components/pages/UKVICompliancePage';
import EnterprisePage from './components/pages/EnterprisePage';
import TimeSchedulingPage from './components/pages/TimeSchedulingPage';
import BillingPage from './components/pages/BillingPage';
import StatutoryPaymentsPage from './components/pages/StatutoryPaymentsPage';
import YearEndPage from './components/pages/YearEndPage';
import LandingPage from './components/pages/LandingPage';
import AdminPortalPage from './components/pages/AdminPortalPage';
import InviteAcceptPage from './components/pages/InviteAcceptPage';
import SuperAdminPage from './components/pages/SuperAdminPage';
import PerformancePage from './components/pages/PerformancePage';
import EmployeeRelationsPage from './components/pages/EmployeeRelationsPage';
import GDPRCenterPage from './components/pages/GDPRCenterPage';
import SecurityPage from './components/pages/SecurityPage';
import TrustBadgePage from './components/pages/TrustBadgePage';
import TrustVerifyPage from './components/pages/TrustVerifyPage';
import PoliciesPage from './components/pages/PoliciesPage';
import TrainingPage from './components/pages/TrainingPage';
import AbsencePage from './components/pages/AbsencePage';
import HRAnalyticsPage from './components/pages/HRAnalyticsPage';
import DPOCenterPage from './components/pages/DPOCenterPage';
import ExpensesPage from './components/pages/ExpensesPage';
import RecruitmentPage from './components/pages/RecruitmentPage';
import ReportsPage from './components/pages/ReportsPage';
import PrivacyPolicyPage from './components/pages/PrivacyPolicyPage';

// Layout
import MainLayout from './components/layout/MainLayout';
import CookieConsent from './components/shared/CookieConsent';

import './App.css';

// Protected Route Component
function ProtectedRoute({ children, showLayout = true }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!showLayout) {
        return children;
    }

    return <MainLayout>{children}</MainLayout>;
}

// Admin-only route — requires owner or admin role
function AdminRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (user.role !== 'owner' && user.role !== 'admin') {
        return (
            <MainLayout>
                <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 text-center">
                    <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-950/40 flex items-center justify-center">
                        <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                        </svg>
                    </div>
                    <h1 className="text-2xl font-bold text-foreground">Access Denied</h1>
                    <p className="text-muted-foreground max-w-sm">
                        The Admin Portal is restricted to users with the <strong>Owner</strong> or <strong>Administrator</strong> role. Contact your account owner to request access.
                    </p>
                    <Navigate to="/dashboard" replace />
                </div>
            </MainLayout>
        );
    }

    return <MainLayout>{children}</MainLayout>;
}

// Blocks the plain "employee" role from admin-level pages (company settings,
// payroll, HMRC, employee records, year-end) regardless of job_title.
function EmployeeRestrictedRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (user.role === 'employee') {
        return <Navigate to="/dashboard" replace />;
    }

    return <MainLayout>{children}</MainLayout>;
}

// Super Admin route — requires platform_admin flag
function SuperAdminRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!user.is_platform_admin) {
        return <Navigate to="/dashboard" replace />;
    }

    return <MainLayout>{children}</MainLayout>;
}

// Public Route - redirects to dashboard if authenticated
function PublicRoute({ children }) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (user) {
        return <Navigate to="/dashboard" replace />;
    }

    return children;
}

// App Router with session_id detection
function AppRouter() {
    const location = useLocation();

    // Check URL fragment (not query params) for session_id - synchronous check
    if (location.hash?.includes('session_id=')) {
        return <AuthCallback />;
    }

    return (
        <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
            <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
            <Route path="/reset-password" element={<PublicRoute><ResetPasswordPage /></PublicRoute>} />
            <Route path="/privacy" element={<PrivacyPolicyPage />} />
            <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
            
            {/* Onboarding Wizard - accessible after login */}
            <Route path="/onboarding" element={<ProtectedRoute showLayout={false}><OnboardingWizard /></ProtectedRoute>} />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/employees" element={<EmployeeRestrictedRoute><EmployeesPage /></EmployeeRestrictedRoute>} />
            <Route path="/employees/new" element={<EmployeeRestrictedRoute><EmployeesPage /></EmployeeRestrictedRoute>} />
            <Route path="/employees/:id" element={<EmployeeRestrictedRoute><EmployeeDetail /></EmployeeRestrictedRoute>} />
            <Route path="/leave" element={<ProtectedRoute><LeavePage /></ProtectedRoute>} />
            <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
            <Route path="/scheduling" element={<ProtectedRoute><SchedulingPage /></ProtectedRoute>} />
            <Route path="/payroll" element={<EmployeeRestrictedRoute><PayrollPage /></EmployeeRestrictedRoute>} />
            <Route path="/payroll/new" element={<EmployeeRestrictedRoute><PayrollPage /></EmployeeRestrictedRoute>} />
            <Route path="/payroll/:id" element={<EmployeeRestrictedRoute><PayRunDetail /></EmployeeRestrictedRoute>} />
            <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
            <Route path="/settings" element={<EmployeeRestrictedRoute><SettingsPage /></EmployeeRestrictedRoute>} />
            <Route path="/import" element={<ProtectedRoute><BulkImportPage /></ProtectedRoute>} />
            <Route path="/self-service" element={<ProtectedRoute><SelfServicePortal /></ProtectedRoute>} />
            <Route path="/hmrc" element={<EmployeeRestrictedRoute><HMRCDashboard /></EmployeeRestrictedRoute>} />
            <Route path="/rti-sync" element={<ProtectedRoute><HMRCSubmissionPage /></ProtectedRoute>} />
            <Route path="/ukvi" element={<ProtectedRoute><UKVICompliancePage /></ProtectedRoute>} />
            <Route path="/enterprise" element={<ProtectedRoute><EnterprisePage /></ProtectedRoute>} />
            <Route path="/time-tracking" element={<ProtectedRoute><TimeSchedulingPage /></ProtectedRoute>} />
            <Route path="/statutory" element={<ProtectedRoute><StatutoryPaymentsPage /></ProtectedRoute>} />
            <Route path="/year-end" element={<EmployeeRestrictedRoute><YearEndPage /></EmployeeRestrictedRoute>} />
            <Route path="/admin" element={<AdminRoute><AdminPortalPage /></AdminRoute>} />
            <Route path="/super-admin" element={<SuperAdminRoute><SuperAdminPage /></SuperAdminRoute>} />
            <Route path="/performance" element={<ProtectedRoute><PerformancePage /></ProtectedRoute>} />
            <Route path="/cases" element={<ProtectedRoute><EmployeeRelationsPage /></ProtectedRoute>} />
            <Route path="/gdpr" element={<ProtectedRoute><GDPRCenterPage /></ProtectedRoute>} />
            <Route path="/security" element={<ProtectedRoute><SecurityPage /></ProtectedRoute>} />
            <Route path="/trust-badge" element={<ProtectedRoute><TrustBadgePage /></ProtectedRoute>} />
            <Route path="/trust/:badgeId" element={<TrustVerifyPage />} />
            <Route path="/policies" element={<ProtectedRoute><PoliciesPage /></ProtectedRoute>} />
            <Route path="/training" element={<ProtectedRoute><TrainingPage /></ProtectedRoute>} />
            <Route path="/absence" element={<ProtectedRoute><AbsencePage /></ProtectedRoute>} />
            <Route path="/hr-analytics" element={<ProtectedRoute><HRAnalyticsPage /></ProtectedRoute>} />
            <Route path="/dpo" element={<ProtectedRoute><DPOCenterPage /></ProtectedRoute>} />
            <Route path="/expenses" element={<ProtectedRoute><ExpensesPage /></ProtectedRoute>} />
            <Route path="/recruitment" element={<ProtectedRoute><RecruitmentPage /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
            <Route path="/invite/:token" element={<InviteAcceptPage />} />
            <Route path="/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
            <Route path="/settings/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
            
            {/* Default redirect */}
            <Route path="/" element={<LandingPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
    );
}

function App() {
    return (
        <ThemeProvider>
            <AuthProvider>
                <BrowserRouter>
                    <AppRouter />
                    <Toaster position="top-right" richColors />
                    <CookieConsent />
                </BrowserRouter>
            </AuthProvider>
        </ThemeProvider>
    );
}

export default App;
