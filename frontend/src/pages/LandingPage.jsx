import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Calendar, CheckCircle, Lock, ShieldCheck, BadgeCheck, Zap, Brain, Database, MapPin, Sparkles } from 'lucide-react';
import api from '../api';

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [userCity, setUserCity] = useState('');
  const [locationStatus, setLocationStatus] = useState('detecting');
  const [landingDoctors, setLandingDoctors] = useState([
    { name: 'Dr. Priya Sharma', spec: 'Cardiologist', init: 'PS', bg: 'linear-gradient(135deg, #059669, #34d399)' },
    { name: 'Dr. Rahul Mehta', spec: 'General Physician', init: 'RM', bg: 'linear-gradient(135deg, #2563eb, #60a5fa)' },
    { name: 'Dr. Anjali Verma', spec: 'Orthopedic', init: 'AV', bg: 'linear-gradient(135deg, #7c3aed, #a78bfa)' }
  ]);

  const BG_COLORS = [
    'linear-gradient(135deg, #059669, #34d399)',
    'linear-gradient(135deg, #2563eb, #60a5fa)',
    'linear-gradient(135deg, #7c3aed, #a78bfa)',
    'linear-gradient(135deg, #d97706, #fbbf24)',
    'linear-gradient(135deg, #dc2626, #f87171)',
  ];

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handleScroll);
    detectLocation();
    // Fetch real doctors for display
    api.get('/doctor/list').then(res => {
      const data = res.data;
      if (Array.isArray(data) && data.length > 0) {
        const real = data
          .filter(d => !/mock/i.test(d.full_name || d.name || ''))
          .map((d, i) => ({
            name: d.full_name || d.name,
            spec: d.specialization || 'Specialist',
            init: (d.full_name || d.name || 'DR').split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase(),
            bg: BG_COLORS[i % BG_COLORS.length],
          }));
        if (real.length > 0) setLandingDoctors(real);
      }
    }).catch(() => { });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const detectLocation = () => {
    setLocationStatus('detecting');
    if (!navigator.geolocation) {
      setLocationStatus('denied');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`);
          const data = await res.json();
          const city = data.address.city || data.address.state || data.address.town || '';
          setUserCity(city);
          setLocationStatus('found');
        } catch (error) {
          console.error('Error reverse geocoding:', error);
          setLocationStatus('denied');
        }
      },
      (error) => {
        console.error('Geolocation error:', error);
        setLocationStatus('denied');
      }
    );
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#060d0a', overflowX: 'hidden', fontFamily: "'DM Sans', sans-serif" }}>
      <style>{`
        :root {
          --gold: #c9a84c;
          --gold-light: #e8c97a;
          --gold-glow: rgba(201,168,76,0.15);
          --dark-900: #060d0a;
          --dark-800: #0d1f16;
          --dark-700: #0a2e1f;
        }
        
        .playfair {
          font-family: 'Playfair Display', serif;
        }
        
        @media (max-width: 768px) {
          .hero-h1-1, .hero-h1-2 { font-size: 40px !important; }
          .steps-grid { grid-template-columns: 1fr !important; }
          .doctors-grid { grid-template-columns: 1fr !important; }
          .hero-btns { flex-direction: column !important; width: 100%; gap: 1rem !important; }
          .hero-btns a { width: 100%; text-align: center; justify-content: center; display: flex; align-items: center; }
          .footer-grid { grid-template-columns: 1fr 1fr !important; gap: 2rem !important; }
          .nav-login { display: none !important; }
          .trust-pills { flex-direction: column; width: 100%; align-items: center; }
        }
      `}</style>

      {/* SECTION 1 — NAVBAR */}
      <nav style={{
        backgroundColor: scrolled ? 'rgba(6, 13, 10, 0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(201, 168, 76, 0.1)' : 'none',
        transition: 'all 0.3s ease',
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        padding: '1rem 0'
      }}>
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Link to="/" style={{ textDecoration: 'none', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div className="pulse-dot animate-pulse" style={{ backgroundColor: 'var(--c-primary)', width: '8px', height: '8px', borderRadius: '50%' }}></div>
              <span className="playfair" style={{ fontSize: '1.5rem', color: '#f5f0e8', fontWeight: 600, letterSpacing: '0.02em' }}>HABS</span>
            </div>
            <span style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '0.65rem', color: '#c9a84c', letterSpacing: '0.15em', textTransform: 'uppercase', marginTop: '0.1rem', marginLeft: '1rem' }}>Private Healthcare</span>
          </Link>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <Link to="/login" className="nav-login" style={{ color: '#8a9e94', textDecoration: 'none', fontSize: '0.9375rem', fontWeight: 500, transition: 'color 0.2s', padding: '0.5rem' }} onMouseEnter={(e) => e.target.style.color = '#f5f0e8'} onMouseLeave={(e) => e.target.style.color = '#8a9e94'}>Login</Link>
            <Link to="/register" style={{
              border: '1px solid #c9a84c', color: '#c9a84c', backgroundColor: 'transparent', textDecoration: 'none',
              borderRadius: 'var(--r-pill)', padding: '0 1.5rem', height: '40px', display: 'flex', alignItems: 'center',
              fontSize: '0.9375rem', fontWeight: 500, transition: 'background-color 0.2s'
            }} onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(201,168,76,0.1)'} onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}>Sign Up</Link>
          </div>
        </div>
      </nav>

      {/* SECTION 2 — HERO */}
      <section style={{
        backgroundColor: '#060d0a', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center', position: 'relative', overflow: 'hidden', paddingTop: '100px', paddingBottom: '4rem'
      }}>
        {/* Layer 1 - Radial gold glow */}
        <div style={{
          position: 'absolute', top: '40%', left: '50%', transform: 'translate(-50%, -50%)',
          width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(201,168,76,0.06) 0%, transparent 65%)', pointerEvents: 'none'
        }}></div>

        {/* Layer 2 - Thin grid lines */}
        <div style={{
          position: 'absolute', inset: 0, zIndex: 0,
          backgroundImage: 'linear-gradient(rgba(201,168,76,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(201,168,76,0.04) 1px, transparent 1px)',
          backgroundSize: '60px 60px'
        }}></div>

        {/* Layer 3 - Bottom gradient fade */}
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0, height: '120px',
          background: 'linear-gradient(transparent 0%, rgba(248,250,248,0.3) 60%, #f8faf8 100%)', zIndex: 1
        }}></div>

        {/* HERO CONTENT */}
        <div className="animate-fadeUp" style={{ position: 'relative', zIndex: 2, maxWidth: '680px', margin: '0 auto', padding: '2rem 1.5rem', width: '100%' }}>

          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.75rem',
            fontFamily: "'DM Sans', sans-serif", fontSize: '0.75rem', letterSpacing: '0.2em', textTransform: 'uppercase', color: '#c9a84c',
            marginBottom: '2.5rem'
          }}>
            <div style={{ width: '32px', height: '1px', backgroundColor: 'rgba(201,168,76,0.5)' }}></div>
            HABS · Private Health Services
            <div style={{ width: '32px', height: '1px', backgroundColor: 'rgba(201,168,76,0.5)' }}></div>
          </div>

          <h1 style={{ marginBottom: '1.75rem', letterSpacing: '-0.02em', lineHeight: '1.08', margin: '0 0 1.75rem 0' }}>
            <div className="playfair hero-h1-1" style={{ fontSize: '64px', color: '#f5f0e8', fontStyle: 'normal', fontWeight: 600 }}>Your Health Deserves</div>
            <div className="playfair hero-h1-2" style={{ fontSize: '64px', color: '#c9a84c', fontStyle: 'italic', fontWeight: 400 }}>The Best Care.</div>
          </h1>

          <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '1.0625rem', color: '#8a9e94', lineHeight: '1.75', maxWidth: '460px', margin: '0 auto 2.5rem auto' }}>
            Schedule appointments with qualified specialists. Secure, private, and designed around your time.
          </p>

          <div className="hero-btns" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '2.5rem' }}>
            <Link to="/register?role=patient" style={{
              backgroundColor: '#c9a84c', color: '#060d0a', borderRadius: 'var(--r-pill)',
              height: '52px', padding: '0 2rem', fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: '0.9375rem',
              border: 'none', transition: 'all 0.2s', textDecoration: 'none', display: 'flex', alignItems: 'center'
            }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#e8c97a'; e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(201,168,76,0.3)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#c9a84c'; e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}>
              Book an Appointment
            </Link>

            <Link to="/register?role=doctor" style={{
              backgroundColor: 'transparent', border: '1px solid rgba(201,168,76,0.35)', color: '#f5f0e8',
              borderRadius: 'var(--r-pill)', height: '52px', padding: '0 2rem', fontFamily: "'DM Sans', sans-serif", fontWeight: 500, fontSize: '0.9375rem',
              transition: 'all 0.2s', textDecoration: 'none', display: 'flex', alignItems: 'center'
            }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#c9a84c'; e.currentTarget.style.backgroundColor = 'rgba(201,168,76,0.05)'; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(201,168,76,0.35)'; e.currentTarget.style.backgroundColor = 'transparent'; }}>
              I'm a Doctor
            </Link>
          </div>

          <div className="trust-pills" style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {['Instant Confirmation', 'No Hidden Fees', 'Cancel Anytime'].map((text, i) => (
              <div key={i} style={{
                border: '1px solid rgba(201,168,76,0.2)', borderRadius: 'var(--r-pill)', padding: '0.4rem 1rem',
                fontSize: '0.8rem', color: '#8a9e94', backgroundColor: 'rgba(201,168,76,0.04)',
                display: 'inline-flex', alignItems: 'center', gap: '0.4rem'
              }}>
                <span style={{ color: '#c9a84c', display: 'inline-flex', alignItems: 'center' }}><Sparkles size={12} /></span> {text}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 3 — HOW IT WORKS */}
      <section style={{ backgroundColor: '#faf9f6', padding: '80px 40px', position: 'relative', zIndex: 2 }}>
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
            <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '11px', letterSpacing: '2px', color: '#c9a96e', textTransform: 'uppercase', marginBottom: '1rem', display: 'inline-block', background: 'transparent', border: '1px solid #c9a96e', borderRadius: '20px', padding: '4px 14px' }}>
              THE PROCESS
            </div>
            <h2 className="playfair" style={{ fontSize: '44px', color: '#1a1a1a', fontStyle: 'italic', marginBottom: '1rem', fontWeight: 500, margin: '0 0 1rem 0' }}>
              Simple by Design.
            </h2>
            <p style={{ fontFamily: "'DM Sans', sans-serif", color: '#666666', fontSize: '0.9375rem', margin: 0 }}>
              From search to confirmation in minutes.
            </p>
          </div>

          <div className="steps-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
            {[
              { icon: <Search size={24} color="#c9a96e" />, label: 'STEP 01', title: 'Find Your Specialist', desc: 'Search by department or doctor name and view available slots in real time.' },
              { icon: <Calendar size={24} color="#c9a96e" />, label: 'STEP 02', title: 'Choose Your Slot', desc: 'Pick a date and time that fits your schedule — no phone calls needed.' },
              { icon: <CheckCircle size={24} color="#c9a96e" />, label: 'STEP 03', title: 'Get Confirmed', desc: 'Receive an instant digital confirmation with all appointment details.' }
            ].map((step, i) => (
              <div key={i} className="animate-fadeUp" style={{
                background: '#ffffff', border: '1px solid #e8e0d0', borderTop: '3px solid #c9a96e', borderRadius: '16px',
                padding: '2rem 1.75rem', boxShadow: '0 4px 24px rgba(180,150,90,0.08)',
                position: 'relative', animationDelay: `${(i + 1) * 0.1}s`
              }}>
                <div className="playfair" style={{
                  position: 'absolute', top: '1rem', right: '1.25rem', fontSize: '5rem', color: '#c9a96e',
                  fontWeight: 700, lineHeight: 1, userSelect: 'none'
                }}>
                  {`0${i + 1}`}
                </div>

                <div style={{ position: 'relative', zIndex: 1 }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '48px', height: '48px', background: '#f5f0e8', borderRadius: '12px', marginBottom: '1rem' }}>
                    {step.icon}
                  </div>
                  <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '0.65rem', letterSpacing: '0.15em', color: '#c9a96e', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                    {step.label}
                  </div>
                  <h3 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: '1.0625rem', color: '#1a1a1a', marginBottom: '0.5rem', margin: '0 0 0.5rem 0' }}>
                    {step.title}
                  </h3>
                  <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '0.875rem', color: '#666666', lineHeight: '1.6', margin: 0 }}>
                    {step.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 4 — DOCTORS */}
      <section style={{ backgroundColor: '#060d0a', padding: '7rem 0' }}>
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
            <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '0.7rem', letterSpacing: '0.2em', color: '#c9a84c', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
              OUR SPECIALISTS
            </div>
            <h2 className="playfair" style={{ fontSize: '44px', color: '#f5f0e8', margin: 0, fontWeight: 500 }}>
              Meet the Team.
            </h2>
            <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '0.875rem', color: '#8a9e94', fontStyle: 'italic', marginTop: '0.5rem', marginBottom: '1.5rem' }}>
              Sample profiles shown below — verified doctors onboarded via admin panel.
            </p>

            <div style={{ color: '#8a9e94', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {locationStatus === 'detecting' && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><MapPin size={14} /> Detecting your location...</span>}
              {locationStatus === 'found' && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><MapPin size={14} /> Showing doctors near {userCity}</span>}
              {locationStatus === 'denied' && (
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <MapPin size={14} /> Enable location for nearby doctors
                  <button onClick={() => { detectLocation(); setLocationStatus('detecting'); }} style={{
                    backgroundColor: 'rgba(201,168,76,0.15)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.3)',
                    borderRadius: 'var(--r-pill)', padding: '0.2rem 0.75rem', fontSize: '0.75rem', fontWeight: 600,
                    cursor: 'pointer', marginLeft: '0.5rem', transition: 'all 0.2s'
                  }}>Enable →</button>
                </span>
              )}
            </div>
          </div>

          <div className="doctors-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {landingDoctors.map((doc, i) => (
              <div key={i} style={{
                backgroundColor: '#0d1f16', border: '1px solid rgba(201,168,76,0.12)', borderRadius: 'var(--r-lg)',
                padding: '1.5rem', transition: 'all 0.25s ease'
              }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(201,168,76,0.4)';
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = '0 12px 40px rgba(0,0,0,0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(201,168,76,0.12)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <div style={{ width: '52px', height: '52px', borderRadius: '50%', background: doc.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 700, fontSize: '0.9rem', flexShrink: 0 }}>
                    {doc.init}
                  </div>
                  <div>
                    <h3 className="playfair" style={{ fontSize: '1rem', color: '#f5f0e8', margin: '0 0 0.2rem 0', fontWeight: 600 }}>{doc.name}</h3>
                    <div style={{
                      display: 'inline-block', backgroundColor: 'rgba(201,168,76,0.1)', color: '#c9a84c',
                      border: '1px solid rgba(201,168,76,0.2)', borderRadius: 'var(--r-pill)',
                      padding: '0.15rem 0.6rem', fontSize: '0.7rem', fontWeight: 600
                    }}>
                      {doc.spec}
                    </div>
                  </div>
                </div>

                <div style={{ height: '1px', backgroundColor: 'rgba(201,168,76,0.1)', margin: '1rem 0' }}></div>

                <div style={{ color: '#8a9e94', fontSize: '0.8rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <MapPin size={14} /> HABS Clinic{userCity ? `, ${userCity}` : ''}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: '#8a9e94', fontSize: '0.8rem' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#059669' }}></div>
                    Available Today
                  </div>
                  <Link to="/register?role=patient" style={{
                    backgroundColor: 'transparent', border: '1px solid #c9a84c', color: '#c9a84c',
                    borderRadius: 'var(--r-pill)', padding: '0.35rem 1rem', fontSize: '0.8rem', fontWeight: 600,
                    textDecoration: 'none', transition: 'background-color 0.2s'
                  }} onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(201,168,76,0.1)'} onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}>
                    Book Now
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 5 — FOOTER */}
      <footer style={{ backgroundColor: '#060d0a', borderTop: '1px solid rgba(201,168,76,0.1)', paddingTop: '4rem', paddingBottom: '2rem' }}>
        <div className="container">
          <div className="footer-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4rem' }}>
            <div>
              <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <div className="pulse-dot" style={{ backgroundColor: 'var(--c-primary)', width: '8px', height: '8px', borderRadius: '50%' }}></div>
                <span className="playfair" style={{ fontSize: '1.5rem', color: '#f5f0e8', fontWeight: 600 }}>HABS</span>
              </Link>
              <p style={{ fontFamily: "'DM Sans', sans-serif", color: '#8a9e94', fontSize: '0.8rem', margin: 0 }}>
                Private Healthcare, Simplified.
              </p>
            </div>

            <div>
              <h4 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: '0.7rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#c9a84c', marginBottom: '1.5rem', marginTop: 0 }}>
                Product
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <Link to="/register" style={{ color: '#8a9e94', textDecoration: 'none', fontSize: '0.875rem', transition: 'color 0.2s' }} onMouseEnter={(e) => e.target.style.color = '#f5f0e8'} onMouseLeave={(e) => e.target.style.color = '#8a9e94'}>Book Appointment</Link>
                <Link to="/register?role=doctor" style={{ color: '#8a9e94', textDecoration: 'none', fontSize: '0.875rem', transition: 'color 0.2s' }} onMouseEnter={(e) => e.target.style.color = '#f5f0e8'} onMouseLeave={(e) => e.target.style.color = '#8a9e94'}>For Doctors</Link>
                <Link to="/" style={{ color: '#8a9e94', textDecoration: 'none', fontSize: '0.875rem', transition: 'color 0.2s' }} onMouseEnter={(e) => e.target.style.color = '#f5f0e8'} onMouseLeave={(e) => e.target.style.color = '#8a9e94'}>Pricing</Link>
              </div>
            </div>

            <div>
              <h4 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: '0.7rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#c9a84c', marginBottom: '1.5rem', marginTop: 0 }}>
                Technology
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', color: '#8a9e94', fontSize: '0.875rem' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><Zap size={13} /> FastAPI + React</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><Brain size={13} /> ML No-Show Predictor</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><Database size={13} /> PostgreSQL + Alembic</span>
              </div>
            </div>

            <div>
              <h4 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 600, fontSize: '0.7rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#c9a84c', marginBottom: '1.5rem', marginTop: 0 }}>
                Trust
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', color: '#8a9e94', fontSize: '0.875rem' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><Lock size={13} /> 256-bit SSL</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><ShieldCheck size={13} /> HIPAA Compliant</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><BadgeCheck size={13} /> ISO 27001</span>
              </div>
            </div>
          </div>

          <div style={{ textAlign: 'center', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '2rem', marginTop: '3rem' }}>
            <span style={{ fontFamily: "'DM Sans', sans-serif", fontSize: '0.8rem', color: '#8a9e94' }}>
              © 2026 HABS. Developed for AI-Driven Healthcare Appointment & No-Show Prediction.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}