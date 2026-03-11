import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  Package,
  ClipboardList,
  Plus,
  Pencil,
  Trash2,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { InventoryItem, Order } from "@/types";
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
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";

const navItems = [
  { label: "Inventory", path: "/supplier", icon: <Package className="h-4 w-4" /> },
  { label: "Orders", path: "/supplier/orders", icon: <ClipboardList className="h-4 w-4" /> },
];

/* ─── Inventory Management ─── */
const InventoryManagement = () => {
  const { inventory, setInventory } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();
  const [editItem, setEditItem] = useState<InventoryItem | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    name: "", category: "", unit: "kg", pricePerUnit: "", stockLevel: "", minTemp: "", maxTemp: "",
  });

  const resetForm = () => setForm({ name: "", category: "", unit: "kg", pricePerUnit: "", stockLevel: "", minTemp: "", maxTemp: "" });

  const openEdit = (item: InventoryItem) => {
    setEditItem(item);
    setForm({
      name: item.name,
      category: item.category,
      unit: item.unit,
      pricePerUnit: String(item.pricePerUnit),
      stockLevel: String(item.stockLevel),
      minTemp: String(item.minTemp),
      maxTemp: String(item.maxTemp),
    });
  };

  const saveItem = () => {
    if (!form.name || !form.category) {
      toast({ title: "Please fill required fields", variant: "destructive" });
      return;
    }
    const data: InventoryItem = {
      id: editItem?.id || `inv${Date.now()}`,
      name: form.name,
      category: form.category,
      unit: form.unit,
      pricePerUnit: Number(form.pricePerUnit),
      stockLevel: Number(form.stockLevel),
      minTemp: Number(form.minTemp),
      maxTemp: Number(form.maxTemp),
      supplierId: user!.id,
      supplierName: user!.company || user!.name,
    };

    if (editItem) {
      setInventory((prev) => prev.map((i) => (i.id === editItem.id ? data : i)));
      toast({ title: "Item updated" });
    } else {
      setInventory((prev) => [...prev, data]);
      toast({ title: "Item added" });
    }
    setEditItem(null);
    setShowAdd(false);
    resetForm();
  };

  const deleteItem = (id: string) => {
    setInventory((prev) => prev.filter((i) => i.id !== id));
    toast({ title: "Item deleted" });
  };

  const formDialog = (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{editItem ? "Edit Item" : "Add New Item"}</DialogTitle>
      </DialogHeader>
      <div className="grid gap-3 py-2">
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
          <div><Label>Category</Label><Input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="mt-1" /></div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div><Label>Unit</Label><Input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="mt-1" /></div>
          <div><Label>Price/Unit</Label><Input type="number" value={form.pricePerUnit} onChange={(e) => setForm({ ...form, pricePerUnit: e.target.value })} className="mt-1" /></div>
          <div><Label>Stock Level</Label><Input type="number" value={form.stockLevel} onChange={(e) => setForm({ ...form, stockLevel: e.target.value })} className="mt-1" /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Min Temp (°C)</Label><Input type="number" value={form.minTemp} onChange={(e) => setForm({ ...form, minTemp: e.target.value })} className="mt-1" /></div>
          <div><Label>Max Temp (°C)</Label><Input type="number" value={form.maxTemp} onChange={(e) => setForm({ ...form, maxTemp: e.target.value })} className="mt-1" /></div>
        </div>
      </div>
      <DialogFooter>
        <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
        <Button onClick={saveItem} className="gradient-frost text-accent-foreground hover:opacity-90">Save</Button>
      </DialogFooter>
    </DialogContent>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Inventory</h1>
        <Dialog open={showAdd} onOpenChange={(v) => { setShowAdd(v); if (!v) { resetForm(); setEditItem(null); } }}>
          <DialogTrigger asChild>
            <Button className="gradient-frost text-accent-foreground hover:opacity-90" onClick={() => { resetForm(); setShowAdd(true); }}>
              <Plus className="h-4 w-4 mr-1" /> Add Item
            </Button>
          </DialogTrigger>
          {formDialog}
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Temp Range</TableHead>
                <TableHead>Stock</TableHead>
                <TableHead>Price</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inventory.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell>{item.category}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{item.minTemp}°C to {item.maxTemp}°C</TableCell>
                  <TableCell>
                    <span className={item.stockLevel < 200 ? "text-destructive font-medium" : ""}>
                      {item.stockLevel} {item.unit}
                    </span>
                  </TableCell>
                  <TableCell>${item.pricePerUnit.toFixed(2)}/{item.unit}</TableCell>
                  <TableCell className="text-right space-x-1">
                    <Dialog open={editItem?.id === item.id} onOpenChange={(v) => { if (!v) setEditItem(null); }}>
                      <DialogTrigger asChild>
                        <Button size="icon" variant="ghost" onClick={() => openEdit(item)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </DialogTrigger>
                      {formDialog}
                    </Dialog>
                    <Button size="icon" variant="ghost" className="text-destructive" onClick={() => deleteItem(item.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

/* ─── Supplier Orders ─── */
const SupplierOrders = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();
  const myOrders = orders.filter((o) => o.supplierId === user?.id);

  const canCancel = (order: Order) => {
    if (order.status === "cancelled" || order.status === "delivered") return false;
    const delivery = new Date(order.deliveryDate);
    const now = new Date();
    const daysUntilDelivery = (delivery.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
    return daysUntilDelivery > 3;
  };

  const cancelOrder = (id: string) => {
    setOrders((prev) =>
      prev.map((o) => (o.id === id ? { ...o, status: "cancelled" as const, updatedAt: new Date().toISOString() } : o))
    );
    toast({ title: `Order ${id} cancelled` });
  };

  const confirmOrder = (id: string) => {
    setOrders((prev) =>
      prev.map((o) => (o.id === id && o.status === "pending" ? { ...o, status: "confirmed" as const, updatedAt: new Date().toISOString() } : o))
    );
    toast({ title: `Order ${id} confirmed` });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-foreground">Orders</h1>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order ID</TableHead>
                <TableHead>Buyer</TableHead>
                <TableHead>Items</TableHead>
                <TableHead>Delivery</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {myOrders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-medium">{order.id}</TableCell>
                  <TableCell>{order.buyerName}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {order.items.map((i) => `${i.name} ×${i.qty}`).join(", ")}
                  </TableCell>
                  <TableCell>{order.deliveryDate}</TableCell>
                  <TableCell>${order.totalAmount.toFixed(2)}</TableCell>
                  <TableCell><StatusBadge status={order.status} /></TableCell>
                  <TableCell className="text-right space-x-1">
                    {order.status === "pending" && (
                      <Button size="sm" variant="outline" onClick={() => confirmOrder(order.id)}>
                        Confirm
                      </Button>
                    )}
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
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">No orders</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

/* ─── Supplier Dashboard ─── */
const SupplierDashboard = () => {
  const { user } = useAuth();
  if (!user || user.role !== "supplier") return <Navigate to="/login/supplier" />;

  return (
    <DashboardLayout navItems={navItems} title="Supplier Portal">
      <Routes>
        <Route index element={<InventoryManagement />} />
        <Route path="orders" element={<SupplierOrders />} />
      </Routes>
    </DashboardLayout>
  );
};

export default SupplierDashboard;
