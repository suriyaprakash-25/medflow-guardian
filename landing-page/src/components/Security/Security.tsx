
import { Shield, Lock, FileKey2 } from 'lucide-react';
import './Security.css';

const Security: React.FC = () => {
  return (
    <section id="security" className="section security-section">
      <div className="container">
        <div className="security-grid">
          <div className="security-content animate-fade-in">
            <h2 className="section-title text-white">Uncompromising Security & Privacy</h2>
            <p className="security-description">
              Your health data is extremely sensitive. MedFlow Guardian is designed with 
              privacy-first principles, ensuring only authorized personnel can access 
              your records, and only when you permit it.
            </p>
            
            <div className="security-features">
              <div className="sec-feature">
                <Shield className="sec-icon" size={24} />
                <div>
                  <h4 className="sec-feature-title">HIPAA & GDPR Compliant Design</h4>
                  <p className="sec-feature-text">Built following stringent regulatory standards for health data protection.</p>
                </div>
              </div>
              <div className="sec-feature">
                <Lock className="sec-icon" size={24} />
                <div>
                  <h4 className="sec-feature-title">End-to-End Encryption</h4>
                  <p className="sec-feature-text">Data is encrypted in transit and at rest. We cannot read your medical records.</p>
                </div>
              </div>
              <div className="sec-feature">
                <FileKey2 className="sec-icon" size={24} />
                <div>
                  <h4 className="sec-feature-title">Granular Consent</h4>
                  <p className="sec-feature-text">Revoke access at any time. View a complete audit log of who viewed your files.</p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="security-visual animate-fade-in delay-200">
            <div className="shield-container">
              <div className="pulse-ring"></div>
              <div className="pulse-ring delay-1"></div>
              <Shield size={120} className="main-shield" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Security;
