
import Navbar from './components/Navbar/Navbar';
import Hero from './components/Hero/Hero';
import Features from './components/Features/Features';
import HowItWorks from './components/HowItWorks/HowItWorks';
import Experience from './components/Experience/Experience';
import Security from './components/Security/Security';
import Footer from './components/Footer/Footer';
import './App.css';

function App() {
  return (
    <div className="app">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Experience />
        <Security />
      </main>
      <Footer />
    </div>
  );
}

export default App;
