import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { X, Send, Bot, User, AlertTriangle, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function AICopilot({ open, onClose }) {
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: "Hello! I'm your RealtouchHR AI Copilot. I can help you with HR processes, payroll guidance, compliance questions, and more. How can I assist you today?",
            suggestions: ['How do I add a new employee?', 'What are UK payroll requirements?', 'Check my compliance status']
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const sendMessage = async (text = input) => {
        if (!text.trim() || loading) return;

        const userMessage = { role: 'user', content: text };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await axios.post(`${API_URL}/api/copilot/chat`, 
                { message: text },
                { withCredentials: true }
            );

            const assistantMessage = {
                role: 'assistant',
                content: response.data.response,
                suggestions: response.data.suggestions,
                requiresApproval: response.data.requires_approval
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "I'm sorry, I encountered an error. Please try again.",
                isError: true
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    if (!open) return null;

    return (
        <>
            {/* Backdrop */}
            <div 
                className="fixed inset-0 z-50 bg-black/50"
                onClick={onClose}
            />

            {/* Sidebar */}
            <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-card border-l border-border shadow-2xl flex flex-col" data-testid="ai-copilot-panel">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 flex items-center justify-center">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="font-semibold font-['Plus_Jakarta_Sans']">AI Copilot</h2>
                            <p className="text-xs text-muted-foreground">HR & Payroll Assistant</p>
                        </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose} data-testid="close-copilot-btn">
                        <X className="w-5 h-5" />
                    </Button>
                </div>

                {/* Messages */}
                <ScrollArea className="flex-1 p-4" ref={scrollRef}>
                    <div className="space-y-4">
                        {messages.map((message, index) => (
                            <div key={index} className={cn(
                                "flex gap-3",
                                message.role === 'user' ? "flex-row-reverse" : ""
                            )}>
                                <div className={cn(
                                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                                    message.role === 'user' 
                                        ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300"
                                        : "bg-gradient-to-r from-indigo-600 to-purple-600 text-white"
                                )}>
                                    {message.role === 'user' ? (
                                        <User className="w-4 h-4" />
                                    ) : (
                                        <Sparkles className="w-4 h-4" />
                                    )}
                                </div>
                                <div className={cn(
                                    "flex-1 space-y-2",
                                    message.role === 'user' ? "text-right" : ""
                                )}>
                                    <div className={cn(
                                        "inline-block rounded-2xl px-4 py-2 max-w-[90%]",
                                        message.role === 'user' 
                                            ? "bg-indigo-600 text-white"
                                            : message.isError 
                                                ? "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300"
                                                : "bg-muted"
                                    )}>
                                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                                    </div>

                                    {message.requiresApproval && (
                                        <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 text-xs">
                                            <AlertTriangle className="w-3 h-3" />
                                            <span>This action requires your approval</span>
                                        </div>
                                    )}

                                    {message.suggestions?.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mt-2">
                                            {message.suggestions.map((suggestion, sIndex) => (
                                                <button
                                                    key={sIndex}
                                                    onClick={() => sendMessage(suggestion)}
                                                    className="text-xs px-3 py-1.5 rounded-full bg-indigo-100 text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-900/50 transition-colors"
                                                >
                                                    {suggestion}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {loading && (
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 flex items-center justify-center">
                                    <Sparkles className="w-4 h-4 text-white animate-pulse" />
                                </div>
                                <div className="bg-muted rounded-2xl px-4 py-2">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>

                {/* Input */}
                <div className="p-4 border-t border-border">
                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask me anything about HR or payroll..."
                            disabled={loading}
                            className="flex-1"
                            data-testid="copilot-input"
                        />
                        <Button 
                            onClick={() => sendMessage()} 
                            disabled={!input.trim() || loading}
                            size="icon"
                            data-testid="copilot-send-btn"
                        >
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2 text-center">
                        AI suggestions are for guidance only. Always verify legal and tax advice.
                    </p>
                </div>
            </div>
        </>
    );
}
