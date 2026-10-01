"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserProfile } from "@/types/api";
import { api } from "@/lib/api-client";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  organizationId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setOrganizationId: (orgId: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [organizationId, setOrgId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check initial auth state from localStorage
    const savedToken = localStorage.getItem("access_token");
    const savedOrg = localStorage.getItem("organization_id");

    if (savedToken) {
      setToken(savedToken);
      if (savedOrg) {
        setOrgId(savedOrg);
      }
      // Load current user profile from /auth/me
      api.auth
        .me()
        .then((res) => {
          if (res.data) {
            setUser(res.data);
            if (res.data.organization_id && !savedOrg) {
              setOrgId(res.data.organization_id);
              localStorage.setItem("organization_id", res.data.organization_id);
            }
          }
        })
        .catch(() => {
          // If token invalid, clear
          localStorage.removeItem("access_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.auth.login(email, password);
      if (res.data) {
        setToken(res.data.access_token);
        setUser(res.data.user);
        if (res.data.user.organization_id) {
          setOrgId(res.data.user.organization_id);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.auth.logout();
    setToken(null);
    setUser(null);
    setOrgId(null);
  };

  const setOrganizationId = (orgId: string) => {
    setOrgId(orgId);
    localStorage.setItem("organization_id", orgId);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        organizationId,
        isAuthenticated: !!token,
        isLoading,
        login,
        logout,
        setOrganizationId,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
