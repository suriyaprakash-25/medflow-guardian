import React, { useState } from 'react';
import { Save, Key, Shield, User, Bell } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Settings() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    fullName: user.full_name || '',
    email: user.email || '',
    notificationsEnabled: true,
    twoFactorEnabled: false
  });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const updatedUser = { ...user, full_name: formData.fullName, email: formData.email };
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      toast.success('Settings updated successfully');
    } catch (err) {
      toast.error('Failed to update settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Platform Settings</h2>
        <p className="text-slate-500 mt-1 font-medium">Manage your administrative account and security preferences.</p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <form onSubmit={handleSave}>
          <div className="p-6 space-y-8">
            
            {/* Profile Section */}
            <section className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <User className="h-5 w-5 text-blue-600" />
                <h3 className="text-lg font-bold text-slate-800">Profile Information</h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={formData.fullName}
                    onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                    className="w-full px-4 py-2 border border-slate-200 rounded-xl bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full px-4 py-2 border border-slate-200 rounded-xl bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  />
                </div>
              </div>
            </section>

            {/* Security Section */}
            <section className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Shield className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-bold text-slate-800">Security Preferences</h3>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl bg-slate-50">
                  <div>
                    <h4 className="font-semibold text-slate-800">Two-Factor Authentication</h4>
                    <p className="text-sm text-slate-500">Require a security key or authenticator app when logging in.</p>
                  </div>
                  <button 
                    type="button"
                    onClick={() => setFormData({...formData, twoFactorEnabled: !formData.twoFactorEnabled})}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${formData.twoFactorEnabled ? 'bg-blue-600' : 'bg-slate-300'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${formData.twoFactorEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl bg-slate-50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-200 rounded-lg">
                      <Key className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800">Change Password</h4>
                      <p className="text-sm text-slate-500">Update your administrative master password.</p>
                    </div>
                  </div>
                  <button type="button" className="px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg shadow-sm hover:bg-slate-50 transition-colors">
                    Update
                  </button>
                </div>
              </div>
            </section>

            {/* Notifications Section */}
            <section className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Bell className="h-5 w-5 text-emerald-600" />
                <h3 className="text-lg font-bold text-slate-800">Alerts & Notifications</h3>
              </div>
              
              <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl bg-slate-50">
                <div>
                  <h4 className="font-semibold text-slate-800">Security Alerts</h4>
                  <p className="text-sm text-slate-500">Receive email alerts for critical security events and denied access attempts.</p>
                </div>
                <button 
                  type="button"
                  onClick={() => setFormData({...formData, notificationsEnabled: !formData.notificationsEnabled})}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${formData.notificationsEnabled ? 'bg-emerald-500' : 'bg-slate-300'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${formData.notificationsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>
            </section>

          </div>

          <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
            <button type="button" className="px-5 py-2.5 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors">
              Discard Changes
            </button>
            <button 
              type="submit" 
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm transition-colors disabled:opacity-50"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save Preferences
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
