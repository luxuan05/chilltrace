import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { UserRole } from "@/types";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  ID: number;
  Email?: string;
  CompanyName?: string;
  Name?: string;
  Phone?: string;
  Address?: string;
  ChatID?: string;
  VehicleNo?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (user: AuthUser, role: UserRole) => void;
  logout: () => void;
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);

  // Restore session on page refresh
  useEffect(() => {
    const storedUser = localStorage.getItem("auth_user");
    const storedRole = localStorage.getItem("auth_role");
    if (storedUser && storedRole) {
      setUser(JSON.parse(storedUser));
      setRole(storedRole as UserRole);
    }
  }, []);

  const login = (userData: AuthUser, userRole: UserRole) => {
    setUser(userData);
    setRole(userRole);
    localStorage.setItem("auth_user", JSON.stringify(userData));
    localStorage.setItem("auth_role", userRole);
  };

  const logout = () => {
    setUser(null);
    setRole(null);
    localStorage.removeItem("auth_user");
    localStorage.removeItem("auth_role");
  };

  return (
    <AuthContext.Provider value={{ user, role, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
