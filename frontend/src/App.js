import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { Toaster } from './components/ui/sonner';

// Pages
import LoginPage from './components/pages/LoginPage';
import RegisterPage from './components/pages/RegisterPage';
import AuthCallback from './components/pages/AuthCallback';
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

// Layout
import MainLayout from './components/layout/MainLayout';

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
            
            {/* Onboarding Wizard - accessible after login */}
            <Route path="/onboarding" element={<ProtectedRoute showLayout={false}><OnboardingWizard /></ProtectedRoute>} />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/employees" element={<ProtectedRoute><EmployeesPage /></ProtectedRoute>} />
            <Route path="/employees/new" element={<ProtectedRoute><EmployeesPage /></ProtectedRoute>} />
            <Route path="/employees/:id" element={<ProtectedRoute><EmployeeDetail /></ProtectedRoute>} />
            <Route path="/leave" element={<ProtectedRoute><LeavePage /></ProtectedRoute>} />
            <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
            <Route path="/scheduling" element={<ProtectedRoute><SchedulingPage /></ProtectedRoute>} />
            <Route path="/payroll" element={<ProtectedRoute><PayrollPage /></ProtectedRoute>} />
            <Route path="/payroll/new" element={<ProtectedRoute><PayrollPage /></ProtectedRoute>} />
            <Route path="/payroll/:id" element={<ProtectedRoute><PayRunDetail /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="/import" element={<ProtectedRoute><BulkImportPage /></ProtectedRoute>} />
            <Route path="/self-service" element={<ProtectedRoute><SelfServicePortal /></ProtectedRoute>} />
            <Route path="/hmrc" element={<ProtectedRoute><HMRCDashboard /></ProtectedRoute>} />
            <Route path="/rti-sync" element={<ProtectedRoute><HMRCSubmissionPage /></ProtectedRoute>} />
            <Route path="/ukvi" element={<ProtectedRoute><UKVICompliancePage /></ProtectedRoute>} />
            <Route path="/enterprise" element={<ProtectedRoute><EnterprisePage /></ProtectedRoute>} />
            <Route path="/time-tracking" element={<ProtectedRoute><TimeSchedulingPage /></ProtectedRoute>} />
            <Route path="/statutory" element={<ProtectedRoute><StatutoryPaymentsPage /></ProtectedRoute>} />
            <Route path="/year-end" element={<ProtectedRoute><YearEndPage /></ProtectedRoute>} />
            <Route path="/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
            <Route path="/settings/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
            
            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/login" replace />} />
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
                </BrowserRouter>
            </AuthProvider>
        </ThemeProvider>
    );
}

export default App;
