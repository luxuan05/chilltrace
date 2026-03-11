import React from "react";
import { useNavigate } from "react-router-dom";
import { Snowflake, ShoppingCart, Warehouse, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroImage from "@/assets/hero-cold-chain.jpg";

const roles = [
  {
    key: "buyer" as const,
    label: "Buyer",
    icon: ShoppingCart,
    description: "Browse inventory, place orders, track deliveries",
    path: "/login/buyer",
  },
  {
    key: "supplier" as const,
    label: "Supplier",
    icon: Warehouse,
    description: "Manage inventory, view orders, handle stock",
    path: "/login/supplier",
  },
  {
    key: "driver" as const,
    label: "Driver",
    icon: Truck,
    description: "Pick up orders, update delivery status",
    path: "/login/driver",
  },
];

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <section className="relative h-[60vh] min-h-[420px] flex items-center justify-center overflow-hidden">
        <img
          src={heroImage}
          alt="Cold chain logistics"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-cold opacity-80" />
        <div className="relative z-10 text-center px-6 animate-fade-in">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Snowflake className="h-8 w-8 text-accent" />
            <span className="text-lg font-semibold tracking-widest uppercase text-accent">
              ChillTrace
            </span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold text-primary-foreground mb-4 tracking-tight">
            Cold Chain Logistics
          </h1>
          <p className="text-lg md:text-xl text-primary-foreground/80 max-w-2xl mx-auto">
            End-to-end temperature-controlled supply chain management. From supplier to doorstep.
          </p>
        </div>
      </section>

      {/* Role Selection */}
      <section className="flex-1 gradient-ice py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2 text-foreground">
            Sign in to your portal
          </h2>
          <p className="text-center text-muted-foreground mb-10">
            Select your role to continue
          </p>

          <div className="grid md:grid-cols-3 gap-6">
            {roles.map((role) => (
              <button
                key={role.key}
                onClick={() => navigate(role.path)}
                className="group bg-card border border-border rounded-lg p-8 text-left hover:border-accent hover:shadow-lg hover:shadow-accent/10 transition-all duration-300 animate-fade-in"
              >
                <div className="h-12 w-12 rounded-lg gradient-frost flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <role.icon className="h-6 w-6 text-accent-foreground" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  {role.label}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {role.description}
                </p>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default Index;
