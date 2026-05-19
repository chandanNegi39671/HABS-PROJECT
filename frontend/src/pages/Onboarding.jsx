import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { Check, AlertTriangle, ArrowRight } from 'lucide-react';

const STEPS = ['Personal Info', 'Health Profile', 'Almost Done!'];

const initialData = {
  date_of_birth: '',
  gender: '',
  blood_group: '',
  diabetes: false,
  hypertension: false,
  alcoholism: false,
  has_chronic_condition: false,
};

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const handleSubmit = async () => {
    setIsLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      await api.post('/patient/onboarding', form, {
        headers: { Authorization: `Bearer ${token}` },
      });
      navigate('/patient/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile');
    } finally {
      setIsLoading(false);
    }
  };

  const skip = () => navigate('/patient/dashboard');

  const PillToggle = ({ label, value, onChange }) => (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#3d2b1f', marginBottom: '0.75rem' }}>{label}</div>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        {[{ label: 'Yes', val: true }, { label: 'No', val: false }].map(opt => (
          <button key={opt.label} type="button" onClick={() => onChange(opt.val)}
            style={{
              padding: '0.5rem 2rem', borderRadius: '100px', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 600,
              border: value === opt.val ? 'none' : '1.5px solid #e8e0d4',
              backgroundColor: value === opt.val ? '#c9a84c' : 'transparent',
              color: value === opt.val ? '#3d2b1f' : '#6b4c3b',
              transition: 'all 0.2s',
              fontFamily: 'inherit',
            }}>
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );

  const GenderPill = ({ label }) => {
    const selected = form.gender === label;
    return (
      <button type="button" onClick={() => setForm({ ...form, gender: label })}
        style={{
          flex: 1, padding: '0.6rem 0', borderRadius: '100px', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 600,
          border: selected ? 'none' : '1.5px solid #e8e0d4',
          backgroundColor: selected ? '#c9a84c' : 'transparent',
          color: selected ? '#3d2b1f' : '#6b4c3b',
          transition: 'all 0.2s', fontFamily: 'inherit',
        }}>
        {label}
      </button>
    );
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        @media (max-width: 768px) {
          .ob-left { display: none !important; }
          .ob-right { width: 100% !important; }
        }
        .ob-input {
          width: 100%; height: 50px; padding: 0 1rem;
          background: #ffffff; border: 1.5px solid #e8e0d4; border-radius: 10px;
          font-size: 0.9375rem; color: #3d2b1f; font-family: inherit;
          outline: none; transition: all 0.22s;
        }
        .ob-input:focus { border-color: #c9a84c; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }
        .ob-input option { background: #fff; color: #3d2b1f; }
        .ob-btn-primary {
          width: 100%; height: 50px; border-radius: 100px;
          background: #c9a84c; border: none; color: #3d2b1f;
          font-weight: 700; font-size: 0.9375rem; cursor: pointer; font-family: inherit;
          transition: all 0.22s; box-shadow: 0 4px 16px rgba(201,168,76,0.25);
        }
        .ob-btn-primary:hover:not(:disabled) { background: #e8c96d; transform: translateY(-1px); }
        .ob-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
        .ob-btn-outline {
          flex: 1; height: 50px; border-radius: 100px;
          background: transparent; border: 1.5px solid #e8e0d4; color: #6b4c3b;
          font-weight: 600; font-size: 0.9375rem; cursor: pointer; font-family: inherit;
          transition: all 0.22s;
        }
        .ob-btn-outline:hover { border-color: #c9a84c; color: #a07830; }
      `}</style>

      {/* LEFT — Warm Side Panel */}
      <div className="ob-left" style={{
        width: '38%', minWidth: '320px',
        background: 'linear-gradient(160deg, #fdfcf8 0%, #f5f0e8 60%, #f0e8d8 100%)',
        borderRight: '1px solid #e8e0d4',
        padding: '4rem 3rem', display: 'flex', flexDirection: 'column', justifyContent: 'center',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Decorative circles */}
        <div style={{ position: 'absolute', top: '-60px', right: '-60px', width: '260px', height: '260px', borderRadius: '50%', border: '1px solid rgba(201,168,76,0.15)' }} />
        <div style={{ position: 'absolute', bottom: '40px', left: '-40px', width: '140px', height: '140px', borderRadius: '50%', border: '1px solid rgba(201,168,76,0.10)' }} />

        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3rem', textDecoration: 'none' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#c9a84c' }} />
          <span style={{ fontFamily: "'Playfair Display', serif", fontSize: '1.5rem', color: '#3d2b1f', fontWeight: 700 }}>HABS</span>
        </Link>

        <div style={{ marginBottom: '2.5rem' }}>
          <div style={{ fontSize: '10px', letterSpacing: '0.2em', textTransform: 'uppercase', color: '#a07830', marginBottom: '12px', fontWeight: 600 }}>
            Setting Up Your Profile
          </div>
          <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '2rem', color: '#3d2b1f', fontWeight: 500, lineHeight: 1.25, margin: '0 0 1rem' }}>
            Help us personalise your experience.
          </h2>
          <p style={{ color: '#6b4c3b', fontSize: '0.9rem', lineHeight: 1.7, margin: 0 }}>
            This information helps your doctors provide better care. All data is private and secure.
          </p>
        </div>

        {/* Progress steps */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2.5rem', gap: '0' }}>
          {STEPS.map((s, i) => {
            const num = i + 1;
            const isDone = num < step;
            const isActive = num === step;
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : 'none' }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.75rem', fontWeight: 700, flexShrink: 0, zIndex: 1,
                  backgroundColor: isDone ? '#4a9b6f' : isActive ? '#c9a84c' : '#e8e0d4',
                  color: isDone || isActive ? '#fff' : '#a08070',
                  transition: 'all 0.3s', boxShadow: isActive ? '0 0 0 4px rgba(201,168,76,0.2)' : 'none',
                }}>
                  {isDone ? <Check size={14} color="currentColor" /> : num}
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{
                    flex: 1, height: '2px', margin: '0 6px',
                    backgroundColor: isDone ? '#4a9b6f' : '#e8e0d4',
                    transition: 'all 0.3s',
                  }} />
                )}
              </div>
            );
          })}
        </div>

        {/* Step list */}
        <div>
          {STEPS.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', opacity: i + 1 <= step ? 1 : 0.4 }}>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0, backgroundColor: i + 1 < step ? '#4a9b6f' : i + 1 === step ? '#c9a84c' : '#d4c5ba' }} />
              <span style={{ color: i + 1 === step ? '#3d2b1f' : '#a08070', fontSize: '0.875rem', fontWeight: i + 1 === step ? 600 : 400 }}>{s}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 'auto', borderLeft: '2px solid #c9a84c', paddingLeft: '16px' }}>
          <p style={{ color: '#6b4c3b', fontStyle: 'italic', fontSize: '13px', lineHeight: 1.7, margin: 0 }}>
            "An ounce of prevention is worth a pound of cure."
          </p>
          <p style={{ color: '#a08070', fontSize: '11px', marginTop: '6px', letterSpacing: '1px' }}>— Benjamin Franklin</p>
        </div>
      </div>

      {/* RIGHT — Form Panel */}
      <div className="ob-right" style={{
        flex: 1, background: '#ffffff',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem 3rem',
      }}>
        <div style={{ width: '100%', maxWidth: '480px' }}>
          {error && (
            <div style={{ background: 'rgba(192,57,43,0.07)', border: '1px solid rgba(192,57,43,0.22)', color: '#c0392b', padding: '12px 16px', borderRadius: '10px', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
              <AlertTriangle size={15} color="#c0392b" /> {error}
            </div>
          )}

          {/* STEP 1 */}
          {step === 1 && (
            <>
              <div style={{ fontSize: '10px', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#a07830', marginBottom: '6px', fontWeight: 600 }}>Step 1 of 3</div>
              <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '2rem', color: '#3d2b1f', margin: '0 0 2rem', fontWeight: 500 }}>Personal Info</h1>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#6b4c3b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Date of Birth</label>
                <input type="date" className="ob-input" value={form.date_of_birth} onChange={e => setForm({ ...form, date_of_birth: e.target.value })} />
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#6b4c3b', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Gender</label>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <GenderPill label="Male" /><GenderPill label="Female" /><GenderPill label="Other" />
                </div>
              </div>

              <div style={{ marginBottom: '2.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#6b4c3b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Blood Group</label>
                <select className="ob-input" value={form.blood_group} onChange={e => setForm({ ...form, blood_group: e.target.value })}
                  style={{ cursor: 'pointer', appearance: 'none', backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236b4c3b' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\")", backgroundRepeat: 'no-repeat', backgroundPosition: 'right 14px center', paddingRight: '2.5rem' }}>
                  <option value="">Select blood group</option>
                  {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map(bg => <option key={bg} value={bg}>{bg}</option>)}
                </select>
              </div>

              <button className="ob-btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }} onClick={() => setStep(2)}><><span>Next</span><ArrowRight size={15} /></></button>
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button type="button" onClick={skip} style={{ background: 'none', border: 'none', color: '#a08070', fontSize: '0.875rem', cursor: 'pointer', fontFamily: 'inherit' }}>Skip for now →</button>
              </div>
            </>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <>
              <div style={{ fontSize: '10px', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#a07830', marginBottom: '6px', fontWeight: 600 }}>Step 2 of 3</div>
              <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '2rem', color: '#3d2b1f', margin: '0 0 2rem', fontWeight: 500 }}>Health Profile</h1>

              <PillToggle label="Do you have Diabetes?" value={form.diabetes} onChange={v => setForm({ ...form, diabetes: v })} />
              <PillToggle label="Do you have Hypertension / BP?" value={form.hypertension} onChange={v => setForm({ ...form, hypertension: v })} />
              <PillToggle label="Do you consume alcohol?" value={form.alcoholism} onChange={v => setForm({ ...form, alcoholism: v })} />
              <PillToggle label="Any chronic condition?" value={form.has_chronic_condition} onChange={v => setForm({ ...form, has_chronic_condition: v })} />

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button className="ob-btn-outline" onClick={() => setStep(1)}>← Back</button>
                <button className="ob-btn-primary" style={{ flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }} onClick={() => setStep(3)}><><span>Next</span><ArrowRight size={15} /></></button>
              </div>
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button type="button" onClick={skip} style={{ background: 'none', border: 'none', color: '#a08070', fontSize: '0.875rem', cursor: 'pointer', fontFamily: 'inherit' }}>Skip for now →</button>
              </div>
            </>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <>
              <div style={{ fontSize: '10px', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#a07830', marginBottom: '6px', fontWeight: 600 }}>Step 3 of 3</div>
              <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: '2rem', color: '#3d2b1f', margin: '0 0 0.75rem', fontWeight: 500 }}>Almost Done!</h1>
              <p style={{ color: '#6b4c3b', marginBottom: '1.75rem', fontSize: '0.9375rem' }}>Review your profile before we save it.</p>

              {/* Summary Card */}
              <div style={{ background: '#fdfcf8', border: '1px solid #e8e0d4', borderRadius: '14px', padding: '1.5rem', marginBottom: '2rem', borderLeft: '3px solid #c9a84c' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                  {[
                    ['Date of Birth', form.date_of_birth || '—'],
                    ['Gender', form.gender || '—'],
                    ['Blood Group', form.blood_group || '—'],
                    ['Diabetes', form.diabetes ? 'Yes' : 'No'],
                    ['Hypertension', form.hypertension ? 'Yes' : 'No'],
                    ['Alcoholism', form.alcoholism ? 'Yes' : 'No'],
                    ['Chronic Condition', form.has_chronic_condition ? 'Yes' : 'No'],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#a08070', marginBottom: '3px', fontWeight: 600 }}>{k}</div>
                      <div style={{ fontWeight: 600, color: '#3d2b1f', fontSize: '0.9375rem' }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button className="ob-btn-outline" onClick={() => setStep(2)}>← Back</button>
                <button className="ob-btn-primary" style={{ flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }} onClick={handleSubmit} disabled={isLoading}>
                  {isLoading ? 'Saving…' : <><span>Complete Profile</span><ArrowRight size={15} /></>}
                </button>
              </div>
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <button type="button" onClick={skip} style={{ background: 'none', border: 'none', color: '#a08070', fontSize: '0.875rem', cursor: 'pointer', fontFamily: 'inherit' }}>Skip for now →</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
