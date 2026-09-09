import { useState, useEffect } from 'react';
import { Activity, Menu, X } from 'lucide-react';
import './Navbar.css';

const Navbar: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`navbar ${isScrolled ? 'scrolled' : ''}`}>
      <div className="container navbar-container">
        <div className="navbar-brand">
          <Activity className="navbar-logo-icon" size={32} />
          <span className="navbar-logo-text">MedFlow Guardian</span>
        </div>

        {/* Desktop Navigation */}
        <nav className="navbar-nav desktop-nav">
          <a href="#features" className="nav-link">Features</a>
          <a href="#how-it-works" className="nav-link">How it Works</a>
          <a href="#security" className="nav-link">Security</a>
        </nav>

        <div className="navbar-actions desktop-actions">
          <a href="http://localhost:5174/login" className="btn btn-secondary nav-btn">Patient Login</a>
          <a href="http://localhost:5175/login" className="btn btn-primary nav-btn">Doctor Portal</a>
        </div>

        {/* Mobile Menu Toggle */}
        <button 
          className="mobile-menu-toggle" 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle mobile menu"
        >
          {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="mobile-menu">
          <nav className="mobile-nav">
            <a href="#features" className="mobile-link" onClick={() => setIsMobileMenuOpen(false)}>Features</a>
            <a href="#how-it-works" className="mobile-link" onClick={() => setIsMobileMenuOpen(false)}>How it Works</a>
            <a href="#security" className="mobile-link" onClick={() => setIsMobileMenuOpen(false)}>Security</a>
          </nav>
          <div className="mobile-actions">
            <a href="http://localhost:5174/login" className="btn btn-secondary mobile-btn">Patient Login</a>
            <a href="http://localhost:5175/login" className="btn btn-primary mobile-btn">Doctor Portal</a>
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;
