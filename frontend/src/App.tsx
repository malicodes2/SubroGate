import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { LandingHero } from './components/LandingHero';
import { CaseView } from './components/CaseView';
import { FleetCatalog } from './components/FleetCatalog';
import { NewInvestigationModal } from './components/NewInvestigationModal';
import { apiClient } from './api/client';
import { HealthResponse } from './types';

export function App() {
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Mobile Sidebar Drawer State
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

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
    <div className="min-h-screen text-slate-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white bg-slate-50">
      
      {/* Top Navigation */}
      <Navbar
        modelInfo={healthData?.model}
        isConnected={!error && healthData !== null}
        onRefresh={initApp}
        onNewInvestigation={() => setIsNewModalOpen(true)}
        onMenuClick={() => setSidebarOpen(true)}
        isLoading={isLoading}
        isLiveMode={isLiveAuth}
      />

      {/* Main Layout Area with Mobile Drawer Support */}
      <div className="flex-1 flex overflow-hidden relative">
        
        {/* Mobile Backdrop Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs md:hidden animate-fade-in"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar overlay"
          />
        )}

        {/* Sidebar Drawer Container */}
        <div className={`
          fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 ease-in-out md:static md:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <Sidebar 
            onNewInvestigation={() => {
              setSidebarOpen(false);
              setIsNewModalOpen(true);
            }}
            onNavigate={() => setSidebarOpen(false)}
            refreshTrigger={refreshSidebar} 
          />
        </div>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto w-full px-4 sm:px-6 py-6 custom-scrollbar relative">
          <Routes>
            <Route path="/" element={
              <div className="max-w-7xl mx-auto mt-6 sm:mt-10">
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
            <Route path="/catalog" element={
              <div className="max-w-7xl mx-auto">
                <FleetCatalog />
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
