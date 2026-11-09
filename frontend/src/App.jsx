import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { ChatPage } from './pages/ChatPage';
import { ResultsPage } from './pages/ResultsPage';
import { EvidencePage } from './pages/EvidencePage';
import { RecoveryPage } from './pages/RecoveryPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { FloatingChatbot } from './components/layout/FloatingChatbot';

function AppLayout() {
  return (
    <div className="min-h-screen bg-[#080d1a] text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-slate-950">
      <Navbar />
      {/* Global AI Chatbot */}
      <FloatingChatbot />
      <main className="flex-1">

        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/assessment" element={<AssessmentPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/recovery" element={<RecoveryPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </SessionProvider>
  );
}