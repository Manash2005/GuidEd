import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import * as AuthContextModule from '../context/AuthContext';

function renderWithRouter(ui, initialRoute = '/test') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/test" element={ui} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/student" element={<div>Student Dashboard Page</div>} />
        <Route path="/mentor" element={<div>Mentor Dashboard Page</div>} />
        <Route path="/admin" element={<div>Admin Dashboard Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('Frontend Route Guards (ProtectedRoute)', () => {
  it('redirects unauthenticated user to login', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      logout: vi.fn()
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['student']}>
        <div>Secret Student Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Login Page')).toBeTruthy();
    expect(screen.queryByText('Secret Student Content')).toBeNull();
  });

  it('allows student to access student-allowed route', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { userId: 'u1', role: 'student', status: 'active' },
      isAuthenticated: true,
      isLoading: false,
      logout: vi.fn()
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['student']}>
        <div>Authorized Student Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Authorized Student Content')).toBeTruthy();
  });

  it('blocks student from accessing admin route and shows Access Denied', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { userId: 'u1', role: 'student', status: 'active' },
      isAuthenticated: true,
      isLoading: false,
      logout: vi.fn()
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['admin']}>
        <div>Admin Top Secret Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Access Denied')).toBeTruthy();
    expect(screen.queryByText('Admin Top Secret Content')).toBeNull();
    expect(screen.getByText('Go to My Dashboard')).toBeTruthy();
  });

  it('blocks mentor from accessing admin route', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { userId: 'u2', role: 'mentor', status: 'active' },
      isAuthenticated: true,
      isLoading: false,
      logout: vi.fn()
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['admin']}>
        <div>Admin Only Zone</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Access Denied')).toBeTruthy();
    expect(screen.queryByText('Admin Only Zone')).toBeNull();
  });

  it('blocks suspended user regardless of role', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { userId: 'u3', role: 'student', status: 'suspended' },
      isAuthenticated: true,
      isLoading: false,
      logout: vi.fn()
    });

    renderWithRouter(
      <ProtectedRoute allowedRoles={['student']}>
        <div>Student Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Account suspended')).toBeTruthy();
    expect(screen.queryByText('Student Content')).toBeNull();
  });
});
