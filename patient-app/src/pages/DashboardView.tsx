import { useEffect, useRef } from 'react';
import { usePatientContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Select } from '@shared/ui/Select';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { HeartPulse, MessageSquare, Send, PlusCircle } from 'lucide-react';

export default function DashboardView() {
  const {
    patientVisits, selectedHospitalId, setSelectedHospitalId, symptoms, setSymptoms,
    submitting, handleSubmit, readings, activeDoctorId, setActiveDoctorId,
    messages, chatInput, setChatInput, sendMessage,
  } = usePatientContext();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  const latestReading = readings.length > 0 ? readings[readings.length - 1] : null;
  const careTeams = Array.from(new Map(patientVisits.filter((visit) => visit.doctor_id).map((visit) => [visit.doctor_id, visit])).values());

  return (
    <div className="space-y-6">
      <FeedbackState
        tone="info"
        title="Symptom triage is automated screening support, not a diagnosis"
        message="Your symptom report is screened using deterministic keyword rules and remains subject to clinician review. If you believe you are experiencing a medical emergency, use local emergency services rather than this portal."
        compact
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="flex flex-col gap-6 xl:col-span-2">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><PlusCircle className="h-5 w-5 text-primary" aria-hidden="true" />Request symptom triage</CardTitle></CardHeader>
            <CardContent>
              {patientVisits.length === 0 ? (
                <FeedbackState tone="empty" title="No eligible visit context" message="A recorded hospital visit is required before a triage request can be associated with a care organization." compact />
              ) : (
                <form onSubmit={handleSubmit} className="grid gap-5">
                  <FormField id="triage-hospital" label="Hospital or clinic" hint="Choose the organization that should receive this symptom report." required>
                    <Select id="triage-hospital" value={selectedHospitalId} onChange={(event) => setSelectedHospitalId(event.target.value)} required>
                      <option value="">Select a hospital or clinic</option>
                      {Array.from(new Map(patientVisits.filter((visit) => visit.hospital).map((visit) => [visit.hospital.id, visit.hospital])).values()).map((hospital) => <option key={hospital.id} value={hospital.id}>{hospital.name}</option>)}
                    </Select>
                  </FormField>
                  <FormField id="triage-symptoms" label="Symptoms" hint="Describe what you are experiencing, when it started, and any important changes." required>
                    <textarea id="triage-symptoms" className="min-h-32 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-blue-600" value={symptoms} onChange={(event) => setSymptoms(event.target.value)} placeholder="Describe your symptoms" required />
                  </FormField>
                  <div className="flex justify-end"><Button type="submit" disabled={submitting || !symptoms.trim() || !selectedHospitalId}>{submitting ? 'Submitting securely…' : 'Submit symptoms for review'}</Button></div>
                </form>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div><CardTitle className="flex items-center gap-2 text-lg"><HeartPulse className="h-5 w-5 text-rose-600" aria-hidden="true" />Latest recorded vitals</CardTitle><p className="mt-1 text-xs text-slate-600">Recorded values only. MedFlow does not infer whether these readings are normal or healthy.</p></div>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">Historic data</span>
            </CardHeader>
            <CardContent>
              {latestReading ? (
                <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center"><dt className="text-sm text-slate-600">Heart rate</dt><dd className="mt-1 text-2xl font-bold text-slate-950">{latestReading.heart_rate} <span className="text-sm font-normal text-slate-600">bpm</span></dd></div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center"><dt className="text-sm text-slate-600">Oxygen saturation</dt><dd className="mt-1 text-2xl font-bold text-slate-950">{latestReading.oxygen_level}<span className="text-sm font-normal text-slate-600">%</span></dd></div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center"><dt className="text-sm text-slate-600">Blood pressure</dt><dd className="mt-1 text-2xl font-bold text-slate-950">{latestReading.blood_pressure_sys}/{latestReading.blood_pressure_dia} <span className="text-sm font-normal text-slate-600">mmHg</span></dd></div>
                </dl>
              ) : <FeedbackState tone="empty" title="No recorded vitals" message="No vital-sign readings are available in your record." compact />}

              {readings.length > 1 ? (
                <div className="mt-6 border-t border-slate-100 pt-4">
                  <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-600">Previous readings</h3>
                  <ul className="max-h-40 space-y-2 overflow-y-auto pr-1">
                    {readings.slice(0, -1).reverse().map((reading) => (
                      <li key={reading.id} className="flex flex-col gap-1 border-b border-slate-100 py-2 text-sm sm:flex-row sm:items-center sm:justify-between">
                        <time className="text-slate-500" dateTime={reading.created_at}>{new Date(reading.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</time>
                        <span className="font-medium text-slate-800">HR {reading.heart_rate} bpm · O₂ {reading.oxygen_level}% · BP {reading.blood_pressure_sys}/{reading.blood_pressure_dia} mmHg</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <Card className="flex min-h-[34rem] flex-col border-primary/10 xl:col-span-1">
          <CardHeader className="border-b border-slate-100 bg-slate-50/50 pb-4">
            <CardTitle className="flex items-center gap-2 text-lg"><MessageSquare className="h-5 w-5 text-primary" aria-hidden="true" />Care-team messages</CardTitle>
            <div className="mt-4">
              <FormField id="message-doctor" label="Clinician">
                <Select id="message-doctor" value={activeDoctorId || ''} onChange={(event) => setActiveDoctorId(event.target.value ? Number(event.target.value) : null)} className="bg-white">
                  <option value="">Select a clinician</option>
                  {careTeams.map((visit) => <option key={visit.doctor_id} value={visit.doctor_id}>{visit.doctor?.full_name ? `Dr. ${visit.doctor.full_name}` : `Doctor ID ${visit.doctor_id}`}</option>)}
                </Select>
              </FormField>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3 overflow-y-auto bg-slate-50/30 p-4" aria-live="polite">
            {!activeDoctorId ? <FeedbackState tone="empty" title="Choose a clinician" message="Select a clinician from a recorded visit to view the conversation." compact /> : messages.length === 0 ? <FeedbackState tone="empty" title="No messages yet" message="Messages exchanged with this clinician will appear here." compact /> : messages.map((message) => {
              const isMine = message.sender_id !== activeDoctorId;
              return <div key={message.id} className={`flex flex-col ${isMine ? 'items-end' : 'items-start'}`}><div className={`max-w-[88%] rounded-2xl px-4 py-2 text-sm ${isMine ? 'rounded-br-sm bg-blue-700 text-white' : 'rounded-bl-sm border border-slate-200 bg-white text-slate-900'}`}>{message.content}</div><time className="mt-1 px-1 text-[11px] text-slate-500" dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div>;
            })}
            <div ref={messagesEndRef} />
          </CardContent>
          <div className="border-t border-slate-100 bg-white p-4">
            <form onSubmit={sendMessage} className="flex items-end gap-2">
              <div className="flex-1"><FormField id="message-input" label="Message"><input id="message-input" type="text" value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Write a message" className="min-h-11 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-600 disabled:bg-slate-100" disabled={!activeDoctorId} /></FormField></div>
              <Button type="submit" size="icon" aria-label="Send message" disabled={!activeDoctorId || !chatInput.trim()}><Send className="h-4 w-4" aria-hidden="true" /></Button>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
}
