import React, { useState, useEffect, useMemo } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  Package,
  ClipboardList,
  Plus,
  Pencil,
  Trash2,
  Search,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { Order } from "@/types";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

const navItems = [
  { label: "Inventory", path: "/supplier", icon: <Package className="h-4 w-4" /> },
  { label: "Orders", path: "/supplier/orders", icon: <ClipboardList className="h-4 w-4" /> },
];

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

const emptyForm = {
  name: "", category: "", unit: "kg", price: "", quantity: "", min_temperature: "", max_temperature: "", description: "",
};

/* ─── Inventory Management ─── */
const InventoryManagement = () => {
  const { user } = useAuth();
  const { toast } = useToast();

  const [inventory, setInventory] = useState<RawInventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [editItem, setEditItem] = useState<RawInventoryItem | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const fetchInventory = async () => {
    if (!user?.ID) return;
    try {
      const res = await fetch(`http://localhost:5001/api/inventory/items?supplier_id=${user.ID}`);
      const data = await res.json();
      setInventory(data);
    } catch {
      toast({ title: "Failed to load inventory", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, [user?.ID]);

  const categories = useMemo(() => {
    const cats = [...new Set(inventory.map((i) => i.category).filter(Boolean))];
    return cats;
  }, [inventory]);

  const filtered = useMemo(() => {
    return inventory.filter((item) => {
      const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.category?.toLowerCase().includes(search.toLowerCase());
      const matchesCategory = categoryFilter === "all" || item.category === categoryFilter;
      return matchesSearch && matchesCategory;
    });
  }, [inventory, search, categoryFilter]);

  const resetForm = () => setForm(emptyForm);

  const openEdit = (item: RawInventoryItem) => {
    setEditItem(item);
    setForm({
      name: item.name,
      category: item.category,
      unit: item.unit,
      price: String(item.price),
      quantity: String(item.quantity_available),
      min_temperature: String(item.min_temperature),
      max_temperature: String(item.max_temperature),
      description: item.description || "",
    });
  };

  const saveItem = async () => {
    if (!form.name || !form.category) {
      toast({ title: "Please fill required fields", variant: "destructive" });
      return;
    }

    const payload = {
      supplier_id: user!.ID,
      name: form.name,
      category: form.category,
      unit: form.unit,
      price: Number(form.price),
      quantity: Number(form.quantity),
      min_temperature: Number(form.min_temperature),
      max_temperature: Number(form.max_temperature),
      description: form.description,
    };

    try {
      if (editItem) {
        // Update existing item
        const res = await fetch(`http://localhost:5001/api/inventory/items/${editItem.item_id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to update");
        toast({ title: "Item updated" });
      } else {
        // Create new item
        const res = await fetch(`http://localhost:5001/api/inventory/items`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to create");
        toast({ title: "Item added" });
      }
      await fetchInventory();
    } catch {
      toast({ title: "Failed to save item", variant: "destructive" });
    }

    setEditItem(null);
    setShowAdd(false);
    resetForm();
  };

  const deleteItem = async (id: number) => {
    try {
      await fetch(`http://localhost:5001/inventory/items/${id}`, { method: "DELETE" });
      setInventory((prev) => prev.filter((i) => i.item_id !== id));
      toast({ title: "Item deleted" });
    } catch {
      toast({ title: "Failed to delete item", variant: "destructive" });
    }
  };

  const formDialog = (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{editItem ? "Edit Item" : "Add New Item"}</DialogTitle>
      </DialogHeader>
      <div className="grid gap-3 py-2">
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Name *</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
          <div><Label>Category *</Label><Input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="mt-1" /></div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div><Label>Price/Unit</Label><Input type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="mt-1" /></div>
          <div><Label>Quantity</Label><Input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className="mt-1" /></div>
          <div>
            <Label>Unit</Label>
            <Select value={form.unit} onValueChange={(v) => setForm({ ...form, unit: v })}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select unit" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="kg">kg</SelectItem>
                <SelectItem value="g">g</SelectItem>
                <SelectItem value="lb">lb</SelectItem>
                <SelectItem value="litre">Litre</SelectItem>
                <SelectItem value="ml">ml</SelectItem>
                <SelectItem value="pack">Pack</SelectItem>
                <SelectItem value="box">Box</SelectItem>
                <SelectItem value="bottle">Bottle</SelectItem>
                <SelectItem value="carton">Carton</SelectItem>
                <SelectItem value="piece">Piece</SelectItem>
                <SelectItem value="dozen">Dozen</SelectItem>
                <SelectItem value="tray">Tray</SelectItem>
                <SelectItem value="cup">Cup</SelectItem>
              </SelectContent>
            </Select>
          </div>        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Min Temp (°C)</Label><Input type="number" value={form.min_temperature} onChange={(e) => setForm({ ...form, min_temperature: e.target.value })} className="mt-1" /></div>
          <div><Label>Max Temp (°C)</Label><Input type="number" value={form.max_temperature} onChange={(e) => setForm({ ...form, max_temperature: e.target.value })} className="mt-1" /></div>
        </div>
        <div><Label>Description</Label><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1" /></div>
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

      {/* Search & Filter */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="text-sm text-muted-foreground p-6">Loading inventory...</p>
          ) : (
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
                {filtered.map((item) => (
                  <TableRow key={item.item_id}>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell>{item.category}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {item.min_temperature}°C to {item.max_temperature}°C
                    </TableCell>
                    <TableCell>
                      <span className={item.quantity_available < 20 ? "text-destructive font-medium" : ""}>
                        {item.quantity_available} {item.unit}
                      </span>
                    </TableCell>
                    <TableCell>${item.price.toFixed(2)}/{item.unit}</TableCell>
                    <TableCell className="text-right space-x-1">
                      <Dialog open={editItem?.item_id === item.item_id} onOpenChange={(v) => { if (!v) setEditItem(null); }}>
                        <DialogTrigger asChild>
                          <Button size="icon" variant="ghost" onClick={() => openEdit(item)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        {formDialog}
                      </Dialog>
                      <Button size="icon" variant="ghost" className="text-destructive" onClick={() => deleteItem(item.item_id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                      No items found
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

/* ─── Supplier Orders ─── */
const SupplierOrders = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();
  const myOrders = orders.filter((o) => o.supplierId === String(user?.ID));

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
  const { user, role } = useAuth();
  if (!user || role !== "supplier") return <Navigate to="/login" />;

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
