import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  Truck,
  ClipboardList,
  MapPin,
  Thermometer,
  AlertTriangle,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

const navItems = [
  { label: "Available Orders", path: "/driver", icon: <ClipboardList className="h-4 w-4" /> },
  { label: "My Deliveries", path: "/driver/deliveries", icon: <Truck className="h-4 w-4" /> },
];

interface BackendOrder {
  ID: number;
  CustomerID: number;
  SupplierId: number;
  OrderStatus: string;
  TotalPrice: number;
  ScheduledDate: string | null;
  DriverID: number | null;
  OrderItems: {
    ID: number;
    OrderID: number;
    ItemID: number;
    Quantity: number;
    UnitPrice: number;
  }[];
}

/* ─── Available Orders ─── */
const AvailableOrders = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [orders, setOrders] = useState<BackendOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOrders = async () => {
    try {
      const res = await fetch("http://localhost:5002/orders");
      const data = await res.json();
      setOrders(Array.isArray(data) ? data : []);
    } catch {
      toast({ title: "Failed to load orders", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const available = orders.filter(
    (o) =>
      (o.OrderStatus === "RECEIVED" ||
        o.OrderStatus === "PAID" ||
        o.OrderStatus === "SCHEDULED") &&
      !o.DriverID
  );

  const acceptOrder = async (id: number) => {
    try {
      const res = await fetch(`http://localhost:5002/orders/${id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ OrderStatus: "IN_TRANSIT", DriverID: user!.ID }),
      });
      if (!res.ok) throw new Error();
      toast({ title: `Order #${id} accepted for delivery` });
      await fetchOrders();
    } catch {
      toast({ title: "Failed to accept order", variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">Available Orders</h1>
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading orders...</p>
      ) : (
        <div className="grid gap-4">
          {available.map((order) => (
            <Card key={order.ID}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-foreground">Order #{order.ID}</span>
                      <span className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground">
                        {order.OrderStatus}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {order.OrderItems.length} item(s) · Total: ${order.TotalPrice.toFixed(2)}
                    </p>
                    {order.ScheduledDate && (
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5" />
                        Delivery: {order.ScheduledDate}
                      </div>
                    )}
                    <p className="text-sm text-muted-foreground">
                      Supplier ID: {order.SupplierId} · Customer ID: {order.CustomerID}
                    </p>
                  </div>
                  <Button
                    onClick={() => acceptOrder(order.ID)}
                    className="gradient-frost text-accent-foreground hover:opacity-90"
                  >
                    Accept
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {available.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                No available orders at the moment
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

/* ─── Temperature Cell ─── */
const TemperatureCell = ({
  order,
  onBreach,
}: {
  order: BackendOrder;
  onBreach: (id: number, temp: string) => void;
}) => {
  const [temp, setTemp] = useState("");

  const isActive =
    order.OrderStatus !== "DELIVERED" &&
    order.OrderStatus !== "CANCELLED" &&
    order.OrderStatus !== "FAILED_TEMP_BREACH";

  if (!isActive) return <span className="text-xs text-muted-foreground">—</span>;

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <Thermometer className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          type="number"
          placeholder="°C"
          value={temp}
          onChange={(e) => setTemp(e.target.value)}
          className="pl-7 w-24 h-8 text-sm"
        />
      </div>
      <Button
        size="sm"
        variant="destructive"
        className="h-8 text-xs gap-1"
        disabled={!temp}
        onClick={() => onBreach(order.ID, temp)}
      >
        <AlertTriangle className="h-3.5 w-3.5" />
        Breach
      </Button>
    </div>
  );
};

/* ─── My Deliveries ─── */
const MyDeliveries = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [orders, setOrders] = useState<BackendOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOrders = async () => {
    try {
      const res = await fetch("http://localhost:5002/orders");
      const data = await res.json();
      const arr = Array.isArray(data) ? data : [];
      setOrders(arr.filter((o: BackendOrder) => o.DriverID === user?.ID));
    } catch {
      toast({ title: "Failed to load deliveries", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  // Full status flow drivers can move through
  const statusFlow = ["SCHEDULED", "IN_TRANSIT", "DELIVERED", "CANCELLED"];

  const updateStatus = async (id: number, newStatus: string) => {
    try {
      const res = await fetch(`http://localhost:5002/orders/${id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ OrderStatus: newStatus }),
      });
      if (!res.ok) throw new Error();
      toast({ title: `Order #${id} updated to ${newStatus.replace(/_/g, " ")}` });
      await fetchOrders();
    } catch {
      toast({ title: "Failed to update status", variant: "destructive" });
    }
  };

  const reportBreach = async (id: number, temperature: string) => {
    try {
      const res = await fetch(`http://localhost:5002/orders/${id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ OrderStatus: "FAILED_TEMP_BREACH" }),
      });
      if (!res.ok) throw new Error();
      toast({
        title: `⚠️ Temperature breach reported for Order #${id}`,
        description: `Recorded temperature: ${temperature}°C`,
        variant: "destructive",
      });
      await fetchOrders();
    } catch {
      toast({ title: "Failed to report breach", variant: "destructive" });
    }
  };

  const isFinal = (status: string) =>
    status === "DELIVERED" || status === "CANCELLED" || status === "FAILED_TEMP_BREACH";

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "DELIVERED": return "bg-green-100 text-green-700";
      case "CANCELLED": return "bg-red-100 text-red-700";
      case "FAILED_TEMP_BREACH": return "bg-orange-100 text-orange-700";
      case "IN_TRANSIT": return "bg-blue-100 text-blue-700";
      case "SCHEDULED": return "bg-purple-100 text-purple-700";
      default: return "bg-muted text-muted-foreground";
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">My Deliveries</h1>
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="text-sm text-muted-foreground p-6">Loading deliveries...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Scheduled Date</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Temperature</TableHead>
                  <TableHead className="text-right">Update Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.ID}>
                    <TableCell className="font-medium">#{order.ID}</TableCell>
                    <TableCell>{order.CustomerID}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {order.OrderItems.length} item(s)
                    </TableCell>
                    <TableCell>{order.ScheduledDate || "—"}</TableCell>
                    <TableCell>${order.TotalPrice.toFixed(2)}</TableCell>
                    <TableCell>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getStatusBadgeClass(order.OrderStatus)}`}>
                        {order.OrderStatus.replace(/_/g, " ")}
                      </span>
                    </TableCell>
                    <TableCell>
                      <TemperatureCell order={order} onBreach={reportBreach} />
                    </TableCell>
                    <TableCell className="text-right">
                      {!isFinal(order.OrderStatus) && (
                        <Select onValueChange={(v) => updateStatus(order.ID, v)}>
                          <SelectTrigger className="w-[150px]">
                            <SelectValue placeholder="Update..." />
                          </SelectTrigger>
                          <SelectContent>
                            {statusFlow
                              .filter(
                                (s) =>
                                  statusFlow.indexOf(s) > statusFlow.indexOf(order.OrderStatus)
                              )
                              .map((s) => (
                                <SelectItem key={s} value={s}>
                                  {s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {orders.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      No deliveries assigned yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

/* ─── Driver Dashboard ─── */
const DriverDashboard = () => {
  const { user, role } = useAuth();
  if (!user || role !== "driver") return <Navigate to="/login" />;

  return (
    <DashboardLayout navItems={navItems} title="Driver Portal">
      <Routes>
        <Route index element={<AvailableOrders />} />
        <Route path="deliveries" element={<MyDeliveries />} />
      </Routes>
    </DashboardLayout>
  );
};

export default DriverDashboard;
