import React, { useState, useEffect } from 'react';
import { api as axios } from '../lib/api';
import { Calendar, Clock, MapPin, User as UserIcon } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useDoctorContext } from '../components/Layout';

export default function Appointments() {
  const { currentUser } = useDoctorContext();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAppointments = async () => {
    if (!currentUser?.id) return;
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`/api/appointments/doctor/${currentUser.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAppointments(res.data);
    } catch (error) {
      toast.error('Failed to load appointments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, [currentUser?.id]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading appointments...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Patient Appointments</h2>
          <p className="text-sm text-slate-500">Manage your upcoming schedules.</p>
        </div>
      </div>

      {appointments.length === 0 ? (
        <div className="bg-white rounded-lg border border-border p-12 text-center">
          <Calendar className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-900 mb-1">No Appointments</h3>
          <p className="text-slate-500">You do not have any scheduled appointments.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {appointments.map(apt => (
            <div key={apt.id} className="bg-white rounded-lg border border-border shadow-sm p-5 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                  <div className="bg-primary/10 p-2 rounded-lg text-primary">
                    <Calendar className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {new Date(apt.scheduled_time).toLocaleDateString()}
                    </p>
                    <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                      <Clock className="h-3 w-3" />
                      {new Date(apt.scheduled_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </div>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  apt.status === 'scheduled' ? 'bg-blue-100 text-blue-700' :
                  apt.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {apt.status.charAt(0).toUpperCase() + apt.status.slice(1)}
                </span>
              </div>
              
              <div className="space-y-3 pt-4 border-t border-slate-100">
                <div className="flex items-start gap-2">
                  <UserIcon className="h-4 w-4 text-slate-400 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium text-slate-700">Patient ID: {apt.patient_id}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <MapPin className="h-4 w-4 text-slate-400 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium text-slate-700">Hospital ID: {apt.hospital_id}</p>
                  </div>
                </div>
                {apt.reason && (
                  <div className="bg-slate-50 p-3 rounded-md mt-2">
                    <p className="text-xs text-slate-600 font-medium">Reason for visit:</p>
                    <p className="text-sm text-slate-800 mt-1">{apt.reason}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
