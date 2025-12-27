import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import { 
    Upload,
    Download,
    FileText,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Users,
    Clock
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function BulkImportPage() {
    const [importing, setImporting] = useState(false);
    const [result, setResult] = useState(null);
    const [importType, setImportType] = useState('employees');
    const fileInputRef = useRef(null);

    const handleFileSelect = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.name.endsWith('.csv')) {
            toast.error('Please select a CSV file');
            return;
        }

        setImporting(true);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const endpoint = importType === 'employees' 
                ? `${API_URL}/api/employees/import`
                : `${API_URL}/api/timesheets/import`;

            const response = await axios.post(endpoint, formData, {
                withCredentials: true,
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setResult(response.data);
            
            if (response.data.success_count > 0) {
                toast.success(`Successfully imported ${response.data.success_count} records`);
            }
            if (response.data.error_count > 0) {
                toast.warning(`${response.data.error_count} records had errors`);
            }
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Import failed');
        } finally {
            setImporting(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/employees/import/template`, {
                withCredentials: true,
                responseType: 'blob'
            });
            
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'employee_import_template.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            toast.error('Failed to download template');
        }
    };

    return (
        <div className="space-y-6" data-testid="bulk-import-page">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Bulk Import</h1>
                <p className="text-muted-foreground mt-1">Import employees and timesheets from CSV files</p>
            </div>

            {/* Import Type Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card 
                    className={`cursor-pointer transition-all ${importType === 'employees' ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'hover:border-indigo-300'}`}
                    onClick={() => setImportType('employees')}
                    data-testid="import-type-employees"
                >
                    <CardContent className="p-6 flex items-center gap-4">
                        <div className={`p-3 rounded-xl ${importType === 'employees' ? 'bg-indigo-100 dark:bg-indigo-900/50' : 'bg-muted'}`}>
                            <Users className={`w-6 h-6 ${importType === 'employees' ? 'text-indigo-600' : 'text-muted-foreground'}`} />
                        </div>
                        <div>
                            <h3 className="font-semibold">Import Employees</h3>
                            <p className="text-sm text-muted-foreground">Bulk add employees from CSV</p>
                        </div>
                    </CardContent>
                </Card>

                <Card 
                    className={`cursor-pointer transition-all ${importType === 'timesheets' ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'hover:border-indigo-300'}`}
                    onClick={() => setImportType('timesheets')}
                    data-testid="import-type-timesheets"
                >
                    <CardContent className="p-6 flex items-center gap-4">
                        <div className={`p-3 rounded-xl ${importType === 'timesheets' ? 'bg-indigo-100 dark:bg-indigo-900/50' : 'bg-muted'}`}>
                            <Clock className={`w-6 h-6 ${importType === 'timesheets' ? 'text-indigo-600' : 'text-muted-foreground'}`} />
                        </div>
                        <div>
                            <h3 className="font-semibold">Import Timesheets</h3>
                            <p className="text-sm text-muted-foreground">Bulk add timesheet entries</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Upload Area */}
            <Card>
                <CardHeader>
                    <CardTitle>Upload CSV File</CardTitle>
                    <CardDescription>
                        {importType === 'employees' 
                            ? 'Required columns: first_name, last_name, email. Optional: job_title, department, salary, ni_number, tax_code, bank_account, bank_sort_code'
                            : 'Required columns: employee_email, week_start, hours_worked. Optional: overtime_hours'
                        }
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Download Template */}
                    {importType === 'employees' && (
                        <Button variant="outline" onClick={handleDownloadTemplate} data-testid="download-template-btn">
                            <Download className="w-4 h-4 mr-2" />
                            Download Template
                        </Button>
                    )}

                    {/* Upload Zone */}
                    <div 
                        className="border-2 border-dashed border-border rounded-xl p-12 text-center hover:border-indigo-400 transition-colors cursor-pointer"
                        onClick={() => fileInputRef.current?.click()}
                        data-testid="upload-zone"
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv"
                            onChange={handleFileSelect}
                            className="hidden"
                            data-testid="file-input"
                        />
                        <Upload className="w-12 h-12 mx-auto text-muted-foreground" />
                        <p className="mt-4 font-medium">Click to upload or drag and drop</p>
                        <p className="text-sm text-muted-foreground mt-1">CSV files only</p>
                    </div>

                    {/* Importing Progress */}
                    {importing && (
                        <div className="space-y-2">
                            <p className="text-sm font-medium">Importing...</p>
                            <Progress value={50} className="animate-pulse" />
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Results */}
            {result && (
                <Card data-testid="import-results">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            {result.error_count === 0 ? (
                                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                            ) : result.success_count === 0 ? (
                                <XCircle className="w-5 h-5 text-rose-600" />
                            ) : (
                                <AlertTriangle className="w-5 h-5 text-amber-600" />
                            )}
                            Import Results
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30">
                                <p className="text-sm text-emerald-600 dark:text-emerald-400">Successful</p>
                                <p className="text-3xl font-bold text-emerald-700 dark:text-emerald-300">{result.success_count}</p>
                            </div>
                            <div className="p-4 rounded-lg bg-rose-50 dark:bg-rose-950/30">
                                <p className="text-sm text-rose-600 dark:text-rose-400">Errors</p>
                                <p className="text-3xl font-bold text-rose-700 dark:text-rose-300">{result.error_count}</p>
                            </div>
                        </div>

                        {result.errors?.length > 0 && (
                            <div className="space-y-2">
                                <p className="font-medium text-rose-600">Error Details:</p>
                                <ul className="space-y-1 text-sm">
                                    {result.errors.map((error, index) => (
                                        <li key={index} className="text-rose-600 dark:text-rose-400">
                                            • {error}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
