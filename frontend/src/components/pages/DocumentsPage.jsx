import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { 
    Plus, 
    FileText,
    File,
    Download,
    Eye
} from 'lucide-react';
import { cn, formatDate, getStatusColor } from '../../lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const docTypes = [
    { value: 'contract', label: 'Employment Contract' },
    { value: 'policy', label: 'Company Policy' },
    { value: 'handbook', label: 'Employee Handbook' },
    { value: 'offer_letter', label: 'Offer Letter' },
    { value: 'nda', label: 'NDA' },
    { value: 'other', label: 'Other' }
];

export default function DocumentsPage() {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        doc_type: '',
        content: ''
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/documents`, { withCredentials: true });
            setDocuments(response.data);
        } catch (error) {
            toast.error('Failed to load documents');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await axios.post(`${API_URL}/api/documents`, formData, { withCredentials: true });
            toast.success('Document created successfully');
            setDialogOpen(false);
            setFormData({ name: '', doc_type: '', content: '' });
            fetchDocuments();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to create document');
        } finally {
            setSubmitting(false);
        }
    };

    const getDocIcon = (type) => {
        switch (type) {
            case 'contract':
            case 'offer_letter':
                return FileText;
            default:
                return File;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="documents-page">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold font-['Plus_Jakarta_Sans']">Documents</h1>
                    <p className="text-muted-foreground mt-1">Manage company policies, contracts, and templates</p>
                </div>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="create-doc-btn">
                            <Plus className="w-4 h-4 mr-2" />
                            Create Document
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[600px]">
                        <DialogHeader>
                            <DialogTitle>Create New Document</DialogTitle>
                            <DialogDescription>
                                Create a new document or template
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Document Name</Label>
                                <Input
                                    id="name"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    required
                                    placeholder="e.g. Employee Handbook 2024"
                                    data-testid="input-doc-name"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Document Type</Label>
                                <Select
                                    value={formData.doc_type}
                                    onValueChange={(value) => setFormData({ ...formData, doc_type: value })}
                                >
                                    <SelectTrigger data-testid="select-doc-type">
                                        <SelectValue placeholder="Select document type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {docTypes.map(type => (
                                            <SelectItem key={type.value} value={type.value}>
                                                {type.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="content">Content</Label>
                                <Textarea
                                    id="content"
                                    value={formData.content}
                                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    placeholder="Enter document content..."
                                    rows={8}
                                    data-testid="input-doc-content"
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={submitting} data-testid="submit-doc-btn">
                                    {submitting ? 'Creating...' : 'Create Document'}
                                </Button>
                            </div>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Documents Grid */}
            {documents.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <FileText className="w-16 h-16 mx-auto text-muted-foreground/50" />
                        <h3 className="mt-4 text-lg font-semibold">No documents yet</h3>
                        <p className="text-muted-foreground mt-1">
                            Create your first document or template
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {documents.map((doc) => {
                        const Icon = getDocIcon(doc.doc_type);
                        return (
                            <Card 
                                key={doc.document_id} 
                                className="hover:shadow-md transition-all hover-lift"
                                data-testid={`doc-card-${doc.document_id}`}
                            >
                                <CardContent className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="p-3 rounded-xl bg-indigo-100 dark:bg-indigo-900/30">
                                            <Icon className="w-6 h-6 text-indigo-600" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-semibold truncate">{doc.name}</h3>
                                            <p className="text-sm text-muted-foreground capitalize">
                                                {doc.doc_type.replace('_', ' ')}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="mt-4 flex items-center justify-between">
                                        <Badge className={getStatusColor(doc.status)}>{doc.status}</Badge>
                                        <span className="text-xs text-muted-foreground">
                                            {formatDate(doc.created_at)}
                                        </span>
                                    </div>
                                    <div className="mt-4 pt-4 border-t border-border flex gap-2">
                                        <Button variant="outline" size="sm" className="flex-1">
                                            <Eye className="w-4 h-4 mr-1" />
                                            View
                                        </Button>
                                        <Button variant="outline" size="sm" className="flex-1">
                                            <Download className="w-4 h-4 mr-1" />
                                            Export
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
