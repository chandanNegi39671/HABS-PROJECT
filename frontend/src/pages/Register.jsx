import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import api from '../api';
import { Mail, Lock, Eye, EyeOff, AlertTriangle, User, UserRound, Stethoscope, Tag, Phone, Check, ArrowRight, CheckCircle2, Cross } from 'lucide-react';

export default function Register() {
  const [searchParams] = useSearchParams();
  const defaultRole = searchParams.get('role') || 'patient';

  const [formData, setFormData] = useState({ full_name: '', email: '', password: '', role: defaultRole, invite_code: '', specialization: '' });
  const [step, setStep] = useState(1);
  const [otp, setOtp] = useState(Array(6).fill(''));
  const [timer, setTimer] = useState(600);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let interval;
    if (step === 2 && timer > 0) {
      interval = setInterval(() => setTimer(t => t - 1), 1000);
    }
    return () => clearInterval(interval);
  }, [step, timer]);

  const formatTimer = (s) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const handleSendOTP = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const res = await api.post('/auth/send-otp', { email: formData.email, role: formData.role });
      // Doctor ke liye OTP nahi — seedha register
      if (formData.role === 'doctor' && res.data.skip_otp) {
        await handleDoctorRegister();
        return;
      }
      setStep(2);
      setTimer(600);
      setOtp(Array(6).fill(''));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDoctorRegister = async () => {
    try {
      await api.post('/auth/verify-otp', { ...formData, otp_code: '000000' });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    const otpString = otp.join('');
    if (otpString.length !== 6) {
      setError('Please enter all 6 digits');
      setIsLoading(false);
      return;
    }
    setError('');
    setIsLoading(true);
    try {
      const res = await api.post('/auth/verify-otp', { ...formData, otp_code: otpString });
      if (formData.role === 'patient') {
        localStorage.setItem('token', res.data.access_token);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        localStorage.setItem('user_id', res.data.user_id || res.data.user?.id || '');
        navigate('/onboarding');
      } else {
        setSuccess(true);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: '100vh' }}>
      <style>{`
        @media (max-width: 900px) {
          .reg-left { display: none !important; }
          .reg-right { grid-column: 1 / -1 !important; }
        }

        .reg-left {
          background: linear-gradient(160deg, #fdfcf8 0%, #f5f0e8 60%, #f0e8d8 100%);
          border-right: 1px solid #e8e0d4;
          padding: 64px 56px;
          display: flex; flex-direction: column; justify-content: center;
          position: relative; overflow: hidden;
        }
        .rc1 { position: absolute; top: -80px; right: -80px; width: 320px; height: 320px; border-radius: 50%; border: 1px solid rgba(201,168,76,0.15); }
        .rc2 { position: absolute; bottom: 40px; left: -40px; width: 160px; height: 160px; border-radius: 50%; border: 1px solid rgba(201,168,76,0.10); }
        .reg-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(201,168,76,0.10); border: 1px solid rgba(201,168,76,0.3); border-radius: 100px; padding: 6px 16px; color: #a07830; font-size: 11px; letter-spacing: 3px; margin-bottom: 48px; align-self: flex-start; }
        .reg-heading { font-size: 46px; line-height: 1.15; color: #3d2b1f; font-family: 'Playfair Display', serif; font-style: italic; font-weight: 400; margin-bottom: 16px; }
        .reg-sub { color: #6b4c3b; font-size: 16px; line-height: 1.7; margin-bottom: 40px; }
        .gold-bar { width: 40px; height: 2px; background: #c9a84c; margin-bottom: 32px; border-radius: 2px; }
        .feature-row { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; color: #6b4c3b; font-size: 14px; }
        .feature-dot { width: 6px; height: 6px; border-radius: 50%; background: #c9a84c; flex-shrink: 0; }
        .reg-quote { border-left: 2px solid #c9a84c; padding-left: 20px; margin-top: auto; }
        .reg-quote-text { color: #6b4c3b; font-style: italic; font-size: 14px; line-height: 1.7; }
        .reg-quote-attr { color: #a08070; font-size: 11px; margin-top: 6px; letter-spacing: 1px; }

        .reg-right { background: #fdfcf8; display: flex; align-items: center; justify-content: center; padding: 48px 40px; }
        .form-card { background: #ffffff; border: 1px solid #e8e0d4; border-radius: 20px; padding: 48px 44px; max-width: 440px; width: 100%; box-shadow: 0 4px 32px rgba(61,43,31,0.08); position: relative; }
        .card-gold-top { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 120px; height: 2px; background: linear-gradient(90deg, transparent, #c9a84c, transparent); }
        .form-eyebrow { letter-spacing: 4px; font-size: 10px; color: #a07830; margin-bottom: 8px; text-transform: uppercase; }
        .form-heading { font-size: 30px; color: #3d2b1f; font-family: 'Playfair Display', serif; font-weight: 400; margin-bottom: 28px; }

        /* Role selector cards */
        .role-card { border-radius: 14px; overflow: hidden; cursor: pointer; transition: all 0.3s ease; margin-bottom: 12px; }
        .role-card-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; }
        .role-icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; transition: all 0.3s; flex-shrink: 0; }
        .role-name { font-size: 14px; font-weight: 600; transition: color 0.3s; }
        .role-desc { color: #a08070; font-size: 11px; margin-top: 2px; }
        .role-chevron { font-size: 16px; transition: transform 0.3s; }
        .role-body { overflow: hidden; transition: max-height 0.4s cubic-bezier(0.4,0,0.2,1); }

        .input-wrap { position: relative; margin-bottom: 12px; }
        .input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #a08070; font-size: 15px; pointer-events: none; }
        .habs-input { width: 100%; background: #fdfcf8; border: 1.5px solid #e8e0d4; border-radius: 10px; padding: 13px 14px 13px 44px; color: #3d2b1f; font-size: 14px; transition: all 0.22s; outline: none; font-family: inherit; }
        .habs-input::placeholder { color: #d4c5ba; }
        .habs-input:focus { border-color: #c9a84c; background: #ffffff; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }

        .error-box { background: rgba(192,57,43,0.07); border: 1px solid rgba(192,57,43,0.22); border-radius: 10px; padding: 11px 14px; color: #c0392b; font-size: 13px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }

        .habs-btn { width: 100%; background: #c9a84c; border: none; border-radius: 10px; padding: 14px; color: #3d2b1f; font-size: 15px; font-weight: 700; letter-spacing: 0.3px; cursor: pointer; margin-top: 6px; transition: all 0.22s; box-shadow: 0 4px 16px rgba(201,168,76,0.25); font-family: inherit; }
        .habs-btn:hover:not(:disabled) { background: #e8c96d; transform: translateY(-1px); box-shadow: 0 6px 24px rgba(201,168,76,0.35); }
        .habs-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .habs-btn-outline { width: 100%; margin-top: 12px; background: transparent; border: 1.5px solid #e8e0d4; border-radius: 10px; padding: 14px; color: #6b4c3b; font-size: 14px; cursor: pointer; font-family: inherit; transition: all 0.2s; }
        .habs-btn-outline:hover { border-color: #c9a84c; color: #a07830; }

        .otp-digit { width: 44px; height: 52px; text-align: center; font-size: 20px; font-weight: 700; border-radius: 10px; border: 1.5px solid #e8e0d4; background: #fdfcf8; color: #3d2b1f; outline: none; transition: all 0.2s; font-family: inherit; }
        .otp-digit:focus { border-color: #c9a84c; background: #ffffff; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }

        .bottom-note { text-align: center; margin-top: 20px; color: #a08070; font-size: 13px; }
        .bottom-link { color: #c9a84c; font-weight: 600; }
        .bottom-link:hover { text-decoration: underline; }
      `}</style>

      {/* LEFT — Brand Panel */}
      <div className="reg-left">
        <div className="rc1" /><div className="rc2" />
        <div className="reg-badge"><Cross size={12} color="#a07830" /> HABS · PRIVATE HEALTHCARE</div>
        <h1 className="reg-heading">Your health,<br />in trusted hands.</h1>
        <p className="reg-sub">Book with India's finest specialists.<br />Confirmed in minutes, not days.</p>
        <div className="gold-bar" />
        <div>
          <div className="feature-row"><div className="feature-dot" />AI-matched appointments</div>
          <div className="feature-row"><div className="feature-dot" />Zero waiting room surprises</div>
          <div className="feature-row"><div className="feature-dot" />End-to-end encrypted records</div>
          <div className="feature-row"><div className="feature-dot" />Instant PDF confirmation</div>
        </div>
        <div className="reg-quote">
          <div className="reg-quote-text">"The best investment you can make is in your own health."</div>
          <div className="reg-quote-attr">— Warren Buffett</div>
        </div>
      </div>

      {/* RIGHT — Form */}
      <div className="reg-right">
        <div className="form-card">
          <div className="card-gold-top" />

          {success ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(74,155,111,0.12)', border: '2px solid #4a9b6f', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}><CheckCircle2 size={40} color="#4a9b6f" /></div>
              <h2 className="form-heading" style={{ marginBottom: '12px' }}>Application Submitted</h2>
              <p style={{ color: '#6b4c3b', fontSize: '14px', lineHeight: 1.7, marginBottom: '24px' }}>
                Your account is under review. You will receive an email once approved. This usually takes 24–48 hours.
              </p>
              <button onClick={() => navigate('/login')} className="habs-btn" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}><><span>Go to Login</span><ArrowRight size={15} /></></button>
            </div>
          ) : (
            <>
              <div className="form-eyebrow">HABS</div>
              <h2 className="form-heading">Create Account</h2>

              {error && <div className="error-box"><AlertTriangle size={15} color="#c0392b" /> {error}</div>}

              {step === 1 ? (
                <form onSubmit={handleSendOTP}>
                  {/* PATIENT CARD */}
                  <div className="role-card"
                    onClick={() => { setFormData({ ...formData, role: formData.role === 'patient' ? '' : 'patient' }); setError(''); }}
                    style={{
                      background: formData.role === 'patient' ? '#fffdf7' : '#fdfcf8',
                      border: `1.5px solid ${formData.role === 'patient' ? '#c9a84c' : '#e8e0d4'}`,
                      boxShadow: formData.role === 'patient' ? '0 2px 12px rgba(201,168,76,0.15)' : 'none',
                    }}>
                    <div className="role-card-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div className="role-icon" style={{ background: formData.role === 'patient' ? 'rgba(201,168,76,0.15)' : '#f5f0e8', border: `1px solid ${formData.role === 'patient' ? 'rgba(201,168,76,0.4)' : '#e8e0d4'}` }}><UserRound size={22} color="#c9a84c" /></div>
                        <div>
                          <div className="role-name" style={{ color: formData.role === 'patient' ? '#a07830' : '#3d2b1f' }}>I'm a Patient</div>
                          <div className="role-desc">Book appointments, manage health</div>
                        </div>
                      </div>
                      <span className="role-chevron" style={{ color: formData.role === 'patient' ? '#c9a84c' : '#d4c5ba', transform: formData.role === 'patient' ? 'rotate(180deg)' : 'rotate(0)' }}>⌄</span>
                    </div>
                    <div className="role-body" style={{ maxHeight: formData.role === 'patient' ? '400px' : '0' }}>
                      <div style={{ padding: '0 18px 20px', borderTop: '1px solid #f0ebe2', paddingTop: '16px', opacity: formData.role === 'patient' ? 1 : 0, transition: 'opacity 0.3s 0.1s' }} onClick={e => e.stopPropagation()}>
                        <div style={{ width: '28px', height: '2px', background: '#c9a84c', marginBottom: '16px', borderRadius: '2px' }} />
                        <div className="input-wrap"><span className="input-icon"><User size={16} color="#a08070" /></span><input type="text" className="habs-input" placeholder="Full Name" value={formData.full_name} onChange={e => { setFormData({ ...formData, full_name: e.target.value }); setError(''); }} required={formData.role === 'patient'} /></div>
                        <div className="input-wrap"><span className="input-icon"><Mail size={16} color="#a08070" /></span><input type="email" className="habs-input" placeholder="Email address" value={formData.email} onChange={e => { setFormData({ ...formData, email: e.target.value }); setError(''); }} required={formData.role === 'patient'} /></div>
                        <div className="input-wrap"><span className="input-icon"><Lock size={16} color="#a08070" /></span><input type="password" className="habs-input" placeholder="Create password" value={formData.password} onChange={e => { setFormData({ ...formData, password: e.target.value }); setError(''); }} required={formData.role === 'patient'} /></div>
                        <button type="submit" className="habs-btn" disabled={isLoading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>{isLoading ? 'Please wait…' : <><span>Send OTP</span><ArrowRight size={15} /></>}</button>
                      </div>
                    </div>
                  </div>

                  {/* DOCTOR CARD */}
                  <div className="role-card"
                    onClick={() => { setFormData({ ...formData, role: formData.role === 'doctor' ? '' : 'doctor' }); setError(''); }}
                    style={{
                      background: formData.role === 'doctor' ? '#fffdf7' : '#fdfcf8',
                      border: `1.5px solid ${formData.role === 'doctor' ? '#c9a84c' : '#e8e0d4'}`,
                      boxShadow: formData.role === 'doctor' ? '0 2px 12px rgba(201,168,76,0.15)' : 'none',
                    }}>
                    <div className="role-card-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div className="role-icon" style={{ background: formData.role === 'doctor' ? 'rgba(201,168,76,0.15)' : '#f5f0e8', border: `1px solid ${formData.role === 'doctor' ? 'rgba(201,168,76,0.4)' : '#e8e0d4'}` }}><Stethoscope size={22} color="#c9a84c" /></div>
                        <div>
                          <div className="role-name" style={{ color: formData.role === 'doctor' ? '#a07830' : '#3d2b1f' }}>I'm a Doctor</div>
                          <div className="role-desc">Register as a medical professional</div>
                        </div>
                      </div>
                      <span className="role-chevron" style={{ color: formData.role === 'doctor' ? '#c9a84c' : '#d4c5ba', transform: formData.role === 'doctor' ? 'rotate(180deg)' : 'rotate(0)' }}>⌄</span>
                    </div>
                    <div className="role-body" style={{ maxHeight: formData.role === 'doctor' ? '560px' : '0' }}>
                      <div style={{ padding: '0 18px 20px', borderTop: '1px solid #f0ebe2', paddingTop: '16px', opacity: formData.role === 'doctor' ? 1 : 0, transition: 'opacity 0.3s 0.1s' }} onClick={e => e.stopPropagation()}>
                        <div style={{ width: '28px', height: '2px', background: '#c9a84c', marginBottom: '16px', borderRadius: '2px' }} />
                        <div className="input-wrap"><span className="input-icon"><User size={16} color="#a08070" /></span><input type="text" className="habs-input" placeholder="Full Name" value={formData.full_name} onChange={e => { setFormData({ ...formData, full_name: e.target.value }); setError(''); }} required={formData.role === 'doctor'} /></div>
                        <div className="input-wrap"><span className="input-icon"><Mail size={16} color="#a08070" /></span><input type="email" className="habs-input" placeholder="Email address" value={formData.email} onChange={e => { setFormData({ ...formData, email: e.target.value }); setError(''); }} required={formData.role === 'doctor'} /></div>
                        <div className="input-wrap"><span className="input-icon"><Lock size={16} color="#a08070" /></span><input type="password" className="habs-input" placeholder="Create password" value={formData.password} onChange={e => { setFormData({ ...formData, password: e.target.value }); setError(''); }} required={formData.role === 'doctor'} /></div>
                        <div className="input-wrap"><span className="input-icon"><Stethoscope size={16} color="#a08070" /></span><select className="habs-input" value={formData.specialization} onChange={e => { setFormData({ ...formData, specialization: e.target.value }); setError(''); }} required={formData.role === 'doctor'} style={{ cursor: 'pointer', appearance: 'none', backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236b4c3b' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\")", backgroundRepeat: 'no-repeat', backgroundPosition: 'right 14px center', paddingLeft: '44px', paddingRight: '2.5rem' }}>
                          <option value="">Select Specialization</option>
                          <option>Cardiologist</option>
                          <option>General Physician</option>
                          <option>Gynaecologist</option>
                          <option>Orthopaedic</option>
                          <option>Dermatologist</option>
                          <option>Paediatrician</option>
                          <option>Neurologist</option>
                          <option>Psychiatrist</option>
                          <option>Oncologist</option>
                          <option>ENT Specialist</option>
                          <option>Ophthalmologist</option>
                          <option>Urologist</option>
                          <option>Endocrinologist</option>
                          <option>Pulmonologist</option>
                          <option>Other</option>
                        </select></div>
                        <div className="input-wrap"><span className="input-icon"><Tag size={16} color="#a08070" /></span><input type="text" className="habs-input" placeholder="Doctor invite code" value={formData.invite_code} onChange={e => { setFormData({ ...formData, invite_code: e.target.value }); setError(''); }} required={formData.role === 'doctor'} /></div>
                        <button type="submit" className="habs-btn" disabled={isLoading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>{isLoading ? 'Please wait…' : <><span>Register</span><ArrowRight size={15} /></>}</button>
                      </div>
                    </div>
                  </div>

                  <div className="bottom-note">Already have an account? <Link to="/login" className="bottom-link">Sign in</Link></div>
                </form>
              ) : (
                <form onSubmit={handleVerifyOTP}>
                  <p style={{ color: '#6b4c3b', fontSize: '14px', textAlign: 'center', marginBottom: '28px', lineHeight: 1.6 }}>
                    OTP sent to <strong style={{ color: '#3d2b1f' }}>{formData.email}</strong>
                  </p>

                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginBottom: '20px' }}>
                    {otp.map((digit, idx) => (
                      <input key={idx} id={`otp-${idx}`} type="text" maxLength={1} value={digit} className="otp-digit"
                        onChange={e => {
                          const val = e.target.value;
                          if (!/^[0-9]*$/.test(val)) return;
                          const newOtp = [...otp]; newOtp[idx] = val; setOtp(newOtp);
                          if (val && idx < 5) document.getElementById(`otp-${idx + 1}`)?.focus();
                        }}
                        onKeyDown={e => { if (e.key === 'Backspace' && !otp[idx] && idx > 0) document.getElementById(`otp-${idx - 1}`)?.focus(); }}
                        required />
                    ))}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', fontSize: '13px' }}>
                    <div style={{ color: timer > 0 ? '#a08070' : '#c0392b' }}>
                      {timer > 0 ? `Expires in ${formatTimer(timer)}` : 'OTP expired'}
                    </div>
                    <button type="button" onClick={handleSendOTP} style={{ color: '#c9a84c', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontWeight: 600, fontSize: '13px' }}>Resend OTP</button>
                  </div>

                  <button type="submit" className="habs-btn" disabled={isLoading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>{isLoading ? 'Please wait…' : <><span>Verify & Register</span><ArrowRight size={15} /></>}</button>
                  <button type="button" className="habs-btn-outline" onClick={() => setStep(1)}>← Back</button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
