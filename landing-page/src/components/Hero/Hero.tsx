
import { ArrowRight, ShieldCheck } from 'lucide-react';
import './Hero.css';

const Hero: React.FC = () => {
  return (
    <section className="hero">
      <div className="container hero-container">
        <div className="hero-content animate-fade-in">
          <div className="hero-badge">
            <ShieldCheck size={16} className="text-secondary" />
            <span>Secure Medical Record Management</span>
          </div>
          <h1 className="hero-title">
            Patient-Controlled Health Data for a <span className="text-primary">Connected World</span>
          </h1>
          <p className="hero-description">
            MedFlow Guardian empowers you to securely share your medical records with doctors across multiple hospitals. You control who sees your data, and for how long.
          </p>
          <div className="hero-actions">
            <a href="http://localhost:5174/login" className="btn btn-primary btn-lg">
              Patient Portal <ArrowRight size={20} />
            </a>
            <a href="http://localhost:5175/login" className="btn btn-secondary btn-lg">
              Doctor Login
            </a>
          </div>
          <div className="hero-stats">
            <div className="stat-item">
              <strong>100%</strong> Patient Control
            </div>
            <div className="stat-item">
              <strong>Real-time</strong> Triage Updates
            </div>
            <div className="stat-item">
              <strong>End-to-End</strong> Secure
            </div>
          </div>
        </div>
        
        <div className="hero-visual animate-fade-in delay-200">
          <div className="mockup-window">
            <div className="mockup-header">
              <span className="dot dot-red"></span>
              <span className="dot dot-yellow"></span>
              <span className="dot dot-green"></span>
            </div>
            <div className="mockup-body">
              <div className="mockup-sidebar">
                <div className="mockup-item active"></div>
                <div className="mockup-item"></div>
                <div className="mockup-item"></div>
              </div>
              <div className="mockup-main">
                <div className="mockup-card header-card"></div>
                <div className="mockup-card-grid">
                  <div className="mockup-card small-card"></div>
                  <div className="mockup-card small-card"></div>
                </div>
                <div className="mockup-card large-card">
                  <div className="mockup-grant-access">
                    <div className="mockup-avatar"></div>
                    <div className="mockup-text">
                      <div className="line"></div>
                      <div className="line short"></div>
                    </div>
                    <button className="mockup-btn">Grant</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Background Decorators */}
      <div className="bg-blob blob-1"></div>
      <div className="bg-blob blob-2"></div>
    </section>
  );
};

export default Hero;
