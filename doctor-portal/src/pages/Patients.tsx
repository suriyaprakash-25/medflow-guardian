import { useState } from 'react';
import { useDoctorContext } from '../components/Layout';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { Users, Search, Activity, ChevronRight, User } from 'lucide-react';

export default function Patients() {
  const { doctorVisits, setActivePatientId } = useDoctorContext();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  const handleSelectPatient = (patientId: number) => {
    setActivePatientId(patientId);
    navigate('/patient-details');
  };

  const filteredVisits = doctorVisits.filter(v => 
    v.patient_id.toString().includes(searchTerm) || 
    (v.hospital?.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.reason.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">My Patients</h2>
          <p className="text-sm text-slate-500 mt-1">Active and past patient encounters.</p>
        </div>
        
        <div className="relative w-full sm:w-72">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-400" />
          </div>
          <input
            type="text"
            placeholder="Search by ID, hospital, or reason..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg text-sm bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow"
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {filteredVisits.length === 0 ? (
            <div className="p-12">
              <EmptyState 
                icon={<Users className="h-10 w-10 text-slate-300" />}
                title={doctorVisits.length === 0 ? "No active patients" : "No results found"}
                description={
                  doctorVisits.length === 0 
                    ? "You haven't been assigned any patients yet." 
                    : "Try adjusting your search terms."
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500 font-semibold">
                    <th className="px-6 py-4">Patient</th>
                    <th className="px-6 py-4">Hospital Context</th>
                    <th className="px-6 py-4">Reason for Visit</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredVisits.map(v => (
                    <tr 
                      key={v.id} 
                      className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                      onClick={() => handleSelectPatient(v.patient_id)}
                    >
                      <td className="px-6 py-4 align-middle">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold shrink-0">
                            <User className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900 text-sm">Patient #{v.patient_id * 13}</div>
                            <div className="text-xs text-slate-500 font-mono mt-0.5">ID: {v.patient_id}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 align-middle">
                        <div className="text-sm font-medium text-slate-800">{v.hospital?.name || 'Unknown'}</div>
                        <div className="text-xs text-slate-500">Visit #{v.id}</div>
                      </td>
                      <td className="px-6 py-4 align-middle">
                        <div className="text-sm text-slate-600 truncate max-w-[200px]" title={v.reason}>
                          {v.reason}
                        </div>
                      </td>
                      <td className="px-6 py-4 align-middle">
                        <Badge variant={v.status === 'Active' ? 'default' : 'secondary'} className={v.status === 'Active' ? 'bg-blue-100 text-blue-700 hover:bg-blue-100 border-none' : ''}>
                          <Activity className="w-3 h-3 mr-1" />
                          {v.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 align-middle text-right">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 font-medium group-hover:translate-x-1 transition-transform"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectPatient(v.patient_id);
                          }}
                        >
                          View Details <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
