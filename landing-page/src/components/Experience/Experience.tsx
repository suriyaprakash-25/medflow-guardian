import { useState } from 'react';
import { User, UserPlus } from 'lucide-react';
import './Experience.css';

const Experience: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'patient' | 'doctor'>('patient');

  return (
    <section className="section bg-alt">
      <div className="container">
        <div className="section-header text-center animate-fade-in">
          <h2 className="section-title">Built for Everyone</h2>
          <p className="section-subtitle text-muted">
            Seamless experiences whether you're managing your own health or saving lives.
          </p>
        </div>

        <div className="experience-container">
          <div className="experience-tabs animate-fade-in delay-100">
            <button 
              className={`tab-btn ${activeTab === 'patient' ? 'active' : ''}`}
              onClick={() => setActiveTab('patient')}
            >
              <User size={20} /> For Patients
            </button>
            <button 
              className={`tab-btn ${activeTab === 'doctor' ? 'active' : ''}`}
              onClick={() => setActiveTab('doctor')}
            >
              <UserPlus size={20} /> For Doctors
            </button>
          </div>

          <div className="experience-content animate-fade-in delay-200">
            {activeTab === 'patient' ? (
              <div className="experience-panel patient-panel">
                <div className="panel-text">
                  <h3>Your Health, Your Control</h3>
                  <ul>
                    <li>View all your medical records in one secure vault.</li>
                    <li>Receive instant notifications when a doctor requests access.</li>
                    <li>Approve or deny access with a single tap.</li>
                    <li>Set time limits on how long records can be viewed.</li>
                  </ul>
                  <a href="http://localhost:5174/login" className="btn btn-primary mt-4">
                    Explore Patient Portal
                  </a>
                </div>
                <div className="panel-image patient-image"></div>
              </div>
            ) : (
              <div className="experience-panel doctor-panel">
                <div className="panel-text">
                  <h3>Efficient Triage & Care</h3>
                  <ul>
                    <li>Access a unified triage queue prioritized by AI.</li>
                    <li>Request temporary access to cross-hospital patient records.</li>
                    <li>Upload new reports directly to the patient's vault.</li>
                    <li>Make informed decisions with complete medical histories.</li>
                  </ul>
                  <a href="http://localhost:5175/login" className="btn btn-secondary mt-4">
                    Explore Doctor Portal
                  </a>
                </div>
                <div className="panel-image doctor-image"></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Experience;
