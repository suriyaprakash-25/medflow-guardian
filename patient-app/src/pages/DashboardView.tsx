import { useEffect, useRef } from 'react';
import { usePatientContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Select } from '@shared/ui/Select';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { HeartPulse, MessageSquare, Send, PlusCircle, CheckCheck } from 'lucide-react';
import React, { Suspense } from 'react';

import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

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
                <div className="space-y-6">
                  <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div className="glass-panel rounded-xl p-4 text-center"><dt className="text-sm text-slate-600">Heart rate</dt><dd className="mt-1 text-2xl font-bold text-slate-950">{latestReading.heart_rate} <span className="text-sm font-normal text-slate-600">bpm</span></dd></div>
                    <div className="glass-panel rounded-xl p-4 text-center"><dt className="text-sm text-slate-600">Oxygen sat</dt><dd className="mt-1 text-2xl font-bold text-slate-950">{latestReading.oxygen_level}<span className="text-sm font-normal text-slate-600">%</span></dd></div>
                    <div className="glass-panel rounded-xl p-4 text-center"><dt className="text-sm text-slate-600">Blood pressure</dt><dd className="mt-1 text-2xl font-bold text-slate-950">{latestReading.blood_pressure_sys}/{latestReading.blood_pressure_dia} <span className="text-sm font-normal text-slate-600">mmHg</span></dd></div>
                  </dl>
                  {readings.length > 1 && (
                    <div className="h-24 w-full mt-4">
                      <Suspense fallback={<div className="h-full w-full flex items-center justify-center text-xs text-slate-400">Loading chart...</div>}>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={readings.slice().reverse()}>
                            <YAxis domain={['dataMin - 10', 'dataMax + 10']} hide />
                            <Line type="monotone" dataKey="heart_rate" stroke="#e11d48" strokeWidth={3} dot={false} isAnimationActive={true} />
                          </LineChart>
                        </ResponsiveContainer>
                      </Suspense>
                      <p className="text-center text-xs text-slate-400 mt-1">Heart rate trend (historic)</p>
                    </div>
                  )}
                </div>
              ) : <FeedbackState tone="empty" title="No recorded vitals" message="No vital-sign readings are available in your record." compact />}
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
          <CardContent className="flex flex-1 flex-col gap-3 overflow-y-auto bg-slate-50/50 p-4 relative" aria-live="polite">
            {!activeDoctorId ? <FeedbackState tone="empty" title="Choose a clinician" message="Select a clinician from a recorded visit to view the conversation." compact /> : messages.length === 0 ? <FeedbackState tone="empty" title="No messages yet" message="Messages exchanged with this clinician will appear here." compact /> : messages.map((message) => {
              const isMine = message.sender_id !== activeDoctorId;
              return (
                <div key={message.id} className={`flex flex-col ${isMine ? 'items-end' : 'items-start'} group animate-in slide-in-from-bottom-2 duration-300`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm shadow-sm transition-all hover:shadow-md ${isMine ? 'rounded-br-sm bg-blue-600 text-white' : 'rounded-bl-sm border border-slate-200 bg-white text-slate-900'}`}>
                    {message.content}
                  </div>
                  <div className="flex items-center gap-1 mt-1 px-1 opacity-70 group-hover:opacity-100 transition-opacity">
                    <time className="text-[10px] font-medium text-slate-500" dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                    {isMine && <CheckCheck className="h-3 w-3 text-blue-500" />}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </CardContent>
          <div className="border-t border-slate-100 bg-white/80 backdrop-blur-md p-4 rounded-b-xl">
            <form onSubmit={sendMessage} className="flex items-end gap-2 relative">
              <div className="flex-1"><FormField id="message-input" label="Message"><input id="message-input" type="text" value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Type a secure message..." className="min-h-12 w-full rounded-full border border-slate-200 bg-slate-50/50 px-5 py-2 text-sm shadow-inner transition-colors focus:bg-white focus-visible:ring-2 focus-visible:ring-blue-600 disabled:bg-slate-100" disabled={!activeDoctorId} /></FormField></div>
              <Button type="submit" size="icon" aria-label="Send message" disabled={!activeDoctorId || !chatInput.trim()} className="rounded-full h-12 w-12 shadow-md hover:shadow-lg transition-all active:scale-95"><Send className="h-4 w-4" aria-hidden="true" /></Button>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
}
