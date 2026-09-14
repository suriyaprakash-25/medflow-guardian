import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, ShieldAlert, LogOut, ShieldCheck, Settings, Building } from 'lucide-react';
import { api, clearAccessToken } from '../lib/api';

interface StoredAdminUser {
  full_name?: string;
  email?: string;
  role?: string;
  system_role?: string;
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  let user: StoredAdminUser = {};
  try { user = JSON.parse(localStorage.getItem('user') || '{}') as StoredAdminUser; } catch { user = {}; }

  const handleLogout = async () => {
    try { await api.post('/api/auth/logout'); }
    catch (error) { console.error('Failed to revoke server session during logout', error); }
    finally {
      clearAccessToken();
      localStorage.removeItem('user');
      navigate('/login');
    }
  };

  const isPlatformAdmin = user.system_role === 'platform_admin' || user.role === 'platform_admin';
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    ...(isPlatformAdmin ? [{ name: 'Organizations', path: '/organizations', icon: Building }] : []),
    { name: 'Staff', path: '/staff', icon: Users },
    { name: 'Audit', path: '/audit', icon: ShieldAlert },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  const pageTitle = navItems.find((item) => location.pathname.startsWith(item.path))?.name || 'Administration';

  return (
    <div className="flex h-screen max-w-full overflow-x-hidden bg-slate-50 font-sans">
      <a href="#admin-main" className="skip-link">Skip to main content</a>
      <aside className="relative z-20 hidden w-72 shrink-0 flex-col bg-slate-950 text-white shadow-2xl md:flex" aria-label="Admin navigation">
        <div className="flex items-center gap-3 border-b border-slate-800 p-6">
          <div className="rounded-xl bg-blue-700 p-2"><ShieldCheck className="h-7 w-7 text-white" aria-hidden="true" /></div>
          <div><h1 className="text-xl font-bold tracking-tight">MedFlow</h1><p className="mt-0.5 text-xs font-semibold uppercase tracking-wider text-blue-300">Guardian console</p></div>
        </div>
        <div className="px-6 py-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
            <div className="truncate text-sm font-semibold text-slate-100">{user.full_name || user.email || 'Administrator'}</div>
            <div className="mt-1 text-xs text-slate-400">{isPlatformAdmin ? 'Platform administrator' : 'Organization administrator'}</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.path} to={item.path} className={({ isActive }) => `flex min-h-11 items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-blue-400 ${isActive ? 'bg-blue-700 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}>
                <Icon className="h-5 w-5" aria-hidden="true" />{item.name}
              </NavLink>
            );
          })}
        </nav>
        <div className="border-t border-slate-800 p-4">
          <button type="button" onClick={() => void handleLogout()} className="flex min-h-11 w-full items-center gap-3 rounded-xl px-4 py-3 text-rose-300 transition-colors hover:bg-rose-500/10 hover:text-rose-200 focus-visible:ring-2 focus-visible:ring-rose-300">
            <LogOut className="h-5 w-5" aria-hidden="true" />Secure logout
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-x-hidden">
        <header className="sticky top-0 z-30 flex min-h-16 min-w-0 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-sm md:px-8">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-700 md:hidden">MedFlow admin</p>
            <h2 className="truncate text-lg font-semibold text-slate-900">{pageTitle}</h2>
          </div>
          <p className="hidden text-xs text-slate-500 sm:block">Administrative changes are server-authorized and audited.</p>
        </header>
        <main id="admin-main" className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto bg-slate-50/50 p-4 pb-28 md:p-8 md:pb-8" tabIndex={-1}>
          <div className="mx-auto min-w-0 max-w-6xl"><Outlet /></div>
        </main>

        <nav className="safe-bottom fixed inset-x-0 bottom-0 z-40 max-w-full border-t border-slate-200 bg-white/95 shadow-[0_-8px_24px_rgba(15,23,42,0.08)] backdrop-blur md:hidden" aria-label="Admin mobile navigation">
          <div className="flex max-w-full overflow-x-auto px-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname.startsWith(item.path);
              return (
                <NavLink key={item.path} to={item.path} aria-current={active ? 'page' : undefined} className={`flex min-h-16 min-w-[5.25rem] flex-1 flex-col items-center justify-center gap-1 px-2 text-[11px] font-semibold ${active ? 'text-blue-800' : 'text-slate-600'}`}>
                  <Icon className="h-5 w-5" aria-hidden="true" />{item.name}
                </NavLink>
              );
            })}
            <button type="button" onClick={() => void handleLogout()} className="flex min-h-16 min-w-[5.25rem] flex-1 flex-col items-center justify-center gap-1 px-2 text-[11px] font-semibold text-rose-700"><LogOut className="h-5 w-5" aria-hidden="true" />Logout</button>
          </div>
        </nav>
      </div>
    </div>
  );
}
