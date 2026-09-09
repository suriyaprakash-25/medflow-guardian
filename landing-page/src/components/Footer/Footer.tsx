
import { Activity } from 'lucide-react';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="footer-logo">
              <Activity className="text-primary" size={28} />
              <span className="footer-logo-text">MedFlow Guardian</span>
            </div>
            <p className="footer-description text-muted">
              Empowering patients with secure, controlled access to their medical records across the healthcare ecosystem.
            </p>
          </div>
          
          <div className="footer-links-group">
            <h4 className="footer-heading">Platform</h4>
            <a href="http://localhost:5174/login" className="footer-link">Patient Portal</a>
            <a href="http://localhost:5175/login" className="footer-link">Doctor Portal</a>
            <a href="#how-it-works" className="footer-link">How it Works</a>
          </div>

          <div className="footer-links-group">
            <h4 className="footer-heading">Legal (Demo)</h4>
            <span className="footer-link cursor-default">Privacy Policy</span>
            <span className="footer-link cursor-default">Terms of Service</span>
            <span className="footer-link cursor-default">HIPAA Compliance</span>
          </div>
        </div>

        <div className="footer-bottom">
          <p className="text-muted">
            &copy; {new Date().getFullYear()} MedFlow Guardian. This is a hackathon prototype.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
