import { useState, useEffect, useCallback } from 'react';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
}

const TOKEN_KEY = 'admin_token';

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    return { token, isAuthenticated: !!token };
  });

  const login = useCallback((token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    setAuth({ token, isAuthenticated: true });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAuth({ token: null, isAuthenticated: false });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    setAuth({ token, isAuthenticated: !!token });
  }, []);

  return { ...auth, login, logout };
}
