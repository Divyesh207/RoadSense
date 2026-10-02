"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { CurrentUserData, UserProfile } from "@/types/api";
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

  // Resolves the active membership (saved choice if still valid, else the first)
  // from /auth/me and persists the organization used for X-Organization-ID.
  const loadProfile = async (preferredOrgId: string | null) => {
    const res = await api.auth.me();
    const me: CurrentUserData | null = res.data ?? null;
    if (!me) throw new Error("Empty profile response");
    const membership =
      me.organizations.find((m) => m.organization_id === preferredOrgId) ?? me.organizations[0];
    setUser({
      ...me,
      role: membership?.role_code ?? "",
      organization_id: membership?.organization_id,
      organization_name: membership?.organization_name,
    });
    if (membership) {
      setOrgId(membership.organization_id);
      localStorage.setItem("organization_id", membership.organization_id);
    } else {
      setOrgId(null);
      localStorage.removeItem("organization_id");
    }
  };

  useEffect(() => {
    // Check initial auth state from localStorage
    const savedToken = localStorage.getItem("access_token");
    const savedOrg = localStorage.getItem("organization_id");

    if (savedToken) {
      setToken(savedToken);
      loadProfile(savedOrg)
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
      if (!res.data?.access_token) throw new Error("Login response did not include a token");
      setToken(res.data.access_token);
      await loadProfile(localStorage.getItem("organization_id"));
    } catch (err) {
      localStorage.removeItem("access_token");
      setToken(null);
      setUser(null);
      throw err;
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
