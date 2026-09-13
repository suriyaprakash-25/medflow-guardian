import { useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { ResponsiveTable } from '@shared/ui/ResponsiveTable';
import { Users, Search, Activity, ChevronRight, User } from 'lucide-react';

export default function Patients() {
  const { doctorVisits, setActivePatientId } = useDoctorContext();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  const handleSelectPatient = (patientId: number) => {
    setActivePatientId(patientId);
    navigate('/patient-details');
  };

  const filteredVisits = doctorVisits.filter((visit) =>
    visit.patient_id.toString().includes(searchTerm) ||
    (visit.hospital?.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (visit.reason || '').toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-950">My patients</h2>
          <p className="mt-1 text-sm text-slate-600">Patients shown here come from visits assigned to your authenticated clinician context.</p>
        </div>
        <div className="w-full sm:w-80">
          <FormField id="patient-search" label="Search patient visits">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-500" aria-hidden="true" />
              <Input id="patient-search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Patient ID, hospital, or visit reason" className="pl-10" />
            </div>
          </FormField>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {filteredVisits.length === 0 ? (
            <div className="p-8 sm:p-12">
              <EmptyState
                icon={<Users className="h-10 w-10 text-slate-400" />}
                title={doctorVisits.length === 0 ? 'No assigned patient visits' : 'No matching patient visits'}
                description={doctorVisits.length === 0 ? 'No visits are currently assigned to this clinician account.' : 'Change the search terms and try again.'}
              />
            </div>
          ) : (
            <ResponsiveTable label="Assigned patient visits">
              <table className="mobile-card-table w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-600">
                    <th scope="col" className="px-6 py-4">Patient</th>
                    <th scope="col" className="px-6 py-4">Hospital context</th>
                    <th scope="col" className="px-6 py-4">Reason for visit</th>
                    <th scope="col" className="px-6 py-4">Visit status</th>
                    <th scope="col" className="px-6 py-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredVisits.map((visit) => (
                    <tr key={visit.id} className="hover:bg-slate-50">
                      <td data-label="Patient" className="px-6 py-4 align-middle">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700"><User className="h-5 w-5" aria-hidden="true" /></div>
                          <div>
                            <div className="text-sm font-semibold text-slate-950">Patient ID {visit.patient_id}</div>
                            <div className="mt-0.5 text-xs text-slate-500">Authoritative system identifier</div>
                          </div>
                        </div>
                      </td>
                      <td data-label="Hospital context" className="px-6 py-4 align-middle">
                        <div className="text-sm font-medium text-slate-800">{visit.hospital?.name || `Hospital ID ${visit.hospital_id}`}</div>
                        <div className="text-xs text-slate-500">Visit ID {visit.id}</div>
                      </td>
                      <td data-label="Reason for visit" className="px-6 py-4 align-middle"><div className="max-w-[18rem] text-sm text-slate-700">{visit.reason || 'Not recorded'}</div></td>
                      <td data-label="Visit status" className="px-6 py-4 align-middle">
                        <Badge variant="secondary"><Activity className="mr-1 h-3 w-3" aria-hidden="true" />{visit.status}</Badge>
                      </td>
                      <td data-label="Action" className="px-6 py-4 text-right align-middle">
                        <Button variant="ghost" size="sm" onClick={() => handleSelectPatient(visit.patient_id)} className="text-blue-700 hover:bg-blue-50 hover:text-blue-800">
                          Open patient workspace <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ResponsiveTable>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
