import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { LandingHero } from './components/LandingHero';
import { CaseView } from './components/CaseView';
import { NewInvestigationModal } from './components/NewInvestigationModal';
import { apiClient } from './api/client';
import { HealthResponse } from './types';

export function App() {
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // New Investigation Wizard Modal
  const [isNewModalOpen, setIsNewModalOpen] = useState<boolean>(false);
  const [refreshSidebar, setRefreshSidebar] = useState<number>(0);

  const navigate = useNavigate();

  // Initial Load - Check live system health
  const initApp = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const health = await apiClient.checkHealth().catch(() => null);
      if (health) setHealthData(health);
    } catch (err: any) {
      console.warn('Initial system health check notice:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initApp();
  }, []);

  const isLiveAuth = Boolean(healthData?.model?.auth_configured);

  const triggerSidebarRefresh = () => {
    setRefreshSidebar(prev => prev + 1);
  };

  return (
    <div className="min-h-screen text-slate-900 flex font-sans selection:bg-blue-600 selection:text-white">
      {/* Sidebar for persistent case history */}
      <Sidebar 
        onNewInvestigation={() => setIsNewModalOpen(true)} 
        refreshTrigger={refreshSidebar} 
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden bg-slate-50">
        <Navbar
          modelInfo={healthData?.model}
          isConnected={!error && healthData !== null}
          onRefresh={initApp}
          onNewInvestigation={() => setIsNewModalOpen(true)}
          isLoading={isLoading}
          isLiveMode={isLiveAuth}
        />

        <main className="flex-1 overflow-y-auto w-full px-4 sm:px-6 py-6 custom-scrollbar">
          <Routes>
            <Route path="/" element={
              <div className="max-w-7xl mx-auto mt-12">
                <LandingHero
                  onStartNew={() => setIsNewModalOpen(true)}
                  isLoading={isLoading}
                />
              </div>
            } />
            <Route path="/cases/:caseId" element={
              <div className="max-w-7xl mx-auto">
                <CaseView onCaseUpdated={triggerSidebarRefresh} />
              </div>
            } />
          </Routes>
        </main>
      </div>

      {/* New Investigation Wizard Modal with key to force reset on open */}
      {isNewModalOpen && (
        <NewInvestigationModal
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          onCaseCreated={(created) => {
            triggerSidebarRefresh();
            navigate(`/cases/${created.case_id}`);
          }}
          isLiveMode={isLiveAuth}
        />
      )}
    </div>
  );
}

export default App;
