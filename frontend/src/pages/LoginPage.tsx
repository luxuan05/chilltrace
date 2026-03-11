import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Snowflake, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types";
import { useToast } from "@/hooks/use-toast";

const roleTitles: Record<string, string> = {
  buyer: "Buyer Portal",
  supplier: "Supplier Portal",
  driver: "Driver Portal",
};

const LoginPage = () => {
  const { role } = useParams<{ role: string }>();
  const navigate = useNavigate();
  const { login } = useAuth();
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const validRole = (role as UserRole) || "buyer";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast({ title: "Please fill in all fields", variant: "destructive" });
      return;
    }
    const success = login(email, password, validRole);
    if (success) {
      toast({ title: `Welcome! Logged in as ${validRole}` });
      navigate(`/${validRole}`);
    } else {
      toast({ title: "Login failed", variant: "destructive" });
    }
  };

  return (
    <div className="min-h-screen gradient-ice flex items-center justify-center px-6">
      <div className="w-full max-w-md animate-fade-in">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground mb-8 text-sm transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to home
        </button>

        <div className="bg-card border border-border rounded-xl p-8 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <Snowflake className="h-6 w-6 text-accent" />
            <span className="font-semibold text-foreground">FrostChain</span>
          </div>

          <h1 className="text-2xl font-bold text-foreground mb-1">
            {roleTitles[validRole] || "Login"}
          </h1>
          <p className="text-sm text-muted-foreground mb-6">
            Enter your credentials to continue
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1"
              />
            </div>
            <Button type="submit" className="w-full gradient-frost text-accent-foreground hover:opacity-90">
              Sign In
            </Button>
          </form>

          <p className="text-xs text-muted-foreground mt-4 text-center">
            Demo: any email &amp; password will work
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
