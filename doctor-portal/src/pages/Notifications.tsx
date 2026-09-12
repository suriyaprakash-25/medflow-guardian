import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Bell, Check, Circle, CheckCircle2 } from 'lucide-react';
import { EmptyState } from '@shared/ui/EmptyState';

export default function Notifications() {
  const { notifications, handleMarkRead, handleMarkAllRead } = useDoctorContext();
  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Notifications</h2>
          <p className="text-sm text-slate-500 mt-1">Updates on your access requests and triage alerts.</p>
        </div>
        {unreadCount > 0 && (
          <Button 
            variant="outline" 
            onClick={handleMarkAllRead}
            className="text-blue-600 border-blue-200 hover:bg-blue-50"
          >
            <Check className="h-4 w-4 mr-2" /> Mark all read
          </Button>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          {notifications.length === 0 ? (
            <div className="p-12">
              <EmptyState 
                icon={<Bell className="h-10 w-10 text-slate-300" />}
                title="You're all caught up"
                description="There are no notifications for you at this time."
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
                      : 'bg-blue-50/50 cursor-pointer hover:bg-blue-50'
                  }`}
                >
                  <div className="mt-1 shrink-0">
                    {n.is_read ? (
                      <CheckCircle2 className="h-5 w-5 text-slate-300" />
                    ) : (
                      <div className="relative">
                        <Circle className="h-5 w-5 text-blue-600" />
                        <span className="absolute top-1.5 left-1.5 h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-1">
                    <p className={`text-sm mb-1 ${n.is_read ? 'text-slate-600' : 'text-slate-900 font-semibold'}`}>
                      {n.message}
                    </p>
                    <span className="text-xs font-medium text-slate-400">
                      {new Date(n.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  </div>
                  
                  {!n.is_read && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-xs text-slate-400 hover:text-blue-600 shrink-0 h-8"
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
