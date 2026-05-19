import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { Mail, Lock, Eye, EyeOff, AlertTriangle, ShieldCheck, ArrowRight } from 'lucide-react';

export default function AdminLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const res = await api.post('/auth/admin/login', { email, password });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('user_id', res.data.user_id || res.data.user?.id || '');
      localStorage.setItem('user', JSON.stringify(res.data.user));
      navigate('/admin/dashboard');
    } catch (err) {
      setError('Invalid admin credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(160deg, #fdfcf8 0%, #f5f0e8 60%, #f0e8d8 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        .admin-card { background: #fff; border: 1px solid #e8e0d4; border-radius: 20px; padding: 52px 48px; max-width: 420px; width: 100%; box-shadow: 0 4px 32px rgba(61,43,31,0.09); position: relative; }
        .admin-gold-top { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 120px; height: 2px; background: linear-gradient(90deg, transparent, #c9a84c, transparent); }
        .admin-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(201,168,76,0.10); border: 1px solid rgba(201,168,76,0.30); border-radius: 100px; padding: 6px 16px; color: #a07830; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; }
        .admin-heading { font-size: 30px; color: #3d2b1f; font-family: 'Playfair Display', serif; font-weight: 400; margin-bottom: 6px; }
        .admin-sub { color: #a08070; font-size: 14px; margin-bottom: 28px; }
        .input-wrap { position: relative; margin-bottom: 14px; }
        .input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #a08070; font-size: 15px; pointer-events: none; }
        .habs-input { width: 100%; background: #fdfcf8; border: 1.5px solid #e8e0d4; border-radius: 10px; padding: 14px 14px 14px 44px; color: #3d2b1f; font-size: 15px; transition: all 0.22s; outline: none; font-family: inherit; }
        .habs-input::placeholder { color: #d4c5ba; }
        .habs-input:focus { border-color: #c9a84c; background: #fff; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }
        .error-box { background: rgba(192,57,43,0.07); border: 1px solid rgba(192,57,43,0.22); border-radius: 10px; padding: 11px 14px; color: #c0392b; font-size: 13px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
        .admin-btn { width: 100%; background: #c9a84c; border: none; border-radius: 10px; padding: 15px; color: #3d2b1f; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 6px; transition: all 0.22s; box-shadow: 0 4px 16px rgba(201,168,76,0.25); font-family: inherit; }
        .admin-btn:hover:not(:disabled) { background: #e8c96d; transform: translateY(-1px); box-shadow: 0 6px 24px rgba(201,168,76,0.35); }
        .admin-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .bottom-note { text-align: center; margin-top: 20px; }
        .bottom-link { color: #c9a84c; font-size: 13px; font-weight: 600; }
        .bottom-link:hover { text-decoration: underline; }
      `}</style>

      <div className="admin-card">
        <div className="admin-gold-top" />

        <div className="admin-badge">
          <ShieldCheck size={12} color="#a07830" />
          Admin Access
        </div>
        <h2 className="admin-heading">Admin Portal</h2>
        <p className="admin-sub">Restricted. Authorised personnel only.</p>

        {error && <div className="error-box"><AlertTriangle size={15} color="#c0392b" /> {error}</div>}

        <form onSubmit={handleLogin}>
          <div className="input-wrap">
            <span className="input-icon"><Mail size={16} color="#a08070" /></span>
            <input type="email" className="habs-input" placeholder="Admin Email"
              value={email} onChange={e => { setEmail(e.target.value); setError(''); }} required />
          </div>

          <div className="input-wrap" style={{ marginBottom: '24px' }}>
            <span className="input-icon"><Lock size={16} color="#a08070" /></span>
            <input type={showPassword ? 'text' : 'password'} className="habs-input" placeholder="Password"
              value={password} onChange={e => { setPassword(e.target.value); setError(''); }} required />
            <button type="button" onClick={() => setShowPassword(!showPassword)}
              style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', color: '#a08070' }}>
              {showPassword ? <Eye size={16} color="#a08070" /> : <EyeOff size={16} color="#a08070" />}
            </button>
          </div>

          <button type="submit" className="admin-btn" disabled={isLoading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
            {isLoading ? 'Authenticating…' : <><span>Access Panel</span><ArrowRight size={15} /></>}
          </button>
        </form>

        <div className="bottom-note">
          <Link to="/login" className="bottom-link">← Back to Patient Login</Link>
        </div>
      </div>
    </div>
  );
}
