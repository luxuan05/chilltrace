import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { AppDataProvider } from "@/context/AppDataContext";
import Index from "./pages/Index";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import BuyerDashboard from "./pages/BuyerDashboard";
import SupplierDashboard from "./pages/SupplierDashboard";
import DriverDashboard from "./pages/DriverDashboard";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <AuthProvider>
        <AppDataProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
              <Routes>
                <Route path="/" element={<Index />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/buyer/*" element={<BuyerDashboard />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/supplier/*" element={<SupplierDashboard />} />
                <Route path="/driver/*" element={<DriverDashboard />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
          </TooltipProvider>
        </AppDataProvider>
      </AuthProvider>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;
