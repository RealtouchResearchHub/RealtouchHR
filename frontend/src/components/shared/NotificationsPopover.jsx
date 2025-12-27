import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '../ui/popover';
import { 
    Bell,
    CheckCircle2,
    XCircle,
    Calendar,
    CreditCard,
    Users,
    CheckCheck
} from 'lucide-react';
import { cn, formatDateTime } from '../../lib/utils';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const notificationIcons = {
    leave_approved: CheckCircle2,
    leave_rejected: XCircle,
    payroll: CreditCard,
    employee: Users,
    default: Bell
};

const notificationColors = {
    leave_approved: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30',
    leave_rejected: 'text-rose-600 bg-rose-100 dark:bg-rose-900/30',
    payroll: 'text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30',
    employee: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
    default: 'text-slate-600 bg-slate-100 dark:bg-slate-900/30'
};

export default function NotificationsPopover() {
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);

    const fetchNotifications = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/notifications`, { withCredentials: true });
            setNotifications(response.data.notifications || []);
            setUnreadCount(response.data.unread_count || 0);
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
        }
    };

    useEffect(() => {
        fetchNotifications();
        // Poll for new notifications every 30 seconds
        const interval = setInterval(fetchNotifications, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleMarkAllRead = async () => {
        setLoading(true);
        try {
            await axios.put(`${API_URL}/api/notifications/read-all`, {}, { withCredentials: true });
            setUnreadCount(0);
            setNotifications(prev => prev.map(n => ({ ...n, read: true })));
        } catch (error) {
            console.error('Failed to mark all as read:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleMarkRead = async (notificationId) => {
        try {
            await axios.put(`${API_URL}/api/notifications/${notificationId}/read`, {}, { withCredentials: true });
            setNotifications(prev => prev.map(n => 
                n.notification_id === notificationId ? { ...n, read: true } : n
            ));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error('Failed to mark as read:', error);
        }
    };

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="relative rounded-full" data-testid="notifications-btn">
                    <Bell className="w-5 h-5" />
                    {unreadCount > 0 && (
                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-rose-500 text-white text-xs rounded-full flex items-center justify-center">
                            {unreadCount > 9 ? '9+' : unreadCount}
                        </span>
                    )}
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-0" align="end">
                <div className="flex items-center justify-between p-4 border-b">
                    <h3 className="font-semibold">Notifications</h3>
                    {unreadCount > 0 && (
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={handleMarkAllRead}
                            disabled={loading}
                            data-testid="mark-all-read-btn"
                        >
                            <CheckCheck className="w-4 h-4 mr-1" />
                            Mark all read
                        </Button>
                    )}
                </div>
                
                <ScrollArea className="h-[400px]">
                    {notifications.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                            <Bell className="w-10 h-10 mx-auto opacity-50 mb-2" />
                            <p>No notifications yet</p>
                        </div>
                    ) : (
                        <div className="divide-y">
                            {notifications.map((notification) => {
                                const Icon = notificationIcons[notification.notification_type] || notificationIcons.default;
                                const colorClass = notificationColors[notification.notification_type] || notificationColors.default;
                                
                                return (
                                    <div 
                                        key={notification.notification_id}
                                        className={cn(
                                            "p-4 hover:bg-accent/50 transition-colors cursor-pointer",
                                            !notification.read && "bg-indigo-50/50 dark:bg-indigo-950/20"
                                        )}
                                        onClick={() => !notification.read && handleMarkRead(notification.notification_id)}
                                    >
                                        <div className="flex gap-3">
                                            <div className={cn("p-2 rounded-lg flex-shrink-0", colorClass)}>
                                                <Icon className="w-4 h-4" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-2">
                                                    <p className={cn("font-medium text-sm", !notification.read && "text-foreground")}>
                                                        {notification.title}
                                                    </p>
                                                    {!notification.read && (
                                                        <span className="w-2 h-2 rounded-full bg-indigo-600 flex-shrink-0 mt-1" />
                                                    )}
                                                </div>
                                                <p className="text-sm text-muted-foreground line-clamp-2">
                                                    {notification.message}
                                                </p>
                                                <p className="text-xs text-muted-foreground mt-1">
                                                    {formatDateTime(notification.created_at)}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </ScrollArea>
            </PopoverContent>
        </Popover>
    );
}
