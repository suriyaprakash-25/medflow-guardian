
import { usePatientContext } from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Bell, Check, CheckCircle2, Circle } from 'lucide-react';
import { EmptyState } from '@shared/ui/EmptyState';

export default function Notifications() {
  const { notifications, handleMarkRead, handleMarkAllRead } = usePatientContext();

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="max-w-4xl mx-auto animate-in fade-in duration-500">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100 pb-4">
          <CardTitle className="flex items-center gap-2 text-xl">
            <Bell className="h-5 w-5 text-slate-800" />
            Notifications
            {unreadCount > 0 && (
              <span className="ml-2 bg-primary text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </CardTitle>
          {unreadCount > 0 && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleMarkAllRead}
              className="text-primary border-primary/20 hover:bg-primary/5"
            >
              <Check className="h-4 w-4 mr-1.5" /> Mark all read
            </Button>
          )}
        </CardHeader>
        
        <CardContent className="p-0">
          {notifications.length === 0 ? (
            <div className="p-8">
              <EmptyState 
                icon={<Bell className="h-10 w-10 text-slate-300" />} 
                title="You're all caught up" 
                description="You don't have any new notifications." 
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {notifications.map(n => (
                <div 
                  key={n.id} 
                  onClick={() => !n.is_read && handleMarkRead(n.id)}
                  className={`p-4 flex items-start gap-4 transition-colors ${
                    n.is_read 
                      ? 'bg-white hover:bg-slate-50' 
                      : 'bg-primary/5 cursor-pointer hover:bg-primary/10'
                  }`}
                >
                  <div className="mt-1 shrink-0">
                    {n.is_read ? (
                      <CheckCircle2 className="h-5 w-5 text-slate-300" />
                    ) : (
                      <div className="relative">
                        <Circle className="h-5 w-5 text-primary" />
                        <span className="absolute top-1.5 left-1.5 h-2 w-2 rounded-full bg-primary" />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-1">
                    <p className={`text-sm mb-1 ${n.is_read ? 'text-slate-600' : 'text-slate-900 font-semibold'}`}>
                      {n.message}
                    </p>
                    <span className="text-xs text-slate-400">
                      {new Date(n.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  </div>
                  
                  {!n.is_read && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-xs text-slate-500 hover:text-primary shrink-0"
                    >
                      Mark read
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
