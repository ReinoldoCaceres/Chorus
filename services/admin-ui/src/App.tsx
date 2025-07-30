import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AgentDashboard from './pages/AgentDashboard';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 3,
    },
  },
});

// Placeholder components for other routes
const Chats = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Chat Management</h2>
    <p className="text-gray-600 dark:text-gray-400">Chat management interface coming soon...</p>
  </div>
);

const Analytics = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Analytics</h2>
    <p className="text-gray-600 dark:text-gray-400">Analytics dashboard coming soon...</p>
  </div>
);

const Settings = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Settings</h2>
    <p className="text-gray-600 dark:text-gray-400">Settings panel coming soon...</p>
  </div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="agents" element={<AgentDashboard />} />
            <Route path="chats" element={<Chats />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
