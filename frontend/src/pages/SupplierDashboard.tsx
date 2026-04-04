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
import { Order, OrderStatus } from "@/types";
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

// ── Service URLs ──────────────────────────────────────────────────────────────
const INVENTORY_SERVICE_URL       = "http://localhost:5001";
const ORDER_SERVICE_URL           = "http://localhost:5002";
const BUYER_SERVICE_URL           = "http://localhost:5012";
const MANAGE_SUPPLIER_SERVICE_URL = "http://localhost:5010";

const navItems = [
  { label: "Inventory", path: "/supplier", icon: <Package className="h-4 w-4" /> },
  { label: "Orders", path: "/supplier/orders", icon: <ClipboardList className="h-4 w-4" /> },
];

interface RawInventoryItem {
  item_id: number;
  supplier_id: number;
  name: string;
  quantity: number;
  price: number;
  category: string;
  unit: string;
  description: string;
  min_temperature: number;
  max_temperature: number;
}

// Raw shapes returned by the backend APIs
interface RawInventoryApiItem {
  item_id: number;
  name: string;
}

interface RawBuyer {
  ID: number;
  CompanyName: string;
}

interface RawOrderItem {
  ItemID: number;
  Quantity: number;
  UnitPrice: number;
}

interface RawOrder {
  ID: number;
  CustomerID: number;
  SupplierId: number;
  OrderStatus: string;
  TotalPrice: number;
  ScheduledDate: string;
  OrderItems: RawOrderItem[];
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
      const res = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items?supplier_id=${user.ID}`);
      const data = await res.json();
      setInventory(data);
    } catch {
      toast({ title: "Failed to load inventory", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInventory(); }, [user?.ID]);

  const categories = useMemo(() => {
    return [...new Set(inventory.map((i) => i.category).filter(Boolean))];
  }, [inventory]);

  const filtered = useMemo(() => {
    return inventory.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.category?.toLowerCase().includes(search.toLowerCase());
      const matchesCategory = categoryFilter === "all" || item.category === categoryFilter;
      return matchesSearch && matchesCategory;
    });
  }, [inventory, search, categoryFilter]);

  const resetForm = () => setForm(emptyForm);

  const openEdit = (item: RawInventoryItem) => {
    setEditItem(item);
    setForm({
      name:            item.name,
      category:        item.category,
      unit:            item.unit,
      price:           String(item.price),
      quantity:        String(item.quantity),
      min_temperature: String(item.min_temperature),
      max_temperature: String(item.max_temperature),
      description:     item.description || "",
    });
  };

  const saveItem = async () => {
    if (!form.name || !form.category) {
      toast({ title: "Please fill required fields", variant: "destructive" });
      return;
    }
    const payload = {
      supplier_id:     user!.ID,
      name:            form.name,
      category:        form.category,
      unit:            form.unit,
      price:           Number(form.price),
      quantity:        Number(form.quantity),
      min_temperature: Number(form.min_temperature),
      max_temperature: Number(form.max_temperature),
      description:     form.description,
    };
    try {
      if (editItem) {
        const res = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items/${editItem.item_id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed to update");
        toast({ title: "Item updated" });
      } else {
        const res = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items`, {
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
      const res = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
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
              <SelectTrigger className="mt-1"><SelectValue placeholder="Select unit" /></SelectTrigger>
              <SelectContent>
                {["kg","g","lb","litre","ml","pack","box","bottle","carton","piece","dozen","tray","cup"].map((u) => (
                  <SelectItem key={u} value={u}>{u}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
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

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search items..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-48"><SelectValue placeholder="All Categories" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((cat) => <SelectItem key={cat} value={cat}>{cat}</SelectItem>)}
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
                      <span className={item.quantity < 20 ? "text-destructive font-medium" : ""}>
                        {item.quantity} {item.unit}
                      </span>
                    </TableCell>
                    <TableCell>${item.price.toFixed(2)}/{item.unit}</TableCell>
                    <TableCell className="text-right space-x-1">
                      <Dialog open={editItem?.item_id === item.item_id} onOpenChange={(v) => { if (!v) setEditItem(null); }}>
                        <DialogTrigger asChild>
                          <Button size="icon" variant="ghost" onClick={() => openEdit(item)}><Pencil className="h-4 w-4" /></Button>
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
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-8">No items found</TableCell>
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
  const { user } = useAuth();
  const { toast } = useToast();
  const [myOrders, setMyOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  // Search & sort state
  const [orderSearch, setOrderSearch] = useState("");
  const [sortMode, setSortMode] = useState<"id" | "upcoming">("upcoming");

  // Modal: which order's items are being viewed
  const [itemsModalOrder, setItemsModalOrder] = useState<Order | null>(null);

  // Lookup maps for resolving IDs to human-readable names
  const [itemMap, setItemMap]   = useState<Record<number, string>>({});
  const [buyerMap, setBuyerMap] = useState<Record<number, string>>({});

  // Fetch all inventory items + all buyers once on mount
  useEffect(() => {
    const fetchLookups = async () => {
      try {
        const invRes  = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items`);
        const invData: RawInventoryApiItem[] = await invRes.json();
        const iMap: Record<number, string> = {};
        (Array.isArray(invData) ? invData : []).forEach((item) => {
          iMap[item.item_id] = item.name;
        });
        setItemMap(iMap);
      } catch {
        console.warn("Could not fetch inventory for name lookup");
      }

      try {
        const buyerRes  = await fetch(`${BUYER_SERVICE_URL}/buyer`);
        const buyerData: RawBuyer[] = await buyerRes.json();
        const bMap: Record<number, string> = {};
        (Array.isArray(buyerData) ? buyerData : []).forEach((b) => {
          bMap[b.ID] = b.CompanyName;
        });
        setBuyerMap(bMap);
      } catch {
        console.warn("Could not fetch buyers for name lookup");
      }
    };
    fetchLookups();
  }, []);

  const mapStatus = (backendStatus: string): OrderStatus => {
    const map: Record<string, OrderStatus> = {
      received:           "pending",
      pending:            "pending",
      paid:               "confirmed",
      confirmed:          "confirmed",
      scheduled:          "processing",
      in_transit:         "in_transit",
      delivered:          "delivered",
      cancelled:          "cancelled",
      failed:             "cancelled",
      failed_temp_breach: "cancelled",
    };
    return map[backendStatus?.toLowerCase()] ?? "pending";
  };

  const fetchOrders = async () => {
    if (!user?.ID) return;
    try {
      const res  = await fetch(`${ORDER_SERVICE_URL}/orders`);
      const data: RawOrder[] = await res.json();
      const filtered = (Array.isArray(data) ? data : [])
        .filter((o) => String(o.SupplierId) === String(user.ID))
        .map((o) => ({
          id:              String(o.ID),
          buyerId:         String(o.CustomerID),
          supplierId:      String(o.SupplierId),
          status:          mapStatus(o.OrderStatus),
          totalAmount:     o.TotalPrice ?? 0,
          deliveryDate:    o.ScheduledDate ?? "",
          items: (o.OrderItems ?? []).map((i) => ({
            inventoryId:  String(i.ItemID),
            name:         String(i.ItemID),
            qty:          i.Quantity,
            unit:         "",
            pricePerUnit: i.UnitPrice,
          })),
          createdAt:       "",
          updatedAt:       "",
          supplierName:    "",
          buyerName:       String(o.CustomerID),
          deliveryAddress: "",
          paymentMethod:   "",
        }));
      setMyOrders(filtered);
    } catch {
      toast({ title: "Failed to load orders", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrders(); }, [user?.ID]);

  // Filtered + sorted orders
  const filteredAndSorted = useMemo(() => {
    let result = [...myOrders];

    if (orderSearch.trim()) {
      const q = orderSearch.toLowerCase();
      result = result.filter(
        (o) =>
          o.id.toLowerCase().includes(q) ||
          (buyerMap[Number(o.buyerId)] ?? o.buyerId).toLowerCase().includes(q)
      );
    }

    if (sortMode === "id") {
      result.sort((a, b) => Number(a.id) - Number(b.id));
    } else {
      result.sort((a, b) => {
        const dateA = a.deliveryDate ? new Date(a.deliveryDate).getTime() : Infinity;
        const dateB = b.deliveryDate ? new Date(b.deliveryDate).getTime() : Infinity;
        return dateA - dateB;
      });
    }

    return result;
  }, [myOrders, orderSearch, sortMode, buyerMap]);

  const canCancel = (order: Order) => {
    if (order.status === "cancelled" || order.status === "delivered") return false;
    const delivery = new Date(order.deliveryDate);
    const now = new Date();
    const daysUntilDelivery = (delivery.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
    return daysUntilDelivery > 3;
  };

  const cancelOrder = async (id: string) => {
    setCancellingId(id);
    try {
      const res = await fetch(
        `${MANAGE_SUPPLIER_SERVICE_URL}/supplier/${user?.ID}/orders/${id}/cancel`,
        { method: "PUT" }
      );
      if (!res.ok) throw new Error("Failed to cancel");
      toast({ title: `Order ${id} cancelled successfully` });
      await fetchOrders();
    } catch {
      toast({ title: "Failed to cancel order", variant: "destructive" });
    } finally {
      setCancellingId(null);
    }
  };

  // Resolve item name from map
  const resolvedItemName = (inventoryId: string) =>
    itemMap[Number(inventoryId)] ?? `Item #${inventoryId}`;

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header with search + sort toggle */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-foreground">Orders</h1>
        <div className="flex gap-2 flex-wrap items-center">
          <div className="relative min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by order ID or buyer..."
              value={orderSearch}
              onChange={(e) => setOrderSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex rounded-md border overflow-hidden text-sm">
            <button
              className={`px-3 py-2 transition-colors ${
                sortMode === "upcoming"
                  ? "bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:bg-muted"
              }`}
              onClick={() => setSortMode("upcoming")}
            >
              Upcoming
            </button>
            <button
              className={`px-3 py-2 transition-colors border-l ${
                sortMode === "id"
                  ? "bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:bg-muted"
              }`}
              onClick={() => setSortMode("id")}
            >
              Order ID
            </button>
          </div>
        </div>
      </div>

      {/* Orders table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="text-sm text-muted-foreground p-6">Loading orders...</p>
          ) : (
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
                {filteredAndSorted.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">{order.id}</TableCell>
                    <TableCell>{buyerMap[Number(order.buyerId)] ?? order.buyerId}</TableCell>

                    {/* Items cell */}
                    <TableCell className="text-sm text-muted-foreground">
                      {order.items.length === 0 ? (
                        <span>—</span>
                      ) : order.items.length === 1 ? (
                        // Single item: just show inline text
                        <span>
                          {resolvedItemName(order.items[0].inventoryId)} ×{order.items[0].qty}
                        </span>
                      ) : (
                        // Multiple items: clickable pill showing first item + "+N more"
                        <button
                          onClick={() => setItemsModalOrder(order)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted hover:bg-muted/80 border text-xs font-medium transition-colors cursor-pointer"
                        >
                          <span>
                            {resolvedItemName(order.items[0].inventoryId)} ×{order.items[0].qty}
                          </span>
                          <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded-full text-[10px] font-semibold">
                            +{order.items.length - 1} more
                          </span>
                        </button>
                      )}
                    </TableCell>

                    <TableCell>{order.deliveryDate}</TableCell>
                    <TableCell>${order.totalAmount.toFixed(2)}</TableCell>
                    <TableCell><StatusBadge status={order.status} /></TableCell>
                    <TableCell className="text-right space-x-1">
                      {canCancel(order) && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => cancelOrder(order.id)}
                          disabled={cancellingId === order.id}
                        >
                          {cancellingId === order.id ? "Cancelling..." : "Cancel"}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {filteredAndSorted.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      {orderSearch ? "No orders match your search" : "No orders"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ── Items Detail Modal ── */}
      <Dialog open={!!itemsModalOrder} onOpenChange={(v) => { if (!v) setItemsModalOrder(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Order #{itemsModalOrder?.id} — Items</DialogTitle>
            <p className="text-sm text-muted-foreground pt-1">
              Buyer: {buyerMap[Number(itemsModalOrder?.buyerId)] ?? itemsModalOrder?.buyerId}
            </p>
          </DialogHeader>

          {/* Scrollable item list */}
          <div className="divide-y max-h-72 overflow-y-auto -mx-6 px-6">
            {itemsModalOrder?.items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-sm">{resolvedItemName(item.inventoryId)}</p>
                  <p className="text-xs text-muted-foreground">
                    Qty: {item.qty}{item.unit ? ` ${item.unit}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">
                    ${(item.pricePerUnit * item.qty).toFixed(2)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    ${item.pricePerUnit.toFixed(2)} / unit
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Order total */}
          <div className="flex items-center justify-between pt-3 border-t">
            <span className="text-sm font-semibold text-muted-foreground">Order Total</span>
            <span className="text-base font-bold">${itemsModalOrder?.totalAmount.toFixed(2)}</span>
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" className="w-full">Close</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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