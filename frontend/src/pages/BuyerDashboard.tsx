import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  ShoppingCart,
  ClipboardList,
  Package,
  Plus,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { Order, OrderItem } from "@/types";
import StatusBadge from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";

const navItems = [
  { label: "Place Order", path: "/buyer", icon: <Plus className="h-4 w-4" /> },
  { label: "Order History", path: "/buyer/orders", icon: <ClipboardList className="h-4 w-4" /> },
];

/* ─── Place Order ─── */
const PlaceOrder = () => {
  const { inventory, orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();
  const [cart, setCart] = useState<Record<string, number>>({});
  const [address, setAddress] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [payment, setPayment] = useState("Bank Transfer");

  const addToCart = (id: string) => {
    setCart((c) => ({ ...c, [id]: (c[id] || 0) + 1 }));
  };

  const updateQty = (id: string, qty: number) => {
    if (qty <= 0) {
      const next = { ...cart };
      delete next[id];
      setCart(next);
    } else {
      setCart((c) => ({ ...c, [id]: qty }));
    }
  };

  const cartItems = Object.entries(cart)
    .map(([id, qty]) => {
      const item = inventory.find((i) => i.id === id);
      return item ? { ...item, qty } : null;
    })
    .filter(Boolean) as (typeof inventory[number] & { qty: number })[];

  const total = cartItems.reduce((s, i) => s + i.qty * i.pricePerUnit, 0);

  const placeOrder = () => {
    if (!cartItems.length || !address || !deliveryDate) {
      toast({ title: "Please fill all order details", variant: "destructive" });
      return;
    }
    const orderItems: OrderItem[] = cartItems.map((i) => ({
      inventoryId: i.id,
      name: i.name,
      qty: i.qty,
      unit: i.unit,
      pricePerUnit: i.pricePerUnit,
    }));
    const newOrder: Order = {
      id: `ORD-${String(orders.length + 1).padStart(3, "0")}`,
      buyerId: user!.id,
      buyerName: user!.name,
      supplierId: cartItems[0].supplierId,
      supplierName: cartItems[0].supplierName,
      items: orderItems,
      totalAmount: total,
      deliveryAddress: address,
      deliveryDate,
      status: "pending",
      paymentMethod: payment,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setOrders((prev) => [...prev, newOrder]);
    setCart({});
    setAddress("");
    setDeliveryDate("");
    toast({ title: `Order ${newOrder.id} placed successfully!` });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">Place New Order</h1>

      {/* Inventory */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Package className="h-5 w-5 text-accent" /> Available Inventory
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Temp Range</TableHead>
                <TableHead>Stock</TableHead>
                <TableHead>Price/Unit</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inventory.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell>{item.category}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {item.minTemp}°C to {item.maxTemp}°C
                  </TableCell>
                  <TableCell>{item.stockLevel} {item.unit}</TableCell>
                  <TableCell>${item.pricePerUnit.toFixed(2)}/{item.unit}</TableCell>
                  <TableCell className="text-right">
                    {cart[item.id] ? (
                      <div className="flex items-center justify-end gap-2">
                        <Button size="sm" variant="outline" onClick={() => updateQty(item.id, cart[item.id] - 1)}>−</Button>
                        <span className="w-8 text-center text-sm font-medium">{cart[item.id]}</span>
                        <Button size="sm" variant="outline" onClick={() => updateQty(item.id, cart[item.id] + 1)}>+</Button>
                      </div>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => addToCart(item.id)}>
                        Add
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Cart / Order Details */}
      {cartItems.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShoppingCart className="h-5 w-5 text-accent" /> Order Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted rounded-lg p-4 space-y-2">
              {cartItems.map((item) => (
                <div key={item.id} className="flex justify-between text-sm">
                  <span>{item.name} × {item.qty} {item.unit}</span>
                  <span className="font-medium">${(item.qty * item.pricePerUnit).toFixed(2)}</span>
                </div>
              ))}
              <div className="border-t border-border pt-2 flex justify-between font-bold">
                <span>Total</span>
                <span>${total.toFixed(2)}</span>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Delivery Address</Label>
                <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Full delivery address" className="mt-1" />
              </div>
              <div>
                <Label>Delivery Date</Label>
                <Input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} className="mt-1" />
              </div>
              <div>
                <Label>Payment Method</Label>
                <select
                  value={payment}
                  onChange={(e) => setPayment(e.target.value)}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option>Bank Transfer</option>
                  <option>Credit Card</option>
                  <option>Net 30</option>
                </select>
              </div>
            </div>

            <Button onClick={placeOrder} className="gradient-frost text-accent-foreground hover:opacity-90">
              Place Order — ${total.toFixed(2)}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

/* ─── Order History ─── */
const OrderHistory = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();
  const myOrders = orders.filter((o) => o.buyerId === user?.id);

  const canCancel = (order: Order) => {
    if (order.status === "cancelled" || order.status === "delivered") return false;
    const delivery = new Date(order.deliveryDate);
    const now = new Date();
    const hoursUntilDelivery = (delivery.getTime() - now.getTime()) / (1000 * 60 * 60);
    return hoursUntilDelivery > 24;
  };

  const cancelOrder = (id: string) => {
    setOrders((prev) =>
      prev.map((o) =>
        o.id === id ? { ...o, status: "cancelled" as const, updatedAt: new Date().toISOString() } : o
      )
    );
    toast({ title: `Order ${id} cancelled` });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">Order History</h1>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order ID</TableHead>
                <TableHead>Items</TableHead>
                <TableHead>Delivery Date</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {myOrders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-medium">{order.id}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {order.items.map((i) => i.name).join(", ")}
                  </TableCell>
                  <TableCell>{order.deliveryDate}</TableCell>
                  <TableCell>${order.totalAmount.toFixed(2)}</TableCell>
                  <TableCell><StatusBadge status={order.status} /></TableCell>
                  <TableCell className="text-right">
                    {canCancel(order) && (
                      <Button size="sm" variant="destructive" onClick={() => cancelOrder(order.id)}>
                        Cancel
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {myOrders.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    No orders yet
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

/* ─── Buyer Dashboard (Router) ─── */
const BuyerDashboard = () => {
  const { user } = useAuth();
  if (!user || user.role !== "buyer") return <Navigate to="/login/buyer" />;

  return (
    <DashboardLayout navItems={navItems} title="Buyer Portal">
      <Routes>
        <Route index element={<PlaceOrder />} />
        <Route path="orders" element={<OrderHistory />} />
      </Routes>
    </DashboardLayout>
  );
};

export default BuyerDashboard;
