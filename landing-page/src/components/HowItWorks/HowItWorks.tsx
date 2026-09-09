
import { UploadCloud, Bell, CheckCircle2, FileText } from 'lucide-react';
import './HowItWorks.css';

const steps = [
  {
    icon: <UploadCloud size={24} />,
    title: 'Hospital Uploads Records',
    description: 'Your primary care hospital securely uploads your medical reports to the MedFlow vault.',
  },
  {
    icon: <Bell size={24} />,
    title: 'Specialist Requests Access',
    description: 'When you visit a new specialist, they request access to your specific documents.',
  },
  {
    icon: <CheckCircle2 size={24} />,
    title: 'You Grant Permission',
    description: 'You receive a notification and can approve access for a limited time (e.g., 24 hours).',
  },
  {
    icon: <FileText size={24} />,
    title: 'Specialist Views Records',
    description: 'The specialist reviews your history, and access is revoked automatically when time expires.',
  },
];

const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="section">
      <div className="container">
        <div className="section-header text-center animate-fade-in">
          <h2 className="section-title">How It Works</h2>
          <p className="section-subtitle text-muted">
            A simple, secure workflow that puts the patient in control.
          </p>
        </div>

        <div className="steps-container">
          {steps.map((step, idx) => (
            <div key={idx} className="step-item animate-fade-in" style={{ animationDelay: `${idx * 150}ms` }}>
              <div className="step-icon-container">
                <div className="step-icon text-primary">{step.icon}</div>
                {idx < steps.length - 1 && <div className="step-connector"></div>}
              </div>
              <div className="step-content">
                <h3 className="step-title">{step.title}</h3>
                <p className="step-description text-muted">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
