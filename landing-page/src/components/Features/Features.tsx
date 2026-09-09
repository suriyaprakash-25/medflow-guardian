
import { Lock, Stethoscope, Share2, Clock } from 'lucide-react';
import './Features.css';

const featuresList = [
  {
    title: 'Bank-Level Security',
    description: 'Your medical records are encrypted and secured. Only you decide who gets access.',
    icon: <Lock className="feature-icon text-primary" size={28} />,
  },
  {
    title: 'Cross-Hospital Sharing',
    description: 'Seamlessly share records between different hospital networks without complicated paperwork.',
    icon: <Share2 className="feature-icon text-secondary" size={28} />,
  },
  {
    title: 'Real-Time Triage',
    description: 'AI-assisted triage ensures doctors prioritize critical cases immediately.',
    icon: <Stethoscope className="feature-icon text-primary" size={28} />,
  },
  {
    title: 'Time-Bound Access',
    description: 'Grant access for a specific duration. After the time expires, access is automatically revoked.',
    icon: <Clock className="feature-icon text-secondary" size={28} />,
  },
];

const Features: React.FC = () => {
  return (
    <section id="features" className="section bg-alt">
      <div className="container">
        <div className="section-header text-center animate-fade-in">
          <h2 className="section-title">Key Features</h2>
          <p className="section-subtitle text-muted">
            Designed for patients who demand privacy and hospitals that require efficiency.
          </p>
        </div>

        <div className="features-grid grid md:grid-cols-2 lg:grid-cols-4 relative z-10">
          {featuresList.map((feature, idx) => (
            <div key={idx} className={`feature-card glass animate-fade-in delay-${(idx + 1) * 100}`}>
              <div className="feature-icon-wrapper">
                {feature.icon}
              </div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description text-muted">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
      
      {/* Background Decorators */}
      <div className="bg-blob blob-3"></div>
    </section>
  );
};

export default Features;
