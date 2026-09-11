import { useEffect, useRef } from 'react';
import { usePatientContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Input } from '@shared/ui/Input';
import { Select } from '@shared/ui/Select';
import { HeartPulse, MessageSquare, Send, PlusCircle } from 'lucide-react';

export default function DashboardView() {
  const { 
    patientVisits, selectedHospitalId, setSelectedHospitalId, symptoms, setSymptoms, 
    submitting, handleSubmit, readings, activeDoctorId, setActiveDoctorId,
    messages, chatInput, setChatInput, sendMessage
  } = usePatientContext();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const latestReading = readings.length > 0 ? readings[readings.length - 1] : null;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Left/Main Column: Triage & Vitals */}
      <div className="xl:col-span-2 flex flex-col gap-6">
        
        {/* Triage Request Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlusCircle className="h-5 w-5 text-primary" />
              Request New Triage
            </CardTitle>
          </CardHeader>
          <CardContent>
            {patientVisits.length === 0 ? (
              <div className="p-4 bg-slate-50 text-slate-500 rounded-md text-sm border border-slate-100">
                You need at least one recorded hospital visit to request triage.
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <Select 
                  value={selectedHospitalId}
                  onChange={e => setSelectedHospitalId(e.target.value)}
                  required
                >
                  <option value="">Select a Hospital or Clinic</option>
                  {Array.from(new Map(patientVisits.filter(v => v.hospital).map(v => [v.hospital.id, v.hospital])).values()).map(h => (
                    <option key={h.id} value={h.id}>{h.name}</option>
                  ))}
                </Select>
                <textarea 
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 min-h-[100px]"
                  value={symptoms} 
                  onChange={e => setSymptoms(e.target.value)} 
                  placeholder="Describe your symptoms in detail..."
                  required
                />
                <div className="flex justify-end">
                  <Button type="submit" disabled={submitting}>
                    {submitting ? 'Submitting...' : 'Submit Request'}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Vitals Summary Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <HeartPulse className="h-5 w-5 text-rose-500" />
              Latest Vitals
            </CardTitle>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full">Historic Data Only</span>
            </div>
          </CardHeader>
          <CardContent>
            
            {latestReading ? (
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 flex flex-col items-center justify-center">
                  <span className="text-sm text-slate-500 mb-1">Heart Rate</span>
                  <span className="text-2xl font-bold text-slate-900">{latestReading.heart_rate} <span className="text-sm font-normal text-slate-400">bpm</span></span>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 flex flex-col items-center justify-center">
                  <span className="text-sm text-slate-500 mb-1">Oxygen</span>
                  <span className="text-2xl font-bold text-slate-900">{latestReading.oxygen_level} <span className="text-sm font-normal text-slate-400">%</span></span>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 flex flex-col items-center justify-center">
                  <span className="text-sm text-slate-500 mb-1">Blood Pressure</span>
                  <span className="text-2xl font-bold text-slate-900">{latestReading.blood_pressure_sys}/{latestReading.blood_pressure_dia} <span className="text-sm font-normal text-slate-400">mmHg</span></span>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-400 text-sm">
                No recent vitals recorded.
              </div>
            )}
            
            {readings.length > 1 && (
              <div className="mt-6 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Previous Readings</h4>
                <div className="max-h-32 overflow-y-auto pr-2 space-y-2">
                  {readings.slice(0, -1).reverse().map(r => (
                    <div key={r.id} className="flex justify-between items-center text-sm py-1 border-b border-slate-50 last:border-0">
                      <span className="text-slate-400">{new Date(r.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      <span className="text-slate-700 font-medium">
                        HR: {r.heart_rate} <span className="mx-1 text-slate-300">|</span> 
                        O2: {r.oxygen_level}% <span className="mx-1 text-slate-300">|</span> 
                        BP: {r.blood_pressure_sys}/{r.blood_pressure_dia}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Right Column: Chat Drawer / Panel */}
      <div className="xl:col-span-1">
        <Card className="h-[600px] flex flex-col shadow-md border-primary/10">
          <CardHeader className="border-b border-slate-100 bg-slate-50/50 pb-4">
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2 text-lg">
                <MessageSquare className="h-5 w-5 text-primary" />
                Doctor Chat
              </CardTitle>
            </div>
            <div className="mt-4">
              <Select 
                value={activeDoctorId || ''} 
                onChange={(e) => setActiveDoctorId(Number(e.target.value))}
                className="bg-white"
              >
                <option value="" disabled>Select a doctor...</option>
                {patientVisits.map(v => (
                  <option key={v.doctor_id} value={v.doctor_id}>Dr. {v.doctor?.full_name}</option>
                ))}
              </Select>
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 bg-slate-50/30">
            {!activeDoctorId ? (
              <div className="flex-1 flex items-center justify-center text-sm text-slate-400 text-center px-4">
                Select a doctor from your previous visits to start chatting.
              </div>
            ) : messages.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-sm text-slate-400">
                No messages yet. Say hello!
              </div>
            ) : (
              messages.map(m => {
                const isMine = m.sender_id !== activeDoctorId;
                return (
                  <div key={m.id} className={`flex flex-col ${isMine ? 'items-end' : 'items-start'}`}>
                    <div 
                      className={`max-w-[85%] px-4 py-2 rounded-2xl text-sm ${
                        isMine 
                          ? 'bg-primary text-primary-foreground rounded-br-sm' 
                          : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm'
                      }`}
                    >
                      {m.content}
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 px-1">
                      {new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </span>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </CardContent>
          
          <div className="p-4 border-t border-slate-100 bg-white rounded-b-xl">
            <form onSubmit={sendMessage} className="flex gap-2">
              <Input 
                value={chatInput} 
                onChange={e => setChatInput(e.target.value)} 
                placeholder="Type a message..." 
                disabled={!activeDoctorId}
                className="flex-1"
              />
              <Button type="submit" size="icon" disabled={!activeDoctorId || !chatInput.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </Card>
      </div>

    </div>
  );
}

