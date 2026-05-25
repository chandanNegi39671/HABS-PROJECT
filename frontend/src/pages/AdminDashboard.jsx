import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Users, Stethoscope, Clock, AlertTriangle, Check, X, CheckCircle2, Lock } from 'lucide-react';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const [stats, setStats] = useState(null);
  const [pendingDoctors, setPendingDoctors] = useState([]);
  const [allDoctors, setAllDoctors] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [rejectionReason, setRejectionReason] = useState({});
  const [showRejectInput, setShowRejectInput] = useState({});

  const fetchPatients = async () => {
    try {
      const res = await api.get('/admin/patients');
      setPatients(res.data);
      setShowPatients(true);
    } catch (err) { console.error(err); }
  };

  const fetchData = async () => {
    try {
      const [statsRes, pendingRes, allRes] = await Promise.all([
        api.get('/admin/stats'),
        api.get('/admin/pending-doctors'),
        api.get('/admin/all-doctors'),
      ]);
      setStats(statsRes.data);
      setPendingDoctors(pendingRes.data);
      setAllDoctors(allRes.data);
    } catch (err) {
      console.error('Error fetching admin data:', err);
    }
  };

  useEffect(() => {
    if (user.role !== 'admin') { navigate('/admin/login'); return; }
    fetchData();
  }, [navigate, user.role]);

  const handleApprove = async (id) => {
    try { await api.patch(`/admin/doctors/${id}/approve`); fetchData(); }
    catch (err) { alert('Approval failed'); }
  };

  const handleReject = async (id) => {
    const reason = rejectionReason[id];
    if (!reason) { alert('Please provide a reason'); return; }
    try { await api.patch(`/admin/doctors/${id}/reject`, { reason }); fetchData(); }
    catch (err) { alert('Rejection failed'); }
  };

  const handleRevoke = async (id) => {
    if (!window.confirm('Revoke this doctor\'s access? They will be logged out and must re-apply to regain entry.')) return;
    try { await api.patch(`/admin/doctors/${id}/revoke`); fetchData(); alert('Access revoked successfully.'); }
    catch (err) { alert('Revoke failed: ' + (err.response?.data?.detail || err.message)); }
  };

  const handleLogout = () => { localStorage.clear(); navigate('/admin/login'); };

  if (!stats) return (
    <div style={{ background: '#fdfcf8', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Inter', sans-serif" }}>
      <div style={{ color: '#c9a84c', fontSize: '14px', letterSpacing: '2px' }}>LOADING ADMIN PANEL…</div>
    </div>
  );

  const statCards = [
    { label: 'Total Patients', value: stats.patients_count, icon: <Users size={20} color="#c9a84c" />, color: '#c9a84c', bg: 'rgba(201,168,76,0.10)', onClick: fetchPatients },
    { label: 'Approved Doctors', value: stats.approved_doctors_count, icon: <Stethoscope size={20} color="#4a9b6f" />, color: '#4a9b6f', bg: 'rgba(74,155,111,0.10)' },
    { label: 'Pending Approvals', value: stats.pending_doctors_count, icon: <Clock size={20} color="#a07830" />, color: '#a07830', bg: 'rgba(201,168,76,0.08)' },
    { label: 'High Risk Appts', value: stats.high_risk_appointments_count, icon: <AlertTriangle size={20} color="#c0392b" />, color: '#c0392b', bg: 'rgba(192,57,43,0.08)' },
  ];

  const statusStyle = (s) => ({
    approved: { bg: 'rgba(74,155,111,0.12)', color: '#2d7a52' },
    pending: { bg: 'rgba(201,168,76,0.12)', color: '#a07830' },
    rejected: { bg: 'rgba(192,57,43,0.10)', color: '#c0392b' },
    revoked: { bg: 'rgba(100,100,100,0.10)', color: '#555555' },
  }[s] || { bg: '#f5f0e8', color: '#a08070' });

  return (
    <div style={{ background: '#fdfcf8', minHeight: '100vh', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        .tab-btn { padding: 1rem 0; background: none; border: none; font-weight: 700; cursor: pointer; font-size: 14px; font-family: inherit; transition: color 0.2s; border-bottom: 2px solid transparent; }
        .tab-btn.active { color: #c9a84c; border-bottom-color: #c9a84c; }
        .tab-btn:not(.active) { color: #a08070; }
        .tab-btn:not(.active):hover { color: #6b4c3b; }
        .doc-row { transition: box-shadow 0.2s; }
        .doc-row:hover { box-shadow: 0 2px 12px rgba(61,43,31,0.07) !important; }
        .approve-btn { background: #c9a84c; border: none; border-radius: 8px; color: #3d2b1f; font-weight: 700; font-size: 13px; padding: 8px 18px; cursor: pointer; font-family: inherit; transition: all 0.18s; }
        .approve-btn:hover { background: #e8c96d; transform: translateY(-1px); }
        .reject-btn  { background: transparent; border: 1.5px solid rgba(192,57,43,0.35); border-radius: 8px; color: #c0392b; font-weight: 600; font-size: 13px; padding: 8px 18px; cursor: pointer; font-family: inherit; transition: all 0.18s; }
        .reject-btn:hover  { background: rgba(192,57,43,0.08); }
        .cancel-btn { background: transparent; border: 1.5px solid #e8e0d4; border-radius: 8px; color: #6b4c3b; font-size: 12px; padding: 6px 14px; cursor: pointer; font-family: inherit; transition: all 0.18s; }
        .cancel-btn:hover { border-color: #c9a84c; color: #a07830; }
        .confirm-rej-btn { background: rgba(192,57,43,0.90); border: none; border-radius: 8px; color: #fff; font-size: 12px; font-weight: 700; padding: 6px 14px; cursor: pointer; font-family: inherit; }
        .reason-input { width: 100%; height: 36px; padding: 0 10px; background: #fdfcf8; border: 1.5px solid #e8e0d4; border-radius: 8px; font-size: 13px; color: #3d2b1f; outline: none; font-family: inherit; transition: border-color 0.2s; }
        .reason-input:focus { border-color: #c9a84c; }
        th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #a08070; font-weight: 600; padding: 14px 20px; background: #f9f6f0; text-align: left; }
        td { padding: 16px 20px; border-top: 1px solid #f0ebe2; vertical-align: middle; }
      `}</style>

      {/* HEADER */}
      <header style={{ background: '#fff', borderBottom: '1px solid #e8e0d4', boxShadow: '0 1px 6px rgba(61,43,31,0.05)' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '1.25rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#c9a84c' }} />
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '22px', color: '#3d2b1f', margin: 0, fontWeight: 600 }}>HABS Admin Panel</h2>
          </div>
          <button onClick={handleLogout}
            style={{ background: 'transparent', border: '1.5px solid #e8e0d4', borderRadius: '100px', padding: '7px 20px', fontSize: '12px', color: '#6b4c3b', cursor: 'pointer', fontFamily: 'inherit', textTransform: 'uppercase', letterSpacing: '0.05em', transition: 'all 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#c0392b'; e.currentTarget.style.color = '#c0392b'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#e8e0d4'; e.currentTarget.style.color = '#6b4c3b'; }}>
            Logout
          </button>
        </div>
      </header>

      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2.5rem 1.5rem' }}>

        {/* STAT CARDS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem', marginBottom: '2.5rem' }}>
          {statCards.map(s => (
            <div key={s.label} style={{ background: '#fff', border: '1px solid #e8e0d4', borderRadius: '14px', padding: '20px 22px', boxShadow: '0 1px 6px rgba(61,43,31,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div style={{ fontSize: '10px', color: '#a08070', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>{s.label}</div>
                <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px' }}>{s.icon}</div>
              </div>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: '34px', color: s.color, lineHeight: 1 }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* TABS */}
        <div style={{ borderBottom: '1px solid #e8e0d4', display: 'flex', gap: '2rem', marginBottom: '1.75rem' }}>
          <button className={`tab-btn ${activeTab === 'pending' ? 'active' : ''}`} onClick={() => setActiveTab('pending')}>
            Pending Doctors ({pendingDoctors.length})
          </button>
          <button className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`} onClick={() => setActiveTab('all')}>
            All Doctors
          </button>
        </div>

        {/* PENDING TAB */}
        {activeTab === 'pending' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {pendingDoctors.length > 0 ? pendingDoctors.map(doc => (
              <div key={doc.id} className="doc-row" style={{ background: '#fff', border: '1px solid #e8e0d4', borderRadius: '14px', padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', boxShadow: '0 1px 4px rgba(61,43,31,0.05)', borderLeft: '3px solid #c9a84c' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '1.0625rem', color: '#3d2b1f', marginBottom: '3px' }}>{doc.full_name}</div>
                  <div style={{ color: '#a08070', fontSize: '0.875rem' }}>{doc.email} · {doc.phone}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                    <span style={{ padding: '2px 10px', borderRadius: '100px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', background: 'rgba(201,168,76,0.12)', color: '#a07830', border: '1px solid rgba(201,168,76,0.25)' }}>{doc.specialization || 'General'}</span>
                    <span style={{ color: '#d4c5ba', fontSize: '0.75rem' }}>Registered: {new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '10px' }}>
                  {!showRejectInput[doc.id] ? (
                    <div style={{ display: 'flex', gap: '0.625rem' }}>
                      <button className="reject-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }} onClick={() => setShowRejectInput({ ...showRejectInput, [doc.id]: true })}><X size={13} /> Reject</button>
                      <button className="approve-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }} onClick={() => handleApprove(doc.id)}><Check size={13} /> Approve</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '240px' }}>
                      <input type="text" className="reason-input" placeholder="Reason for rejection…"
                        value={rejectionReason[doc.id] || ''}
                        onChange={e => setRejectionReason({ ...rejectionReason, [doc.id]: e.target.value })} />
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button className="cancel-btn" onClick={() => setShowRejectInput({ ...showRejectInput, [doc.id]: false })}>Cancel</button>
                        <button className="confirm-rej-btn" onClick={() => handleReject(doc.id)}>Confirm Reject</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )) : (
              <div style={{ textAlign: 'center', padding: '3.5rem', background: '#fff', border: '1px dashed #d4c5ba', borderRadius: '14px' }}>
                <div style={{ marginBottom: '12px' }}><CheckCircle2 size={40} color="#4a9b6f" /></div>
                <div style={{ fontWeight: 700, color: '#3d2b1f', fontFamily: "'Playfair Display', serif", fontSize: '18px' }}>No pending approvals</div>
                <div style={{ color: '#a08070', fontSize: '13px', marginTop: '4px' }}>All doctors have been reviewed.</div>
              </div>
            )}
          </div>
        ) : (
          /* ALL DOCTORS TABLE */
          <div style={{ background: '#fff', border: '1px solid #e8e0d4', borderRadius: '14px', overflow: 'hidden', boxShadow: '0 1px 6px rgba(61,43,31,0.05)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th>Doctor Name</th>
                  <th>Specialization</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {allDoctors.map(doc => {
                  const st = statusStyle(doc.verification_status);
                  return (
                    <tr key={doc.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: '#3d2b1f', fontSize: '0.9375rem' }}>{doc.full_name}</div>
                        {doc.verification_status === 'rejected' && (
                          <div style={{ fontSize: '12px', color: '#c0392b', marginTop: '2px' }}>Reason: {doc.rejection_reason}</div>
                        )}
                      </td>
                      <td>
                        <span style={{ padding: '2px 10px', borderRadius: '100px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', background: 'rgba(201,168,76,0.10)', color: '#a07830', border: '1px solid rgba(201,168,76,0.2)' }}>{doc.specialization || 'General'}</span>
                      </td>
                      <td style={{ color: '#a08070', fontSize: '14px' }}>{doc.email}</td>
                      <td>
                        <span style={{ padding: '4px 12px', borderRadius: '100px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', background: st.bg, color: st.color }}>
                          {doc.verification_status}
                        </span>
                      </td>
                      <td>
                        {doc.verification_status === 'approved' && (
                          <button
                            onClick={() => handleRevoke(doc.id)}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', background: 'transparent', border: '1.5px solid rgba(192,57,43,0.4)', borderRadius: '8px', color: '#c0392b', fontSize: '11px', fontWeight: 700, padding: '5px 14px', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.18s', textTransform: 'uppercase', letterSpacing: '0.04em' }}
                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(192,57,43,0.08)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.transform = 'translateY(0)'; }}>
                            <Lock size={13} /> Revoke Access
                          </button>
                        )}
                        {doc.verification_status === 'revoked' && (
                          <span style={{ fontSize: '11px', color: '#888', fontStyle: 'italic' }}>Access revoked</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>

      {/* Patient List Modal */}
      {showPatients && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: '16px', padding: '32px', maxWidth: '700px', width: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ color: '#3d2b1f', fontFamily: 'Playfair Display, serif', fontSize: '24px' }}>All Patients ({patients.length})</h2>
              <button onClick={() => setShowPatients(false)} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#6b4c3b' }}>×</button>
            </div>
            {patients.map(p => (
              <div key={p.id} style={{ padding: '16px', borderBottom: '1px solid #f0ebe2', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#3d2b1f' }}>{p.full_name}</div>
                  <div style={{ fontSize: '13px', color: '#a08070' }}>{p.email}</div>
                </div>
                <div style={{ fontSize: '12px', color: '#a08070' }}>{p.gender || 'N/A'}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
