import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  Truck,
  ClipboardList,
  MapPin,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { OrderStatus } from "@/types";
import StatusBadge from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

/* ─── Available Orders ─── */
const AvailableOrders = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();

  const available = orders.filter(
    (o) => (o.status === "confirmed" || o.status === "processing") && !o.driverId
  );

  const acceptOrder = (id: string) => {
    setOrders((prev) =>
      prev.map((o) =>
        o.id === id
          ? {
              ...o,
              driverId: user!.id,
              driverName: user!.name,
              status: "processing" as const,
              updatedAt: new Date().toISOString(),
            }
          : o
      )
    );
    toast({ title: `Order ${id} accepted for delivery` });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">Available Orders</h1>
      <div className="grid gap-4">
        {available.map((order) => (
          <Card key={order.id}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-foreground">{order.id}</span>
                    <StatusBadge status={order.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {order.items.map((i) => `${i.name} ×${i.qty}`).join(", ")}
                  </p>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <MapPin className="h-3.5 w-3.5" />
                    {order.deliveryAddress}
                  </div>
                  <p className="text-sm text-muted-foreground">Delivery: {order.deliveryDate}</p>
                </div>
                <Button onClick={() => acceptOrder(order.id)} className="gradient-frost text-accent-foreground hover:opacity-90">
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
    </div>
  );
};

/* ─── My Deliveries ─── */
const MyDeliveries = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();

  const myDeliveries = orders.filter((o) => o.driverId === user?.id);

  const statusFlow: OrderStatus[] = ["processing", "in_transit", "delivered"];

  const updateStatus = (id: string, newStatus: OrderStatus) => {
    setOrders((prev) =>
      prev.map((o) =>
        o.id === id ? { ...o, status: newStatus, updatedAt: new Date().toISOString() } : o
      )
    );
    toast({ title: `Order ${id} updated to ${newStatus.replace("_", " ")}` });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">My Deliveries</h1>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order ID</TableHead>
                <TableHead>Buyer</TableHead>
                <TableHead>Address</TableHead>
                <TableHead>Delivery Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Update</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {myDeliveries.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-medium">{order.id}</TableCell>
                  <TableCell>{order.buyerName}</TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                    {order.deliveryAddress}
                  </TableCell>
                  <TableCell>{order.deliveryDate}</TableCell>
                  <TableCell><StatusBadge status={order.status} /></TableCell>
                  <TableCell className="text-right">
                    {order.status !== "delivered" && order.status !== "cancelled" && (
                      <Select onValueChange={(v) => updateStatus(order.id, v as OrderStatus)}>
                        <SelectTrigger className="w-[140px]">
                          <SelectValue placeholder="Update..." />
                        </SelectTrigger>
                        <SelectContent>
                          {statusFlow
                            .filter((s) => statusFlow.indexOf(s) > statusFlow.indexOf(order.status as any))
                            .map((s) => (
                              <SelectItem key={s} value={s}>
                                {s.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {myDeliveries.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    No deliveries assigned yet
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

/* ─── Driver Dashboard ─── */
const DriverDashboard = () => {
  const { user, role } = useAuth();
  if (!user || role !== "driver") return <Navigate to="/login/driver" />;

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
