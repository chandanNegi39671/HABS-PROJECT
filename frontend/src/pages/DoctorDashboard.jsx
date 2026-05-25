import { useState, useEffect } from 'react';
import api from '../api';
import { Calendar, CheckCircle, AlertTriangle, XCircle, CheckCircle2, UserX, Clock, ChevronRight, LogOut, Activity, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function DoctorDashboard() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(true);

  const fetchAppointments = async () => {
    try {
      setLoading(true);
      const res = await api.get('/doctor/dashboard');
      setAppointments(res.data);
    } catch (err) {
      console.error('Error fetching appointments:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAppointments(); }, []);

  const todayDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());

  const stats = {
    total: appointments.length,
    confirmed: appointments.filter(a => a.status === 'booked' || a.status === 'confirmed').length,
    noShows: appointments.filter(a => a.status === 'no_show').length,
    alerts: appointments.filter(a => (a.risk >= 0.4) && (a.status === 'booked' || a.status === 'confirmed')).length,
  };

  const updateStatus = async (id, status) => {
    try { 
      await api.patch(`/doctor/${id}/status?status=${status}`);
      fetchAppointments();
    }
    catch (err) { 
      console.error('Error updating status:', err);
      const msg = err.response?.data?.detail || 'Failed to update status';
      alert(msg);
    }
  };

  const filtered = appointments.filter(a => {
    if (filter === 'All') return true;
    if (filter === 'Booked') return a.status === 'booked' || a.status === 'confirmed';
    if (filter === 'Completed') return a.status === 'completed';
    if (filter === 'No Show') return a.status === 'no_show';
    return true;
  });

  const statCards = [
    { label: 'Total Today',  value: stats.total,     icon: <Calendar size={22} color="#D4AF37" />,    bg: 'rgba(212,175,55,0.15)'  },
    { label: 'Confirmed',    value: stats.confirmed,  icon: <CheckCircle size={22} color="#2A4B3C" />,  bg: 'rgba(42,75,60,0.15)'  },
    { label: 'High Risk',    value: stats.alerts,     icon: <AlertTriangle size={22} color="#c0392b" />, bg: 'rgba(192,57,43,0.1)'  },
    { label: 'No Shows',     value: stats.noShows,    icon: <XCircle size={22} color="#8E9A94" />,     bg: 'rgba(142,154,148,0.15)' },
  ];

  const logout = () => { localStorage.clear(); navigate('/'); };

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'DR';

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

        .filt-btn { 
          border-radius: 100px; padding: 8px 24px; font-size: 12px; font-weight: 600; cursor: pointer; 
          border: 1px solid rgba(26,54,41,0.15); background: transparent; color: #8E9A94; 
          font-family: inherit; transition: all 0.3s; text-transform: uppercase; letter-spacing: 0.05em; 
        }
        .filt-btn.active { background: #1A3629; border-color: #1A3629; color: #D4AF37; box-shadow: 0 4px 12px rgba(26,54,41,0.15); }
        .filt-btn:not(.active):hover { border-color: #D4AF37; color: #1A3629; }

        .action-btn { border: none; background: transparent; cursor: pointer; border-radius: 10px; padding: 10px; display: flex; align-items: center; transition: all 0.2s; }
        .action-btn.green:hover { background: rgba(42,75,60,0.15); color: #2A4B3C; transform: scale(1.05); }
        .action-btn.red:hover   { background: rgba(192,57,43,0.15);  color: #c0392b; transform: scale(1.05); }
        .action-btn.gray:hover  { background: rgba(26,54,41,0.1); color: #1A3629; transform: scale(1.05); }

        .appt-row { position: relative; overflow: hidden; }
        .appt-row::before {
          content: '';
          position: absolute;
          left: 0; top: 0; bottom: 0; width: 4px;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #D4AF37; border-radius: 10px; }
      `}</style>

      {/* SIDEBAR */}
      <div className="sidebar">
        <div style={{ padding: '0 40px', marginBottom: '60px' }}>
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '28px', color: '#D4AF37', margin: 0, fontWeight: 600, letterSpacing: '0.05em' }}>HABS</h1>
          <div style={{ fontSize: '10px', color: '#A0B2A8', textTransform: 'uppercase', letterSpacing: '0.2em', marginTop: '4px' }}>Physician Portal</div>
        </div>

        <div style={{ padding: '0 40px', marginBottom: '40px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#F9F7F1', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1A3629', fontSize: '16px', fontWeight: 600, border: '1px solid #D4AF37' }}>
            {initials}
          </div>
          <div>
            <div style={{ color: '#fff', fontSize: '15px', fontWeight: 500 }}>Dr. {user?.full_name?.split(' ')[0] || 'Guest'}</div>
            <div style={{ color: '#D4AF37', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '2px' }}>Attending</div>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div className="nav-item active"><Calendar size={18} /> Schedule Overview</div>
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
            <p style={{ color: '#D4AF37', textTransform: 'uppercase', letterSpacing: '0.15em', fontSize: '12px', fontWeight: 600, marginBottom: '8px' }}>Daily Overview</p>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '42px', color: '#1A3629', margin: 0, fontWeight: 500 }}>
              Good morning, Dr. {user.full_name?.split(' ')[0] || 'Guest'}
            </h1>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ color: '#8E9A94', fontSize: '14px', margin: 0, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{todayDate}</p>
          </div>
        </div>

        {/* STAT CARDS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '24px', marginBottom: '60px' }}>
          {statCards.map(s => (
            <div key={s.label} className="glass-card" style={{ padding: '32px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                <div style={{ fontSize: '11px', color: '#8E9A94', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>{s.label}</div>
                <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{s.icon}</div>
              </div>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '48px', color: '#1A3629', lineHeight: 1 }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* APPOINTMENTS */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', flexWrap: 'wrap', gap: '20px' }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '28px', color: '#1A3629', fontWeight: 500, margin: 0 }}>Consultations</h2>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', background: 'rgba(255,255,255,0.5)', padding: '6px', borderRadius: '100px', border: '1px solid rgba(255,255,255,0.4)' }}>
              {['All', 'Booked', 'Completed', 'No Show'].map(f => (
                <button key={f} onClick={() => setFilter(f)} className={`filt-btn ${filter === f ? 'active' : ''}`}>{f}</button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '60px', color: '#D4AF37', letterSpacing: '2px', textTransform: 'uppercase', fontSize: '14px' }}>Retrieving Schedule…</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {filtered.length > 0 ? filtered.map(appt => {
                const isBooked    = appt.status === 'booked' || appt.status === 'confirmed';
                const isCompleted = appt.status === 'completed';
                const isNoShow    = appt.status === 'no_show';
                const riskPercent = appt.risk != null ? (appt.risk * 100).toFixed(0) : 0;
                const hasRisk     = appt.risk != null;
                const isHighRisk  = hasRisk && appt.risk >= 0.4;

                const leftBorder  = isCompleted ? '#2A4B3C' : isBooked ? '#D4AF37' : isNoShow ? '#c0392b' : '#8E9A94';

                return (
                  <div key={appt.id} className="appt-row glass-card" style={{
                    padding: '24px 32px',
                    display: 'flex', alignItems: 'center', gap: '32px', flexWrap: 'wrap',
                    opacity: (appt.status === 'no_show' || appt.status === 'cancelled') ? 0.5 : 1,
                  }}>
                    {/* LEFT BORDER HACK via inline style since ::before is tricky with dynamic colors */}
                    <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '4px', background: leftBorder }}></div>

                    {/* TIME */}
                    <div style={{ minWidth: '100px', borderRight: '1px solid rgba(26,54,41,0.1)', paddingRight: '24px' }}>
                      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '24px', color: '#D4AF37', marginBottom: '4px' }}>{appt.time}</div>
                      <div style={{ fontSize: '11px', color: '#8E9A94', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>Scheduled</div>
                    </div>

                    {/* PATIENT */}
                    <div style={{ flex: 1, minWidth: '200px' }}>
                      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '20px', color: '#1A3629', fontWeight: 500, marginBottom: '6px' }}>{appt.patient}</div>
                      <div style={{ fontSize: '13px', color: '#8E9A94' }}>
                        {appt.lead_time_days !== undefined ? `Booked ${appt.lead_time_days} days in advance` : 'Standard Booking'}
                      </div>
                    </div>

                    {/* RISK BADGE */}
                    {hasRisk && (
                      <div style={{ minWidth: '120px' }}>
                        <span style={{
                          padding: '6px 16px', borderRadius: '100px', fontSize: '11px', fontWeight: 600,
                          textTransform: 'uppercase', letterSpacing: '0.05em',
                          display: 'inline-flex', alignItems: 'center', gap: '6px',
                          background: isHighRisk ? 'rgba(192,57,43,0.08)' : 'rgba(42,75,60,0.08)',
                          color: isHighRisk ? '#c0392b' : '#2A4B3C',
                          border: `1px solid ${isHighRisk ? 'rgba(192,57,43,0.2)' : 'rgba(42,75,60,0.2)'}`,
                        }}>
                          {isHighRisk ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
                          {riskPercent}% Risk
                        </span>
                      </div>
                    )}

                    {/* ACTIONS */}
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      {isBooked ? (
                        <>
                          <button className="action-btn green" title="Mark Completed" onClick={() => updateStatus(appt.id, 'completed')} style={{ color: '#8E9A94' }}><CheckCircle2 size={24} /></button>
                          <button className="action-btn red"   title="Mark No-Show"   onClick={() => updateStatus(appt.id, 'no_show')}   style={{ color: '#8E9A94' }}><UserX size={24} /></button>
                          <button className="action-btn gray"  title="Cancel"         onClick={() => updateStatus(appt.id, 'cancelled')}  style={{ color: '#8E9A94' }}><Clock size={24} /></button>
                        </>
                      ) : (
                        <span style={{ fontSize: '12px', fontWeight: 600, color: leftBorder, textTransform: 'uppercase', letterSpacing: '0.1em', padding: '10px' }}>
                          {appt.status.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                  </div>
                );
              }) : (
                <div className="glass-card" style={{ textAlign: 'center', padding: '60px' }}>
                  <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(212,175,55,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', color: '#D4AF37' }}>
                    <Calendar size={30} />
                  </div>
                  <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '24px', color: '#1A3629', marginBottom: '8px', fontWeight: 500 }}>Clear Schedule</div>
                  <div style={{ fontSize: '14px', color: '#8E9A94' }}>There are no {filter !== 'All' ? filter.toLowerCase() : ''} consultations to display at this time.</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
