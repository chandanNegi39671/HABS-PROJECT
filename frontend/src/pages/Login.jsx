import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { Mail, Lock, Eye, EyeOff, AlertTriangle, ArrowRight, Cross } from 'lucide-react';

export default function Login() {
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
      const res = await api.post('/auth/login', { email, password });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('user_id', res.data.user_id);
      localStorage.setItem('role', res.data.user?.role);
      localStorage.setItem('full_name', res.data.user?.full_name);
      localStorage.setItem('user', JSON.stringify(res.data.user));
      if (res.data.user.role === 'doctor') {
        navigate('/doctor/dashboard');
      } else {
        navigate('/patient/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: '100vh' }}>
      <style>{`
        @media (max-width: 900px) {
          .login-left { display: none !important; }
          .login-right { grid-column: 1 / -1 !important; }
        }

        /* Left panel */
        .login-left {
          background: linear-gradient(160deg, #fdfcf8 0%, #f5f0e8 60%, #f0e8d8 100%);
          border-right: 1px solid #e8e0d4;
          padding: 64px 56px;
          display: flex; flex-direction: column; justify-content: center;
          position: relative; overflow: hidden;
        }
        .lp-circle-1 {
          position: absolute; top: -80px; right: -80px;
          width: 320px; height: 320px; border-radius: 50%;
          border: 1px solid rgba(201,168,76,0.15);
        }
        .lp-circle-2 {
          position: absolute; bottom: 40px; left: -40px;
          width: 160px; height: 160px; border-radius: 50%;
          border: 1px solid rgba(201,168,76,0.10);
        }
        .lp-badge {
          display: inline-flex; align-items: center; gap: 8px;
          background: rgba(201,168,76,0.10); border: 1px solid rgba(201,168,76,0.3);
          border-radius: 100px; padding: 6px 16px;
          color: #a07830; font-size: 11px; letter-spacing: 3px;
          margin-bottom: 48px; align-self: flex-start;
        }
        .lp-heading {
          font-size: 46px; line-height: 1.15;
          color: #3d2b1f; font-family: 'Playfair Display', serif;
          font-style: italic; font-weight: 400; margin-bottom: 16px;
        }
        .lp-sub {
          color: #6b4c3b; font-size: 16px; line-height: 1.7; margin-bottom: 40px;
        }
        .gold-bar { width: 40px; height: 2px; background: #c9a84c; margin-bottom: 40px; border-radius: 2px; }
        .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 40px; }
        .stat-card {
          background: #ffffff; border: 1px solid #e8e0d4;
          border-radius: 12px; padding: 16px; text-align: center;
          box-shadow: 0 2px 8px rgba(61,43,31,0.06);
        }
        .stat-num { color: #c9a84c; font-size: 22px; font-weight: 700; display: block; font-family: 'Playfair Display', serif; }
        .stat-lbl { color: #a08070; font-size: 11px; margin-top: 4px; letter-spacing: 0.05em; }
        .quote-block { border-left: 2px solid #c9a84c; padding-left: 20px; margin-top: auto; }
        .quote-text { color: #6b4c3b; font-style: italic; font-size: 14px; line-height: 1.7; }
        .quote-attr { color: #a08070; font-size: 11px; margin-top: 6px; letter-spacing: 1px; }

        /* Right panel / form */
        .login-right {
          background: #fdfcf8;
          display: flex; align-items: center; justify-content: center;
          padding: 48px 40px;
        }
        .form-card {
          background: #ffffff;
          border: 1px solid #e8e0d4;
          border-radius: 20px;
          padding: 52px 48px;
          max-width: 440px; width: 100%;
          box-shadow: 0 4px 32px rgba(61,43,31,0.08);
          position: relative;
        }
        .card-gold-top {
          position: absolute; top: 0; left: 50%; transform: translateX(-50%);
          width: 120px; height: 2px;
          background: linear-gradient(90deg, transparent, #c9a84c, transparent);
        }
        .form-eyebrow { letter-spacing: 4px; font-size: 10px; color: #a07830; margin-bottom: 8px; text-transform: uppercase; }
        .form-heading { font-size: 32px; color: #3d2b1f; font-family: 'Playfair Display', serif; font-weight: 400; margin-bottom: 32px; }

        .input-wrap { position: relative; margin-bottom: 14px; }
        .input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #a08070; font-size: 15px; pointer-events: none; }
        .habs-input {
          width: 100%; background: #ffffff;
          border: 1.5px solid #e8e0d4; border-radius: 10px;
          padding: 14px 14px 14px 44px;
          color: #3d2b1f; font-size: 15px;
          transition: all 0.22s; outline: none; font-family: inherit;
        }
        .habs-input::placeholder { color: #d4c5ba; }
        .habs-input:focus {
          border-color: #c9a84c;
          box-shadow: 0 0 0 3px rgba(201,168,76,0.15);
        }

        .error-box {
          background: rgba(192,57,43,0.07); border: 1px solid rgba(192,57,43,0.22);
          border-radius: 10px; padding: 12px 16px; color: #c0392b;
          font-size: 13px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
        }

        .habs-btn {
          width: 100%; background: #c9a84c; border: none; border-radius: 10px;
          padding: 15px; color: #3d2b1f; font-size: 15px; font-weight: 700;
          letter-spacing: 0.3px; cursor: pointer; margin-top: 8px;
          transition: all 0.22s; box-shadow: 0 4px 16px rgba(201,168,76,0.25);
          font-family: inherit;
        }
        .habs-btn:hover:not(:disabled) { background: #e8c96d; transform: translateY(-1px); box-shadow: 0 6px 24px rgba(201,168,76,0.35); }
        .habs-btn:active:not(:disabled) { transform: translateY(0); }
        .habs-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .bottom-note { text-align: center; margin-top: 24px; color: #a08070; font-size: 14px; }
        .bottom-link { color: #c9a84c; font-weight: 600; }
        .bottom-link:hover { text-decoration: underline; }
      `}</style>

      {/* LEFT — Brand Panel */}
      <div className="login-left">
        <div className="lp-circle-1" />
        <div className="lp-circle-2" />

        <div className="lp-badge">
          <Cross size={12} color="#a07830" />
          HABS · PRIVATE HEALTHCARE
        </div>

        <h1 className="lp-heading">Welcome back.<br />We kept your spot.</h1>
        <p className="lp-sub">Your appointments, records, and doctors —<br />all exactly where you left them.</p>

        <div className="gold-bar" />

        <div className="stat-grid">
          <div className="stat-card"><span className="stat-num">91%</span><div className="stat-lbl">Model Accuracy</div></div>
          <div className="stat-card"><span className="stat-num">500+</span><div className="stat-lbl">Appointments Tested</div></div>
          <div className="stat-card"><span className="stat-num">0.88</span><div className="stat-lbl">AUC–ROC Score</div></div>
        </div>

        <div className="quote-block">
          <div className="quote-text">"Medicine is not only a science; it is also an art."</div>
          <div className="quote-attr">— Paracelsus</div>
        </div>
      </div>

      {/* RIGHT — Form */}
      <div className="login-right">
        <div className="form-card">
          <div className="card-gold-top" />

          <div className="form-eyebrow">HABS</div>
          <h2 className="form-heading">Sign In</h2>

          {error && <div className="error-box"><AlertTriangle size={15} color="#c0392b" /> {error.includes('under review') || error.includes('rejected') ? error : 'Invalid email or password.'}</div>}

          <form onSubmit={handleLogin}>
            <div className="input-wrap">
              <span className="input-icon"><Mail size={16} color="#a08070" /></span>
              <input type="email" className="habs-input" placeholder="Email address"
                value={email} onChange={(e) => { setEmail(e.target.value); setError(''); }} required />
            </div>

            <div className="input-wrap" style={{ marginBottom: '6px' }}>
              <span className="input-icon"><Lock size={16} color="#a08070" /></span>
              <input type={showPassword ? 'text' : 'password'} className="habs-input" placeholder="Password"
                value={password} onChange={(e) => { setPassword(e.target.value); setError(''); }} required />
              <button type="button" onClick={() => setShowPassword(!showPassword)}
                style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', color: '#a08070' }}>
                {showPassword ? <Eye size={16} color="#a08070" /> : <EyeOff size={16} color="#a08070" />}
              </button>
            </div>

            <div style={{ textAlign: 'right', marginBottom: '24px' }}>
              <Link to="/forgot-password" style={{ color: '#c9a84c', fontSize: '13px' }}
                onMouseEnter={e => e.target.style.textDecoration = 'underline'}
                onMouseLeave={e => e.target.style.textDecoration = 'none'}>
                Forgot password?
              </Link>
            </div>

            <button type="submit" className="habs-btn" disabled={isLoading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
              {isLoading ? 'Please wait…' : <><span>Sign In</span><ArrowRight size={15} /></>}
            </button>
          </form>

          <div className="bottom-note">
            New to HABS? <Link to="/register" className="bottom-link">Create account →</Link>
          </div>

          {/* Subtle admin entry — intentionally low-visibility */}
          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <Link to="/admin/login"
              style={{ fontSize: '11px', color: '#d4c5ba', letterSpacing: '0.05em' }}
              onMouseEnter={e => e.target.style.color = '#a08070'}
              onMouseLeave={e => e.target.style.color = '#d4c5ba'}>
              Admin →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}