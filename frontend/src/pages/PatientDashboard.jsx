import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { CalendarX2, Calendar, Clock, AlertTriangle, ShieldCheck, CheckCircle2, ChevronRight, User, LogOut, ArrowRight, Star, Check } from 'lucide-react';

const getToday = () => new Date().toISOString().split('T')[0];
const getTomorrow = () => { const t = new Date(); t.setDate(t.getDate() + 1); return t.toISOString().split('T')[0]; };
const formatDisplayDate = (d) => d ? new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(d)) : '';
const getDay = (d) => d ? new Intl.DateTimeFormat('en-GB', { day: '2-digit' }).format(new Date(d)) : '';
const getMonth = (d) => d ? new Intl.DateTimeFormat('en-GB', { month: 'short' }).format(new Date(d)) : '';
const getGreeting = () => { const h = new Date().getHours(); if (h < 12) return 'Good morning'; if (h < 17) return 'Good afternoon'; return 'Good evening'; };

export default function PatientDashboard() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const navigate = useNavigate();

  const isValidUUID = (s) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s || ''));
  const rawId = localStorage.getItem('user_id') || user?.id || '';
  const userId = isValidUUID(rawId) ? rawId : (isValidUUID(user?.id) ? user.id : null);

  const [doctors, setDoctors] = useState([]);
  const [doctorsLoading, setDoctorsLoading] = useState(true);
  const [appointments, setAppointments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [selectedDate, setSelectedDate] = useState(getTomorrow());
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [dateError, setDateError] = useState('');
  const [confirmed, setConfirmed] = useState(null);
  const [bookingError, setBookingError] = useState('');

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'U';

  const fetchAppointments = () => {
    api.get('/appointments', { headers: { 'X-User-Id': userId } })
      .then(res => { const data = res.data; setAppointments(Array.isArray(data) ? data : []); })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchAppointments();
    api.get('/doctor/list').then(res => {
      const data = res.data;
      if (Array.isArray(data)) {
        const realDoctors = data
          .filter(d => !/mock/i.test(d.full_name || d.name || ''))
          .map(d => ({
            id: d.id,
            name: d.full_name || d.name,
            spec: d.specialization || 'Specialist',
            init: (d.full_name || d.name || 'DR').split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase(),
          }));
        setDoctors(realDoctors);
      }
      setDoctorsLoading(false);
    }).catch(() => { setDoctorsLoading(false); });
  }, []);

  const handleDate = (e) => {
    const val = e.target.value;
    setSelectedDate(val);
    setSelectedSlot(null);
    setDateError(new Date(val) < new Date(getToday()) ? 'Please select a future date' : '');
  };

  const handleBook = () => {
    setBookingError('');
    const doc = (doctors || []).find(d => d.id === selectedDoc);
    api.post('/appointments', { doctor_id: selectedDoc, appointment_date: selectedDate, time_slot: selectedSlot }, { headers: { 'X-User-Id': userId } })
      .then(res => {
        setConfirmed({ id: res.data.appointment_id, doc: { name: doc?.name || doc?.full_name, spec: doc?.spec || doc?.specialization }, date: selectedDate, time: selectedSlot });
        fetchAppointments();
      })
      .catch(err => {
        const errData = err.response?.data;
        if (typeof errData === 'string') setBookingError(errData);
        else if (Array.isArray(errData?.detail)) setBookingError(errData.detail[0]?.msg || 'Validation error');
        else if (errData?.detail) setBookingError(errData.detail);
        else setBookingError(`Booking failed: ${err.message || 'Unknown error'}`);
      });
  };

  const handleCancel = (id) => {
    if (window.confirm('Are you sure you want to cancel this appointment?')) {
      api.patch(`/appointments/${id}/cancel`, {}, { headers: { 'X-User-Id': userId } })
        .then(fetchAppointments).catch(err => console.error(err));
    }
  };

  const logout = () => { localStorage.removeItem('token'); localStorage.removeItem('user'); navigate('/'); };

  if (!user || !user.id) return (
    <div style={{ background: '#1A3629', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ color: '#D4AF37', fontSize: '13px', letterSpacing: '4px', textTransform: 'uppercase', animation: 'pulse 2s infinite', fontFamily: "'Inter', sans-serif" }}>Preparing your private suite...</div>
    </div>
  );

  const selectedDocData = (doctors || []).find(d => d.id === selectedDoc);

  /* ── CONFIRMATION PAGE ── */
  if (confirmed) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#F9F7F1', fontFamily: "'Inter', sans-serif" }}>
        <style>{`
          @media print {
            body * { visibility: hidden !important; }
            #habs-print-area, #habs-print-area * { visibility: visible !important; }
            #habs-print-area { position: absolute !important; left: 0; top: 0; width: 100vw; display: flex !important; justify-content: center; padding: 40px; background: white !important; }
            .no-print { display: none !important; }
          }
        `}</style>
        
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
          <div id="habs-print-area" style={{ width: '100%', maxWidth: '560px' }}>
            <div style={{ background: '#fff', border: '1px solid #E8E0D4', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(26,54,41,0.08)' }}>
              <div style={{ padding: '3rem', textAlign: 'center', background: '#1A3629', color: '#fff', position: 'relative' }}>
                <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '150px', height: '150px', borderRadius: '50%', border: '1px solid rgba(212,175,55,0.2)' }}></div>
                <div style={{ width: '72px', height: '72px', borderRadius: '50%', background: 'rgba(212,175,55,0.15)', border: '2px solid #D4AF37', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', color: '#D4AF37' }}>
                  <CheckCircle2 size={36} />
                </div>
                <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '2rem', margin: '0 0 0.5rem', fontWeight: 400, color: '#F9F7F1' }}>Booking Confirmed</h2>
                <p style={{ color: '#A0B2A8', fontSize: '14px', margin: '0 0 1rem', fontStyle: 'italic' }}>Your private consultation is scheduled.</p>
                <div style={{ display: 'inline-block', background: 'rgba(255,255,255,0.1)', padding: '6px 16px', borderRadius: '100px', fontSize: '11px', letterSpacing: '0.12em', color: '#D4AF37', border: '1px solid rgba(212,175,55,0.3)' }}>REF: {String(confirmed.id).slice(0, 8).toUpperCase()}</div>
              </div>

              <div style={{ padding: '3rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2.5rem' }}>
                  {[
                    ['Patient', user?.full_name || 'Patient'],
                    ['Specialist', `Dr. ${confirmed.doc.name}`],
                    ['Department', confirmed.doc.spec],
                    ['Date', formatDisplayDate(confirmed.date)],
                    ['Time', confirmed.time],
                    ['Status', <><Check size={14} style={{ display: 'inline', verticalAlign: 'middle' }}/> CONFIRMED</>],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#8E9A94', marginBottom: '6px' }}>{k}</div>
                      <div style={{ fontWeight: 500, color: k === 'Status' ? '#2A4B3C' : '#1C2E26', fontSize: '15px' }}>{v}</div>
                    </div>
                  ))}
                </div>

                <div style={{ background: '#F4F1E8', borderLeft: '3px solid #D4AF37', borderRadius: '0 8px 8px 0', padding: '1rem 1.25rem', marginBottom: '2.5rem', fontSize: '13px', color: '#4A5B52', fontStyle: 'italic' }}>
                  Please arrive 10 minutes prior to your appointment time. Enjoy a complimentary beverage in our VIP lounge while you wait.
                </div>

                <div className="no-print" style={{ display: 'flex', gap: '1rem' }}>
                  <button onClick={() => window.print()}
                    style={{ flex: 1, height: '48px', borderRadius: '12px', background: 'transparent', border: '1.5px solid #D4AF37', color: '#D4AF37', cursor: 'pointer', fontWeight: 600, fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontFamily: 'inherit', transition: 'all 0.3s' }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(212,175,55,0.05)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}>
                    ⬇ Download Pass
                  </button>
                  <button onClick={() => { setConfirmed(null); setSelectedDoc(null); setSelectedSlot(null); }}
                    style={{ flex: 1, height: '48px', borderRadius: '12px', background: '#D4AF37', border: 'none', color: '#1A3629', cursor: 'pointer', fontWeight: 600, fontSize: '14px', fontFamily: 'inherit', transition: 'all 0.3s', boxShadow: '0 4px 15px rgba(212,175,55,0.3)' }}
                    onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(212,175,55,0.4)' }}
                    onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 15px rgba(212,175,55,0.3)' }}>
                    Return to Suite
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ── MAIN DASHBOARD ── */
  return (
    <div className="dashboard-layout" style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#F9F7F1', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&display=swap');

        .sidebar {
          width: 280px;
          background: #1A3629;
          color: white;
          padding: 40px 0;
          display: flex;
          flex-direction: column;
          position: fixed;
          height: 100vh;
          z-index: 10;
          border-right: 1px solid rgba(212,175,55,0.15);
        }
        
        .main-content {
          flex: 1;
          margin-left: 280px;
          padding: 60px 80px;
          background: linear-gradient(135deg, #F9F7F1 0%, #F0EAE1 100%);
          min-height: 100vh;
        }

        .nav-item {
          padding: 16px 40px;
          color: #A0B2A8;
          display: flex;
          align-items: center;
          gap: 16px;
          text-decoration: none;
          font-size: 14px;
          font-weight: 500;
          letter-spacing: 0.05em;
          transition: all 0.3s ease;
          border-left: 3px solid transparent;
          cursor: pointer;
        }
        .nav-item:hover, .nav-item.active {
          color: #D4AF37;
          background: rgba(212,175,55,0.05);
          border-left: 3px solid #D4AF37;
        }

        .glass-card {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.4);
          border-radius: 20px;
          box-shadow: 0 8px 32px rgba(26,54,41,0.04);
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .glass-card:hover {
          box-shadow: 0 12px 48px rgba(26,54,41,0.08);
          transform: translateY(-2px);
          border-color: rgba(212,175,55,0.3);
        }

        .appt-row {
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
        }
        .appt-row::before {
          content: '';
          position: absolute;
          left: 0; top: 0; height: 100%; width: 4px;
          background: #D4AF37;
          transform: scaleY(0);
          transition: transform 0.3s ease;
          transform-origin: bottom;
        }
        .appt-row:hover {
          background: #ffffff;
          box-shadow: 0 8px 24px rgba(26,54,41,0.06) !important;
        }
        .appt-row:hover::before {
          transform: scaleY(1);
        }

        .doc-card { transition: all 0.3s ease; }
        .doc-card:hover { border-color: #D4AF37 !important; box-shadow: 0 8px 30px rgba(212,175,55,0.15) !important; transform: translateY(-4px); }
        .slot-btn { transition: all 0.2s ease; }
        .slot-btn:hover { border-color: #D4AF37 !important; color: #D4AF37 !important; transform: translateY(-1px); }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #D4AF37; border-radius: 10px; }
      `}</style>

      {/* SIDEBAR */}
      <div className="sidebar">
        <div style={{ padding: '0 40px', marginBottom: '60px' }}>
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '28px', color: '#D4AF37', margin: 0, fontWeight: 600, letterSpacing: '0.05em' }}>HABS</h1>
          <div style={{ fontSize: '10px', color: '#A0B2A8', textTransform: 'uppercase', letterSpacing: '0.2em', marginTop: '4px' }}>Elite Care</div>
        </div>

        <div style={{ padding: '0 40px', marginBottom: '40px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'linear-gradient(135deg, #D4AF37, #A07830)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1A3629', fontSize: '16px', fontWeight: 600, boxShadow: '0 4px 12px rgba(212,175,55,0.3)' }}>
            {initials}
          </div>
          <div>
            <div style={{ color: '#fff', fontSize: '15px', fontWeight: 500 }}>{user?.full_name?.split(' ')[0] || 'Patient'}</div>
            <div style={{ color: '#D4AF37', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '2px' }}>Member</div>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div className="nav-item active"><CalendarX2 size={18} /> My Appointments</div>
        </div>

        <div style={{ padding: '0 40px' }}>
          <button onClick={logout} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', width: '100%', padding: '12px', borderRadius: '8px', color: '#A0B2A8', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'pointer', transition: 'all 0.3s' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#D4AF37'; e.currentTarget.style.color = '#D4AF37'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = '#A0B2A8'; }}>
            <LogOut size={16} /> Sign Out
          </button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        {/* HEADER */}
        <div style={{ marginBottom: '50px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            <p style={{ color: '#D4AF37', textTransform: 'uppercase', letterSpacing: '0.15em', fontSize: '12px', fontWeight: 600, marginBottom: '8px' }}>Private Dashboard</p>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '42px', color: '#1A3629', margin: 0, fontWeight: 500 }}>
              {getGreeting()}, {user?.full_name?.split(' ')[0] || 'Guest'}
            </h1>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ color: '#8E9A94', fontSize: '14px', margin: 0 }}>{new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())}</p>
          </div>
        </div>

        {/* APPOINTMENTS ROW */}
        <div style={{ marginBottom: '60px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '24px', color: '#1A3629', margin: 0, fontWeight: 500 }}>Your Itinerary</h2>
            {appointments.length > 0 && <span style={{ color: '#D4AF37', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>View History <ArrowRight size={14} style={{display:'inline', verticalAlign:'middle'}}/></span>}
          </div>

          {(!appointments || appointments.length === 0) ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '60px 40px' }}>
              <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(212,175,55,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', color: '#D4AF37' }}>
                <CalendarX2 size={30} />
              </div>
              <h3 style={{ fontFamily: "'Playfair Display', serif", fontSize: '20px', color: '#1A3629', margin: '0 0 8px', fontWeight: 500 }}>No Upcoming Consultations</h3>
              <p style={{ color: '#8E9A94', fontSize: '14px', margin: 0 }}>Select a specialist below to schedule your next private appointment.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {appointments.map(appt => {
                const rawStatus = typeof appt.status === 'object' ? (appt.status?.value ?? 'pending') : (appt.status ?? 'pending');
                const isCancelled = rawStatus === 'cancelled';
                const isConfirmed = rawStatus === 'booked' || rawStatus === 'confirmed';
                
                return (
                  <div key={appt.id} className="appt-row glass-card" style={{
                    padding: '24px 32px',
                    display: 'flex', alignItems: 'center', gap: '32px',
                    opacity: isCancelled ? 0.6 : 1,
                  }}>
                    <div style={{ textAlign: 'center', minWidth: '60px', paddingRight: '24px', borderRight: '1px solid rgba(26,54,41,0.1)' }}>
                      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '32px', color: '#D4AF37', lineHeight: 1, marginBottom: '4px' }}>{getDay(appt.date)}</div>
                      <div style={{ fontSize: '12px', color: '#8E9A94', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 500 }}>{getMonth(appt.date)}</div>
                    </div>
                    
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '20px', color: '#1A3629', fontWeight: 500 }}>{appt.doctor_name}</div>
                        <span style={{ padding: '4px 12px', borderRadius: '100px', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', background: isCancelled ? '#F0EAE1' : isConfirmed ? 'rgba(212,175,55,0.15)' : 'rgba(42,75,60,0.1)', color: isCancelled ? '#8E9A94' : isConfirmed ? '#A07830' : '#2A4B3C' }}>
                          {rawStatus}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontSize: '13px', color: '#8E9A94' }}>
                        <span>{appt.doctor_spec || 'Specialist'}</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#1A3629', fontWeight: 500 }}><Clock size={14} color="#D4AF37" />{appt.time}</span>
                      </div>
                    </div>

                    {!isCancelled && (
                      <div>
                        <button onClick={() => handleCancel(appt.id)}
                          style={{ background: 'transparent', border: '1px solid rgba(26,54,41,0.2)', borderRadius: '100px', color: '#1A3629', fontSize: '12px', fontWeight: 500, cursor: 'pointer', padding: '8px 20px', transition: 'all 0.3s' }}
                          onMouseEnter={e => { e.currentTarget.style.background = '#1A3629'; e.currentTarget.style.color = '#fff'; e.currentTarget.style.borderColor = '#1A3629'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#1A3629'; e.currentTarget.style.borderColor = 'rgba(26,54,41,0.2)'; }}>
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* DOCTORS GRID */}
        <div style={{ marginBottom: '60px' }}>
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '24px', color: '#1A3629', margin: '0 0 4px', fontWeight: 500 }}>Our Elite Specialists</h2>
            <p style={{ color: '#8E9A94', fontSize: '14px', margin: 0 }}>Select a specialist to book your private consultation.</p>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '24px' }}>
            {doctorsLoading ? (
              <div style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: '#D4AF37', fontSize: '14px', letterSpacing: '2px', textTransform: 'uppercase' }}>
                Curating Specialists...
              </div>
            ) : doctors.length === 0 ? (
              <div className="glass-card" style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: '#8E9A94' }}>
                No specialists available at the moment.
              </div>
            ) : (
              doctors.map(doc => (
                <div key={doc.id} className="doc-card glass-card" style={{ padding: '24px', cursor: 'pointer', border: selectedDoc === doc.id ? '2px solid #D4AF37' : '1px solid rgba(255,255,255,0.4)' }} onClick={() => setSelectedDoc(doc.id)}>
                  <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                    <div style={{ width: '64px', height: '64px', borderRadius: '16px', background: 'linear-gradient(135deg, #1A3629, #2A4B3C)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#D4AF37', fontFamily: "'Playfair Display', serif", fontSize: '22px', fontWeight: 500, boxShadow: '0 8px 16px rgba(26,54,41,0.15)' }}>
                      {doc.init}
                    </div>
                    <div>
                      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '18px', color: '#1A3629', fontWeight: 500, marginBottom: '4px' }}>{doc.name}</div>
                      <div style={{ fontSize: '12px', color: '#D4AF37', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{doc.spec}</div>
                    </div>
                  </div>
                  
                  {selectedDoc === doc.id && (
                    <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid rgba(26,54,41,0.1)', animation: 'fadeIn 0.3s ease-out' }}>
                       <span style={{ fontSize: '12px', color: '#1A3629', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}><CheckCircle2 size={14} color="#D4AF37" /> Selected for Booking</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* BOOKING FLOW */}
        {selectedDoc && (
          <div className="glass-card" style={{ padding: '40px', borderTop: '4px solid #D4AF37', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: '-100px', right: '-100px', width: '300px', height: '300px', background: 'radial-gradient(circle, rgba(212,175,55,0.05) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }}></div>
            
            <h3 style={{ fontFamily: "'Playfair Display', serif", fontSize: '28px', color: '#1A3629', marginBottom: '8px', fontWeight: 500 }}>
              Schedule with {selectedDocData?.name}
            </h3>
            <p style={{ color: '#8E9A94', fontSize: '14px', marginBottom: '32px' }}>Select your preferred date and time for the private consultation.</p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '40px', alignItems: 'flex-start' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: '#8E9A94', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '12px', fontWeight: 600 }}>1. Select Date</label>
                <input type="date" value={selectedDate} min={getToday()} onChange={handleDate}
                  style={{ width: '100%', background: '#fff', border: '1px solid rgba(26,54,41,0.2)', borderRadius: '12px', padding: '14px 16px', color: '#1A3629', fontFamily: 'inherit', fontSize: '15px', outline: 'none', transition: 'all 0.3s', boxShadow: '0 2px 8px rgba(26,54,41,0.02)' }}
                  onFocus={e => { e.target.style.borderColor = '#D4AF37'; e.target.style.boxShadow = '0 4px 16px rgba(212,175,55,0.15)' }}
                  onBlur={e => { e.target.style.borderColor = 'rgba(26,54,41,0.2)'; e.target.style.boxShadow = '0 2px 8px rgba(26,54,41,0.02)' }} />
                {dateError && <div style={{ color: '#c0392b', fontSize: '12px', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={12}/> {dateError}</div>}
              </div>

              <div style={{ opacity: dateError ? 0.4 : 1, pointerEvents: dateError ? 'none' : 'auto', transition: 'opacity 0.3s' }}>
                <label style={{ display: 'block', fontSize: '11px', color: '#8E9A94', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '12px', fontWeight: 600 }}>2. Select Time Slot</label>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  {['09:00', '10:00', '11:00', '14:00', '15:00', '16:00'].map(time => {
                    const isSel = selectedSlot === time;
                    return (
                      <button key={time} className="slot-btn" onClick={() => setSelectedSlot(time)}
                        style={{ padding: '12px 24px', borderRadius: '12px', fontSize: '14px', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s', background: isSel ? '#1A3629' : '#fff', border: `1px solid ${isSel ? '#1A3629' : 'rgba(26,54,41,0.15)'}`, color: isSel ? '#D4AF37' : '#1A3629', fontWeight: isSel ? 600 : 500, boxShadow: isSel ? '0 8px 16px rgba(26,54,41,0.2)' : '0 2px 4px rgba(26,54,41,0.02)' }}>
                        {time}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {bookingError && (
              <div style={{ background: 'rgba(192,57,43,0.05)', color: '#c0392b', padding: '16px', borderRadius: '12px', margin: '32px 0 0', fontSize: '14px', border: '1px solid rgba(192,57,43,0.1)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={16} /> {typeof bookingError === 'string' ? bookingError : 'Something went wrong. Please try again.'}
              </div>
            )}

            {selectedSlot && !dateError && (
              <div style={{ marginTop: '40px', borderTop: '1px solid rgba(26,54,41,0.1)', paddingTop: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '13px', color: '#8E9A94', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Confirming For</div>
                  <div style={{ fontSize: '16px', color: '#1A3629', fontWeight: 600 }}>{formatDisplayDate(selectedDate)} at {selectedSlot}</div>
                </div>
                <button onClick={handleBook}
                  style={{ padding: '16px 40px', borderRadius: '100px', background: 'linear-gradient(135deg, #D4AF37, #C19B2E)', border: 'none', color: '#1A3629', fontFamily: "'Inter', sans-serif", fontSize: '15px', cursor: 'pointer', fontWeight: 600, boxShadow: '0 8px 24px rgba(212,175,55,0.3)', transition: 'all 0.3s', display: 'flex', alignItems: 'center', gap: '8px' }}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 12px 32px rgba(212,175,55,0.4)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(212,175,55,0.3)'; }}>
                  Confirm Reservation <ArrowRight size={18} />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}