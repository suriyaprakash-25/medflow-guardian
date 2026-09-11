import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Shield, Users, Activity, LogOut, Database } from 'lucide-react';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: Activity },
    { path: '/staff', label: 'Staff Management', icon: Users },
    { path: '/audit', label: 'Audit Explorer', icon: Database },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col fixed inset-y-0 z-10">
        <div className="h-16 flex items-center px-6 bg-slate-950 text-white font-bold text-lg border-b border-slate-800">
          <Shield className="h-6 w-6 text-blue-500 mr-2" />
          MedFlow Admin
        </div>
        
        <div className="px-6 py-4 border-b border-slate-800">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Signed in as</div>
          <div className="text-sm font-medium text-white truncate">{user?.email || 'Admin User'}</div>
          <div className="text-xs text-slate-400 mt-1 capitalize">{user?.system_role || 'Role'}</div>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-blue-600/10 text-blue-400 font-medium' 
                    : 'hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <LogOut className="h-5 w-5 text-slate-400" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 flex flex-col min-h-screen">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
          <h1 className="text-lg font-semibold text-slate-800">
            {navItems.find(i => location.pathname.startsWith(i.path))?.label || 'Admin Portal'}
          </h1>
        </header>
        <div className="flex-1 p-8 overflow-y-auto bg-slate-50">
          <div className="max-w-6xl mx-auto">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
