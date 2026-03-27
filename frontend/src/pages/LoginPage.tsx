import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Snowflake, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types";
import { useToast } from "@/hooks/use-toast";

const rolePortMap: Record<UserRole, string> = {
  buyer:    "http://localhost:5012",
  supplier: "http://localhost:5011",
  driver:   "http://localhost:5013",
};

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, role } = useAuth();
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated && role) {
      navigate(`/${role}`, { replace: true });
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast({ title: "Please fill in all fields", variant: "destructive" });
      return;
    }

    setIsLoading(true);
    try {
      // Try each role until one succeeds
      for (const [roleKey, base] of Object.entries(rolePortMap) as [UserRole, string][]) {
        const res = await fetch(`${base}/${roleKey}/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ Email: email, Password: password }),
        });

        if (res.ok) {
          const data = await res.json();
          login(data.user, roleKey);
          toast({ title: `Welcome! Logged in as ${roleKey}` });
          navigate(`/${roleKey}`);
          return;
        }
      }

      // None succeeded
      toast({ title: "Invalid email or password", variant: "destructive" });
    } catch (err) {
      console.error("ERROR:", err);
      toast({ title: "Could not connect to server", variant: "destructive" });
    } finally {
      setIsLoading(false);
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
            <span className="font-semibold text-foreground">ChillTrace</span>
          </div>

          <h1 className="text-2xl font-bold text-foreground mb-1">Sign In</h1>
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
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full gradient-frost text-accent-foreground hover:opacity-90"
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-4 text-center">
            Don't have an account?{" "}
            <button
              onClick={() => navigate("/register")}
              className="text-accent hover:underline font-medium"
            >
              Register
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
