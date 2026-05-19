import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { Mail, Lock, Eye, EyeOff, AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react';

export default function ForgotPassword() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [resetToken, setResetToken] = useState('');
  const navigate = useNavigate();

  const handleSendOTP = async (e) => {
    if (e) e.preventDefault();
    setError(''); setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setStep(2); setOtp(['', '', '', '', '', '']);
    } catch (err) {
      setError(err.response?.data?.detail || 'No account found with this email.');
    } finally { setLoading(false); }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    const otpCode = otp.join('');
    if (otpCode.length !== 6) { setError('Please enter all 6 digits'); return; }
    setError(''); setLoading(true);
    try {
      const res = await api.post('/auth/verify-reset-otp', { email, otp_code: otpCode });
      setResetToken(res.data.reset_token);
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid or expired OTP.');
    } finally { setLoading(false); }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (newPassword.length < 6) { setError('Password must be at least 6 characters.'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match.'); return; }
    setError(''); setLoading(true);
    try {
      await api.post('/auth/reset-password', { reset_token: resetToken, new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset password.');
    } finally { setLoading(false); }
  };

  const stepLabels = ['Email', 'Verify OTP', 'New Password'];

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(160deg, #fdfcf8 0%, #f5f0e8 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        .fp-card { background: #ffffff; border: 1px solid #e8e0d4; border-radius: 20px; padding: 52px 48px; max-width: 440px; width: 100%; box-shadow: 0 4px 32px rgba(61,43,31,0.09); position: relative; }
        .fp-gold-top { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 120px; height: 2px; background: linear-gradient(90deg, transparent, #c9a84c, transparent); }
        .fp-eyebrow { letter-spacing: 4px; font-size: 10px; color: #a07830; margin-bottom: 8px; text-transform: uppercase; font-weight: 600; }
        .fp-heading { font-size: 30px; color: #3d2b1f; font-family: 'Playfair Display', serif; font-weight: 400; margin-bottom: 8px; }
        .fp-sub { color: #6b4c3b; font-size: 14px; margin-bottom: 28px; line-height: 1.6; }

        .step-track { display: flex; align-items: center; gap: 6px; margin-bottom: 32px; }
        .step-seg { height: 4px; border-radius: 4px; transition: all 0.35s ease; }
        .step-seg.done   { background: #4a9b6f; }
        .step-seg.active { background: #c9a84c; }
        .step-seg.future { background: #e8e0d4; }

        .input-wrap { position: relative; margin-bottom: 14px; }
        .input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #a08070; font-size: 15px; pointer-events: none; }
        .habs-input { width: 100%; background: #fdfcf8; border: 1.5px solid #e8e0d4; border-radius: 10px; padding: 14px 14px 14px 44px; color: #3d2b1f; font-size: 15px; transition: all 0.22s; outline: none; font-family: inherit; }
        .habs-input::placeholder { color: #d4c5ba; }
        .habs-input:focus { border-color: #c9a84c; background: #ffffff; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }

        .otp-digit { width: 44px; height: 52px; text-align: center; font-size: 20px; font-weight: 700; border-radius: 10px; border: 1.5px solid #e8e0d4; background: #fdfcf8; color: #3d2b1f; outline: none; transition: all 0.2s; font-family: inherit; }
        .otp-digit:focus { border-color: #c9a84c; background: #ffffff; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }

        .error-box { background: rgba(192,57,43,0.07); border: 1px solid rgba(192,57,43,0.22); border-radius: 10px; padding: 11px 14px; color: #c0392b; font-size: 13px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }

        .habs-btn { width: 100%; background: #c9a84c; border: none; border-radius: 10px; padding: 15px; color: #3d2b1f; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 6px; transition: all 0.22s; box-shadow: 0 4px 16px rgba(201,168,76,0.25); font-family: inherit; }
        .habs-btn:hover:not(:disabled) { background: #e8c96d; transform: translateY(-1px); box-shadow: 0 6px 24px rgba(201,168,76,0.35); }
        .habs-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .back-link { display: block; text-align: center; margin-top: 20px; color: #c9a84c; font-size: 13px; font-weight: 600; }
        .back-link:hover { text-decoration: underline; }
      `}</style>

      <div className="fp-card">
        <div className="fp-gold-top" />

        {success ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(74,155,111,0.12)', border: '2px solid #4a9b6f', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}><CheckCircle2 size={40} color="#4a9b6f" /></div>
            <h2 className="fp-heading" style={{ marginBottom: '12px' }}>Password Reset!</h2>
            <p className="fp-sub">You can now sign in with your new password.</p>
            <button onClick={() => navigate('/login')} className="habs-btn" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}><><span>Go to Login</span><ArrowRight size={15} /></></button>
          </div>
        ) : (
          <>
            {/* Step progress track */}
            <div className="step-track">
              {[1, 2, 3].map(n => (
                <div key={n} className={`step-seg ${n < step ? 'done' : n === step ? 'active' : 'future'}`}
                  style={{ flex: n === step ? 2 : 1 }} />
              ))}
            </div>

            <div className="fp-eyebrow">HABS — {stepLabels[step - 1]}</div>

            {/* STEP 1 */}
            {step === 1 && (
              <>
                <h2 className="fp-heading">Forgot Password</h2>
                <p className="fp-sub">Enter your registered email and we'll send you a verification code.</p>
                {error && <div className="error-box"><AlertTriangle size={15} color="#c0392b" /> {error}</div>}
                <form onSubmit={handleSendOTP}>
                  <div className="input-wrap">
                    <span className="input-icon"><Mail size={16} color="#a08070" /></span>
                    <input type="email" className="habs-input" placeholder="Email address" value={email}
                      onChange={e => { setEmail(e.target.value); setError(''); }} required />
                  </div>
                  <button type="submit" className="habs-btn" disabled={loading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>{loading ? 'Please wait…' : <><span>Send OTP</span><ArrowRight size={15} /></>}</button>
                </form>
                <Link to="/login" className="back-link">← Back to Login</Link>
              </>
            )}

            {/* STEP 2 */}
            {step === 2 && (
              <>
                <h2 className="fp-heading">Verify Email</h2>
                <p className="fp-sub">OTP sent to <strong style={{ color: '#3d2b1f' }}>{email}</strong></p>
                {error && <div className="error-box"><AlertTriangle size={15} color="#c0392b" /> {error}</div>}
                <form onSubmit={handleVerifyOTP}>
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginBottom: '24px' }}>
                    {otp.map((digit, idx) => (
                      <input key={idx} id={`fp-otp-${idx}`} type="text" maxLength={1} value={digit} className="otp-digit"
                        onChange={e => {
                          const val = e.target.value;
                          if (!/^[0-9]*$/.test(val)) return;
                          const n = [...otp]; n[idx] = val; setOtp(n);
                          if (val && idx < 5) document.getElementById(`fp-otp-${idx + 1}`)?.focus();
                        }}
                        onKeyDown={e => { if (e.key === 'Backspace' && !otp[idx] && idx > 0) document.getElementById(`fp-otp-${idx - 1}`)?.focus(); }}
                        required />
                    ))}
                  </div>
                  <button type="submit" className="habs-btn" disabled={loading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>{loading ? 'Please wait…' : <><span>Verify OTP</span><ArrowRight size={15} /></>}</button>
                  <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '13px', color: '#a08070' }}>
                    Didn't receive it?{' '}
                    <button type="button" onClick={() => handleSendOTP()} style={{ color: '#c9a84c', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Resend</button>
                  </div>
                </form>
              </>
            )}

            {/* STEP 3 */}
            {step === 3 && (
              <>
                <h2 className="fp-heading">New Password</h2>
                <p className="fp-sub">Secure your account with a strong new password.</p>
                {error && <div className="error-box"><AlertTriangle size={15} color="#c0392b" /> {error}</div>}
                <form onSubmit={handleResetPassword}>
                  <div className="input-wrap">
                    <span className="input-icon"><Lock size={16} color="#a08070" /></span>
                    <input type={showNewPassword ? 'text' : 'password'} className="habs-input" placeholder="New password"
                      value={newPassword} onChange={e => { setNewPassword(e.target.value); setError(''); }} required />
                    <button type="button" onClick={() => setShowNewPassword(!showNewPassword)}
                      style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', color: '#a08070' }}>
                      {showNewPassword ? <Eye size={16} color="#a08070" /> : <EyeOff size={16} color="#a08070" />}
                    </button>
                  </div>
                  <div className="input-wrap">
                    <span className="input-icon"><Lock size={16} color="#a08070" /></span>
                    <input type={showConfirmPassword ? 'text' : 'password'} className="habs-input" placeholder="Confirm password"
                      value={confirmPassword} onChange={e => { setConfirmPassword(e.target.value); setError(''); }} required />
                    <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', color: '#a08070' }}>
                      {showConfirmPassword ? <Eye size={16} color="#a08070" /> : <EyeOff size={16} color="#a08070" />}
                    </button>
                  </div>
                  <button type="submit" className="habs-btn" disabled={loading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>{loading ? 'Please wait…' : <><span>Reset Password</span><ArrowRight size={15} /></>}</button>
                </form>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
