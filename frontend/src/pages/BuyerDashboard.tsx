import React, { useState, useEffect } from "react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

const navItems = [
  { label: "Place Order", path: "/buyer", icon: <Plus className="h-4 w-4" /> },
  { label: "Order History", path: "/buyer/orders", icon: <ClipboardList className="h-4 w-4" /> },
];

interface Supplier {
  ID: number;
  CompanyName: string;
  Email: string;
  Phone: string;
  Address: string;
}

interface RawInventoryItem {
  item_id: number;
  supplier_id: number;
  name: string;
  quantity_available: number;
  price: number;
  category: string;
  unit: string;
  description: string;
  min_temperature: number;
  max_temperature: number;
}

/* ─── Place Order ─── */
const PlaceOrder = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>("");
  const [inventory, setInventory] = useState<RawInventoryItem[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(true);
  const [loadingInventory, setLoadingInventory] = useState(false);

  const [cart, setCart] = useState<Record<number, number>>({});
  const [address, setAddress] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [payment, setPayment] = useState("Bank Transfer");

  // Fetch suppliers on mount
  useEffect(() => {
    const fetchSuppliers = async () => {
      try {
        const res = await fetch("http://localhost:5011/supplier");
        const data = await res.json();
        setSuppliers(data);
      } catch {
        toast({ title: "Failed to load suppliers", variant: "destructive" });
      } finally {
        setLoadingSuppliers(false);
      }
    };
    fetchSuppliers();
  }, []);

  // Fetch inventory when supplier changes
  useEffect(() => {
    if (!selectedSupplierId) {
      setInventory([]);
      return;
    }
    const fetchInventory = async () => {
      setLoadingInventory(true);
      setCart({});
      try {
        const url = `http://localhost:5001/api/inventory/items?supplier_id=${selectedSupplierId}`;
        console.log("Fetching inventory from:", url);
        const res = await fetch(url);
        console.log("Status:", res.status);
        const data = await res.json();
        setInventory(data);
      } catch {
        toast({ title: "Failed to load inventory", variant: "destructive" });
      } finally {
        setLoadingInventory(false);
      }
    };
    fetchInventory();
  }, [selectedSupplierId]);

  const addToCart = (id: number) =>
    setCart((c) => ({ ...c, [id]: (c[id] || 0) + 1 }));

  const updateQty = (id: number, qty: number) => {
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
      const item = inventory.find((i) => i.item_id === Number(id));
      return item ? { ...item, qty } : null;
    })
    .filter(Boolean) as (RawInventoryItem & { qty: number })[];

  const total = cartItems.reduce((s, i) => s + i.qty * i.price, 0);

  const selectedSupplier = suppliers.find(
    (s) => s.ID === Number(selectedSupplierId)
  );

  const placeOrder = () => {
    if (!cartItems.length || !address || !deliveryDate) {
      toast({ title: "Please fill all order details", variant: "destructive" });
      return;
    }
    const orderItems: OrderItem[] = cartItems.map((i) => ({
      inventoryId: String(i.item_id),
      name: i.name,
      qty: i.qty,
      unit: i.unit,
      pricePerUnit: i.price,
    }));
    const newOrder: Order = {
      id: `ORD-${String(orders.length + 1).padStart(3, "0")}`,
      buyerId: String(user!.ID),
      buyerName: user!.CompanyName || user!.Name || "",
      supplierId: String(selectedSupplierId),
      supplierName: selectedSupplier?.CompanyName || "",
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

      {/* Supplier Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Select Supplier</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingSuppliers ? (
            <p className="text-sm text-muted-foreground">Loading suppliers...</p>
          ) : (
            <Select value={selectedSupplierId} onValueChange={setSelectedSupplierId}>
              <SelectTrigger className="w-full md:w-80">
                <SelectValue placeholder="Choose a supplier..." />
              </SelectTrigger>
              <SelectContent>
                {suppliers.map((s) => (
                  <SelectItem key={s.ID} value={String(s.ID)}>
                    {s.CompanyName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {selectedSupplier && (
            <p className="text-sm text-muted-foreground mt-2">
              {selectedSupplier.Address} · {selectedSupplier.Phone}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Inventory */}
      {selectedSupplierId && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Package className="h-5 w-5 text-accent" /> Available Inventory
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingInventory ? (
              <p className="text-sm text-muted-foreground">Loading inventory...</p>
            ) : inventory.length === 0 ? (
              <p className="text-sm text-muted-foreground">No items available from this supplier.</p>
            ) : (
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
                    <TableRow key={item.item_id}>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>{item.category}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {item.min_temperature}°C to {item.max_temperature}°C
                      </TableCell>
                      <TableCell>{item.quantity_available} {item.unit}</TableCell>
                      <TableCell>${item.price.toFixed(2)}/{item.unit}</TableCell>
                      <TableCell className="text-right">
                        {cart[item.item_id] ? (
                          <div className="flex items-center justify-end gap-2">
                            <Button size="sm" variant="outline" onClick={() => updateQty(item.item_id, cart[item.item_id] - 1)}>−</Button>
                            <span className="w-8 text-center text-sm font-medium">{cart[item.item_id]}</span>
                            <Button size="sm" variant="outline" onClick={() => updateQty(item.item_id, cart[item.item_id] + 1)}>+</Button>
                          </div>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => addToCart(item.item_id)}>
                            Add
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

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
                <div key={item.item_id} className="flex justify-between text-sm">
                  <span>{item.name} × {item.qty} {item.unit}</span>
                  <span className="font-medium">${(item.qty * item.price).toFixed(2)}</span>
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
  const myOrders = orders.filter((o) => o.buyerId === String(user?.ID));

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
                <TableHead>Supplier</TableHead>
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
                  <TableCell className="text-sm">{order.supplierName}</TableCell>
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
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
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
  const { user, role } = useAuth();
  if (!user || role !== "buyer") return <Navigate to="/login/buyer" />;

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