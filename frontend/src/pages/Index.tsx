import React from "react";
import { useNavigate } from "react-router-dom";
import { Snowflake, ShoppingCart, Warehouse, Truck, ArrowRight, ThermometerSnowflake, MapPin, BarChart2 } from "lucide-react";
import heroImage from "@/assets/hero-cold-chain.jpg";

const roles = [
  {
    key: "buyer" as const,
    label: "Buyer",
    icon: ShoppingCart,
    description: "Browse inventory, place orders, track deliveries in real time.",
  },
  {
    key: "supplier" as const,
    label: "Supplier",
    icon: Warehouse,
    description: "Manage your inventory, view incoming orders, handle stock levels.",
  },
  {
    key: "driver" as const,
    label: "Driver",
    icon: Truck,
    description: "Pick up orders, update delivery status, navigate routes.",
  },
];

const features = [
  {
    icon: ThermometerSnowflake,
    title: "Temperature Monitoring",
    description: "Real-time cold chain tracking ensuring product integrity from source to destination.",
  },
  {
    icon: MapPin,
    title: "Live Tracking",
    description: "End-to-end visibility of every shipment with GPS-powered delivery updates.",
  },
  {
    icon: BarChart2,
    title: "Analytics & Reports",
    description: "Actionable insights on orders, deliveries, and supply chain performance.",
  },
];

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-background">

      {/* ── Navbar ── */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-8 py-5">
        <div className="flex items-center gap-2">
          <Snowflake className="h-6 w-6 text-accent" />
          <span className="font-bold text-lg text-white tracking-tight">ChillTrace</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className="px-4 py-2 text-sm font-semibold text-white/90 hover:text-white transition"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate("/register")}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-white/15 hover:bg-white/25 text-white border border-white/20 transition backdrop-blur-sm"
          >
            Register
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative h-[65vh] min-h-[480px] flex items-center justify-center overflow-hidden">
        <img
          src={heroImage}
          alt="Cold chain logistics"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-slate-900/70 via-slate-900/50 to-background" />

        <div className="relative z-10 text-center px-6 animate-fade-in max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 backdrop-blur-sm px-4 py-1.5 mb-6">
            <Snowflake className="h-4 w-4 text-accent" />
            <span className="text-xs font-semibold uppercase tracking-widest text-white/90">
              Cold Chain Management
            </span>
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold text-white mb-5 tracking-tight leading-tight">
            Your Cold Chain,<br />
            <span className="text-accent">Fully Traced.</span>
          </h1>
          <p className="text-base md:text-lg text-white/75 max-w-xl mx-auto mb-8">
            End-to-end temperature-controlled supply chain management — from supplier warehouse to your doorstep.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={() => navigate("/login")}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3 rounded-xl bg-accent text-accent-foreground font-semibold text-sm hover:opacity-90 transition shadow-lg shadow-accent/30"
            >
              Get Started <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => navigate("/register")}
              className="w-full sm:w-auto px-7 py-3 rounded-xl border border-white/25 bg-white/10 backdrop-blur-sm text-white font-semibold text-sm hover:bg-white/20 transition"
            >
              Create Account
            </button>
          </div>
        </div>
      </section>

      {/* ── Roles ── */}
      <section className="py-10 px-6 gradient-ice border-t border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center text-foreground mb-2">
            Built for every role
          </h2>
          <p className="text-center text-muted-foreground mb-10 text-sm">
            One platform, tailored experiences for buyers, suppliers, and drivers.
          </p>

          <div className="grid md:grid-cols-3 gap-6 mb-10">
            {roles.map(({ key, label, icon: Icon, description }) => (
              <div
                key={key}
                className="group bg-card border border-border rounded-2xl p-6 hover:border-accent/50 hover:shadow-lg hover:shadow-accent/5 transition-all duration-300"
              >
                <div className="h-11 w-11 rounded-xl gradient-frost flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Icon className="h-5 w-5 text-accent-foreground" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-1.5">{label}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-6 px-8 border-t border-border bg-background flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Snowflake className="h-4 w-4 text-accent" />
          <span className="text-sm font-semibold text-foreground">ChillTrace</span>
        </div>
        <p className="text-xs text-muted-foreground">© 2025 ChillTrace. All rights reserved.</p>
      </footer>

    </div>
  );
};

export default Index;
