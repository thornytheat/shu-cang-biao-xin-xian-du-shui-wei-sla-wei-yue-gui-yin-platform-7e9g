import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { Board } from '../pages/Board';
import { Breaches } from '../pages/Breaches';
import { Login } from '../pages/Login';
import { Policies } from '../pages/Policies';
import { TableDetail } from '../pages/TableDetail';
import { RequireAuth } from './guards';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/board" element={<Board />} />
          <Route path="/tables/:code" element={<TableDetail />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/breaches" element={<Breaches />} />
        </Route>
        <Route path="/" element={<Navigate to="/board" replace />} />
        <Route path="*" element={<Navigate to="/board" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
