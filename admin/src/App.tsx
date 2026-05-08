import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import ClientList from './pages/ClientList';
import ClientDetail from './pages/ClientDetail';
import ClientCreate from './pages/ClientCreate';
import Analytics from './pages/Analytics';

function AdminApp() {
  return (
    <Layout>
      <Routes>
        <Route path="/clients" element={<ClientList />} />
        <Route path="/clients/new" element={<ClientCreate />} />
        <Route path="/clients/:client_id" element={<ClientDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="*" element={<Navigate to="/clients" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AdminApp />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
