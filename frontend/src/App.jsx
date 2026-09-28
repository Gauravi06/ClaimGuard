import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import ClaimForm from './components/ClaimForm';
import ClaimsTable from './components/ClaimsTable';
import ClaimDetail from './components/ClaimDetail';
import ModelPerformance from './components/ModelPerformance';
import Simulator from './components/Simulator';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/submit" element={<ClaimForm />} />
          <Route path="/claims" element={<ClaimsTable />} />
          <Route path="/claims/:id" element={<ClaimDetail />} />
          <Route path="/performance" element={<ModelPerformance />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
