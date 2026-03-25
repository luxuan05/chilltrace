import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Snowflake, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types";
import { useToast } from "@/hooks/use-toast";

const roles: { value: UserRole; label: string }[] = [
  { value: "buyer", label: "Buyer" },
  { value: "supplier", label: "Supplier" },
  { value: "driver", label: "Driver" },
];

const rolePortMap: Record<UserRole, string> = {
  buyer:    "http://localhost:5012",
  supplier: "http://localhost:5011",
  driver:   "http://localhost:5013",
};

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, role } = useAuth();
  const { toast } = useToast();
  const [selectedRole, setSelectedRole] = useState<UserRole>("buyer");
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
      const base = rolePortMap[selectedRole];
      const res = await fetch(`${base}/${selectedRole}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ Email: email, Password: password }),
      });

      const data = await res.json();
      console.log("1. Response status:", res.ok);
      console.log("2. Response data:", data);

      if (!res.ok) {
        toast({ title: data.error || "Login failed", variant: "destructive" });
        return;
      }

      console.log("3. Calling login...");
      login(data.user, selectedRole);
      console.log("4. Login called, isAuthenticated:", isAuthenticated);
      
      toast({ title: `Welcome! Logged in as ${selectedRole}` });
      
      console.log("5. About to navigate to:", `/${selectedRole}`);
      navigate(`/${selectedRole}`);
      console.log("6. Navigate called");
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
            {/* Role selector */}
            <div className="flex rounded-lg border border-border bg-muted p-1 gap-1">
              {roles.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setSelectedRole(value)}
                  className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    selectedRole === value
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

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
              {isLoading ? "Signing in..." : `Sign In as ${roles.find(r => r.value === selectedRole)?.label}`}
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
