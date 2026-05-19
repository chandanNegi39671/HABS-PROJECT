import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Onboarding from './pages/Onboarding';
import PatientDashboard from './pages/PatientDashboard';
import DoctorDashboard from './pages/DoctorDashboard';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import ForgotPassword from './pages/ForgotPassword';

function App() {
  const PrivateRoute = ({ children, role }) => {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
      const handleScroll = () => setScrolled(window.scrollY > 10);
      window.addEventListener('scroll', handleScroll);
      return () => window.removeEventListener('scroll', handleScroll);
    }, []);
    
    if (!token) return <Navigate to="/" />;
    if (role && user.role !== role) return <Navigate to="/" />;
    
    const initials = user.full_name 
      ? user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() 
      : 'U';

    return (
      <>
        <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
          <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <a href="/" className="brand-logo">
              <div className="pulse-dot animate-pulse"></div>
              HABS
            </a>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div className="avatar">{initials}</div>
              <button 
                className="btn btn-ghost"
                onClick={() => {
                  localStorage.removeItem('token');
                  localStorage.removeItem('user');
                  window.location.href = '/';
                }}
              >
                Logout
              </button>
            </div>
          </div>
        </nav>
        {children}
      </>
    );
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/register" element={<Register />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route 
          path="/patient/dashboard" 
          element={
            <PrivateRoute role="patient">
              <PatientDashboard />
            </PrivateRoute>
          } 
        />
        <Route 
          path="/doctor/dashboard" 
          element={
            <PrivateRoute role="doctor">
              <DoctorDashboard />
            </PrivateRoute>
          } 
        />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
      </Routes>
    </Router>
  );
}

export default App;