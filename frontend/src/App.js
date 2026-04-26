import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { LanguageProvider } from '@/contexts/LanguageContext';
import LandingPage from '@/pages/LandingPage';
import AuthPage from '@/pages/AuthPage';
import VoiceSelect from '@/pages/VoiceSelect';
import ChatPage from '@/pages/ChatPage';
import TariffPage from '@/pages/TariffPage';
import PaymentSuccess from '@/pages/PaymentSuccess';
import SpecialistsPage from '@/pages/SpecialistsPage';
import AboutPage from '@/pages/AboutPage';
import ProfilePage from '@/pages/ProfilePage';
import MiroRadio from '@/pages/MiroRadio';
import BookingCalendar from '@/pages/BookingCalendar';
import MagicVerify from '@/pages/MagicVerify';
import InstallPrompt from '@/components/InstallPrompt';
import '@/App.css';

function WaitForAuth({ children }) {
  const { loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="loading-spinner" /></div>;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<WaitForAuth><LandingPage /></WaitForAuth>} />
      <Route path="/auth" element={<WaitForAuth><AuthPage /></WaitForAuth>} />
      <Route path="/voice-select" element={<WaitForAuth><VoiceSelect /></WaitForAuth>} />
      <Route path="/chat" element={<WaitForAuth><ChatPage /></WaitForAuth>} />
      <Route path="/tariffs" element={<WaitForAuth><TariffPage /></WaitForAuth>} />
      <Route path="/payment-success" element={<WaitForAuth><PaymentSuccess /></WaitForAuth>} />
      <Route path="/specialists" element={<WaitForAuth><SpecialistsPage /></WaitForAuth>} />
      <Route path="/about" element={<WaitForAuth><AboutPage /></WaitForAuth>} />
      <Route path="/profile" element={<WaitForAuth><ProfilePage /></WaitForAuth>} />
      <Route path="/radio" element={<WaitForAuth><MiroRadio /></WaitForAuth>} />
      <Route path="/booking" element={<WaitForAuth><BookingCalendar /></WaitForAuth>} />
      <Route path="/magic/:token" element={<MagicVerify />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <BrowserRouter>
            <div className="app-root" data-testid="app-root">
              <AppRoutes />
              <InstallPrompt />
            </div>
          </BrowserRouter>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
