import React, { useState, useEffect, useRef, useMemo } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  ShoppingCart,
  ClipboardList,
  Package,
  Plus,
  Trash2,
  Search,
  ChevronRight,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { Order, OrderItem, OrderStatus } from "@/types";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { loadStripe, Stripe, StripeCardElement } from "@stripe/stripe-js";

const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
const stripePromise = stripePublishableKey ? loadStripe(stripePublishableKey) : null;

// ── Service URLs ──────────────────────────────────────────────────────────────
const SUPPLIER_SERVICE_URL     = "http://localhost:5011";
const INVENTORY_SERVICE_URL    = "http://localhost:5001";
const PLACE_ORDER_SERVICE_URL  = "http://localhost:5006";
const ORDER_SERVICE_URL        = "http://localhost:5002";
const CANCEL_ORDER_SERVICE_URL = "http://localhost:5009";

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

interface PlaceOrderResult {
  result?: {
    data?: {
      client_secret?: string;
      OrderID?: number;
    };
  };
  message?: string;
  Error?: string;
}

// ── Step indicator ────────────────────────────────────────────────────────────
const steps = ["Shop", "Cart & Details", "Payment", "Confirmed"];

const StepIndicator = ({ current }: { current: number }) => (
  <div className="flex items-center gap-0 mb-8">
    {steps.map((label, idx) => (
      <React.Fragment key={label}>
        <div className="flex flex-col items-center">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
              idx < current
                ? "bg-primary border-primary text-primary-foreground"
                : idx === current
                ? "bg-primary/10 border-primary text-primary"
                : "bg-muted border-muted-foreground/30 text-muted-foreground"
            }`}
          >
            {idx < current ? <CheckCircle2 className="h-4 w-4" /> : idx + 1}
          </div>
          <span
            className={`mt-1 text-[10px] font-medium whitespace-nowrap ${
              idx === current ? "text-primary" : "text-muted-foreground"
            }`}
          >
            {label}
          </span>
        </div>
        {idx < steps.length - 1 && (
          <div
            className={`flex-1 h-0.5 mx-1 mb-4 transition-all ${
              idx < current ? "bg-primary" : "bg-muted"
            }`}
          />
        )}
      </React.Fragment>
    ))}
  </div>
);

/* ─── Place Order (multi-step) ─── */
const PlaceOrder = () => {
  const { orders, setOrders } = useAppData();
  const { user } = useAuth();
  const { toast } = useToast();

  // ── Step: 0=shop, 1=cart+details, 2=payment, 3=confirmed
  const [step, setStep] = useState(0);

  // ── Step 0: browse
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>("");
  const [inventory, setInventory] = useState<RawInventoryItem[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(true);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [inventorySearch, setInventorySearch] = useState("");
  const [cart, setCart] = useState<Record<number, number>>({});

  // ── Step 1: delivery details
  const [address, setAddress] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [payment, setPayment] = useState("Credit Card");

  // ── Step 2: payment
  const [isPaying, setIsPaying] = useState(false);
  const [cardName, setCardName] = useState("");
  const stripeRef = useRef<Stripe | null>(null);
  const cardElementRef = useRef<StripeCardElement | null>(null);
  const cardMountRef = useRef<HTMLDivElement | null>(null);

  // ── Confirmed order id
  const [confirmedOrderId, setConfirmedOrderId] = useState("");

  // ── Cart items view modal
  const [cartOpen, setCartOpen] = useState(false);

  // Fetch suppliers
  useEffect(() => {
    const fetchSuppliers = async () => {
      try {
        const res = await fetch(`${SUPPLIER_SERVICE_URL}/supplier`);
        const data: Supplier[] = await res.json();
        setSuppliers(data);
      } catch {
        toast({ title: "Failed to load suppliers", variant: "destructive" });
      } finally {
        setLoadingSuppliers(false);
      }
    };
    fetchSuppliers();
  }, [toast]);

  // Fetch inventory when supplier changes
  useEffect(() => {
    if (!selectedSupplierId) { setInventory([]); return; }
    const fetchInventory = async () => {
      setLoadingInventory(true);
      setCart({});
      try {
        const res = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items?supplier_id=${selectedSupplierId}`);
        const data: RawInventoryItem[] = await res.json();
        setInventory(data);
      } catch {
        toast({ title: "Failed to load inventory", variant: "destructive" });
      } finally {
        setLoadingInventory(false);
      }
    };
    fetchInventory();
  }, [selectedSupplierId, toast]);

  // Mount Stripe card element when we reach payment step
  useEffect(() => {
    if (step !== 2) return;
    const isCard = payment === "Credit Card" || payment === "Debit Card";
    if (!isCard) return;

    let cancelled = false;
    const init = async () => {
      if (!stripePromise || !cardMountRef.current) return;
      const stripe = await stripePromise;
      if (!stripe || cancelled) return;
      stripeRef.current = stripe;
      if (!cardElementRef.current && cardMountRef.current) {
        const elements = stripe.elements();
        const card = elements.create("card", { hidePostalCode: true });
        card.mount(cardMountRef.current);
        cardElementRef.current = card;
      }
    };
    init();
    return () => { cancelled = true; };
  }, [step, payment]);

  const addToCart = (id: number) => setCart((c) => ({ ...c, [id]: (c[id] || 0) + 1 }));
  const updateQty = (id: number, qty: number) => {
    if (qty <= 0) { const n = { ...cart }; delete n[id]; setCart(n); }
    else setCart((c) => ({ ...c, [id]: qty }));
  };

  const cartItems = useMemo(() =>
    Object.entries(cart)
      .map(([id, qty]) => {
        const item = inventory.find((i) => i.item_id === Number(id));
        return item ? { ...item, qty } : null;
      })
      .filter(Boolean) as (RawInventoryItem & { qty: number })[],
    [cart, inventory]
  );

  const total = cartItems.reduce((s, i) => s + i.qty * i.price, 0);
  const selectedSupplier = suppliers.find((s) => s.ID === Number(selectedSupplierId));
  const cartCount = Object.values(cart).reduce((a, b) => a + b, 0);
  const isCard = payment === "Credit Card" || payment === "Debit Card";

  const filteredInventory = useMemo(() => {
    if (!inventorySearch.trim()) return inventory;
    const q = inventorySearch.toLowerCase();
    return inventory.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        i.category?.toLowerCase().includes(q)
    );
  }, [inventory, inventorySearch]);

  const deductInventory = async (items: (RawInventoryItem & { qty: number })[]) => {
    await Promise.allSettled(
      items.map((item) =>
        fetch(`${INVENTORY_SERVICE_URL}/inventory/deduct`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_id: item.item_id, quantity: item.qty }),
        })
      )
    );
  };

  // ── Step 2 → 3: pay then place order
  const handlePay = async () => {
    if (isCard && (!cardName || !cardElementRef.current || !stripeRef.current)) {
      toast({ title: "Please fill all card details", variant: "destructive" });
      return;
    }

    setIsPaying(true);
    try {
      // 1. Call placeorder to get Stripe client_secret
      const payload = {
        CustomerID: Number(user!.ID),
        OrderItems: cartItems.map((i) => ({ ItemID: i.item_id, Quantity: i.qty })),
        SupplierID: Number(selectedSupplierId),
        Address: address,
        ScheduledDate: deliveryDate,
      };

      const orderRes = await fetch(`${PLACE_ORDER_SERVICE_URL}/placeorder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const orderResult: PlaceOrderResult = await orderRes.json().catch(() => ({}));

      if (!orderRes.ok) {
        toast({
          title: "Failed to initialise order",
          description: orderResult?.message || orderResult?.Error || "Please try again",
          variant: "destructive",
        });
        return;
      }

      const clientSecret = orderResult?.result?.data?.client_secret;
      const orderIdFromBackend = orderResult?.result?.data?.OrderID;

      if (!clientSecret) {
        toast({ title: "Missing payment intent from server", variant: "destructive" });
        return;
      }

      // 2. Confirm Stripe payment
      if (isCard) {
        const result = await stripeRef.current!.confirmCardPayment(clientSecret, {
          payment_method: {
            card: cardElementRef.current!,
            billing_details: { name: cardName },
          },
        });

        if (result.error) {
          toast({ title: "Payment failed", description: result.error.message, variant: "destructive" });
          return;
        }
        if (result.paymentIntent?.status !== "succeeded") {
          toast({ title: "Payment not completed", description: `Status: ${result.paymentIntent?.status}`, variant: "destructive" });
          return;
        }

        // 3. Forward to backend webhook continuation
        const webhookRes = await fetch("http://localhost:5004/payment/confirm-intent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ payment_intent_id: result.paymentIntent.id }),
        });

        if (!webhookRes.ok) {
          const webhookResult: { error?: string } = await webhookRes.json().catch(() => ({}));
          toast({
            title: "Backend flow continuation failed",
            description: webhookResult?.error || "Payment succeeded but backend failed",
            variant: "destructive",
          });
          return;
        }
      }

      // 4. Deduct inventory
      await deductInventory(cartItems);

      // 5. Build local order record
      const generatedOrderId = `ORD-${String(orderIdFromBackend).padStart(3, "0")}`;
      const orderItems: OrderItem[] = cartItems.map((i) => ({
        inventoryId: String(i.item_id),
        name: i.name,
        qty: i.qty,
        unit: i.unit,
        pricePerUnit: i.price,
      }));

      const newOrder: Order = {
        id: generatedOrderId,
        buyerId: String(user!.ID),
        buyerName: user!.CompanyName || user!.Name || "",
        supplierId: String(selectedSupplierId),
        supplierName: selectedSupplier?.CompanyName || "",
        items: orderItems,
        totalAmount: total,
        deliveryAddress: address,
        deliveryDate,
        status: "confirmed",
        paymentMethod: payment,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      setOrders((prev) => [...prev, newOrder]);
      setConfirmedOrderId(generatedOrderId);
      setStep(3);
    } catch {
      toast({ title: "Payment failed", description: "Unable to confirm payment.", variant: "destructive" });
    } finally {
      setIsPaying(false);
    }
  };

  const resetAll = () => {
    setStep(0);
    setCart({});
    setAddress("");
    setDeliveryDate("");
    setCardName("");
    setInventorySearch("");
    setConfirmedOrderId("");
    cardElementRef.current = null;
  };

  // ── RENDER ────────────────────────────────────────────────────────────────

  // Step 3: Confirmed
  if (step === 3) {
    return (
      <div className="space-y-6 animate-fade-in">
        <StepIndicator current={3} />
        <div className="flex flex-col items-center justify-center py-16 space-y-4 text-center">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <CheckCircle2 className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Order Placed!</h2>
          <p className="text-muted-foreground">
            Your order <span className="font-semibold text-foreground">{confirmedOrderId}</span> has been confirmed and payment received.
          </p>
          <Button className="gradient-frost text-accent-foreground hover:opacity-90 mt-4" onClick={resetAll}>
            Place Another Order
          </Button>
        </div>
      </div>
    );
  }

  // Step 2: Payment
  if (step === 2) {
    return (
      <div className="space-y-6 animate-fade-in">
        <StepIndicator current={2} />
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <h1 className="text-2xl font-bold text-foreground">Payment</h1>
        </div>

        {/* Order summary */}
        <Card>
          <CardHeader><CardTitle className="text-base">Order Summary</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {cartItems.map((item) => (
              <div key={item.item_id} className="flex justify-between text-sm">
                <span>{item.name} × {item.qty} {item.unit}</span>
                <span className="font-medium">${(item.qty * item.price).toFixed(2)}</span>
              </div>
            ))}
            <div className="border-t pt-2 flex justify-between font-bold">
              <span>Total</span>
              <span>${total.toFixed(2)}</span>
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              Delivery to: {address} · {deliveryDate}
            </p>
          </CardContent>
        </Card>

        {/* Card details */}
        <Card>
          <CardHeader><CardTitle className="text-base">{payment}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {isCard ? (
              <div className="grid gap-4">
                <div>
                  <Label>Cardholder Name</Label>
                  <Input
                    value={cardName}
                    onChange={(e) => setCardName(e.target.value)}
                    placeholder="Name on card"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Card Details</Label>
                  <div
                    ref={cardMountRef}
                    className="mt-1 rounded-md border border-input bg-background px-3 py-3"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    Card number, expiry, and CVC are securely collected by Stripe.
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No additional fields required for {payment}.
              </p>
            )}

            <Button
              onClick={handlePay}
              disabled={isPaying}
              className="w-full gradient-frost text-accent-foreground hover:opacity-90"
            >
              {isPaying ? "Processing payment..." : `Pay & Place Order — $${total.toFixed(2)}`}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Step 1: Cart + delivery details
  if (step === 1) {
    return (
      <div className="space-y-6 animate-fade-in">
        <StepIndicator current={1} />
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setStep(0)}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <h1 className="text-2xl font-bold text-foreground">Cart & Details</h1>
        </div>

        {/* Cart items */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShoppingCart className="h-5 w-5 text-accent" /> Your Cart
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {cartItems.map((item) => (
                <div key={item.item_id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium">{item.name}</p>
                    <p className="text-xs text-muted-foreground">${item.price.toFixed(2)} / {item.unit}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => updateQty(item.item_id, item.qty - 1)}>−</Button>
                    <span className="w-8 text-center text-sm font-medium">{item.qty}</span>
                    <Button size="sm" variant="outline" onClick={() => updateQty(item.item_id, item.qty + 1)}>+</Button>
                    <span className="w-20 text-right text-sm font-semibold">${(item.qty * item.price).toFixed(2)}</span>
                    <Button size="icon" variant="ghost" className="text-destructive h-7 w-7" onClick={() => updateQty(item.item_id, 0)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
              {cartItems.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">Your cart is empty. Go back to add items.</p>
              )}
              {cartItems.length > 0 && (
                <div className="flex justify-between font-bold pt-2 text-base">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Delivery details */}
        <Card>
          <CardHeader><CardTitle className="text-lg">Delivery Details</CardTitle></CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <Label>Delivery Address</Label>
                <Input
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Full delivery address"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Delivery Date</Label>
                <Input
                  type="date"
                  value={deliveryDate}
                  onChange={(e) => setDeliveryDate(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Payment Method</Label>
                <select
                  value={payment}
                  onChange={(e) => setPayment(e.target.value)}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option>Credit Card</option>
                  <option>Debit Card</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button
          onClick={() => {
            if (!cartItems.length) { toast({ title: "Cart is empty", variant: "destructive" }); return; }
            if (!address || !deliveryDate) { toast({ title: "Please fill delivery details", variant: "destructive" }); return; }
            setStep(2);
          }}
          className="w-full gradient-frost text-accent-foreground hover:opacity-90"
        >
          Continue to Payment <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    );
  }

  // Step 0: Shop
  return (
    <div className="space-y-6 animate-fade-in">
      <StepIndicator current={0} />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Place New Order</h1>
        {cartCount > 0 && (
          <Button
            variant="outline"
            className="relative"
            onClick={() => setStep(1)}
          >
            <ShoppingCart className="h-4 w-4 mr-2" />
            View Cart
            <span className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold">
              {cartCount}
            </span>
          </Button>
        )}
      </div>

      {/* Supplier selector */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Select Supplier</CardTitle></CardHeader>
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
                  <SelectItem key={s.ID} value={String(s.ID)}>{s.CompanyName}</SelectItem>
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
            <div className="flex items-center justify-between flex-wrap gap-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Package className="h-5 w-5 text-accent" /> Available Items
              </CardTitle>
              <div className="relative w-60">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search items..."
                  value={inventorySearch}
                  onChange={(e) => setInventorySearch(e.target.value)}
                  className="pl-9 h-8 text-sm"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loadingInventory ? (
              <p className="text-sm text-muted-foreground">Loading inventory...</p>
            ) : filteredInventory.length === 0 ? (
              <p className="text-sm text-muted-foreground">No items found.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Temp Range</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead>Price/Unit</TableHead>
                    <TableHead className="text-right">Add to Cart</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredInventory.map((item) => (
                    <TableRow key={item.item_id}>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>{item.category}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {item.min_temperature}°C to {item.max_temperature}°C
                      </TableCell>
                      <TableCell>{item.quantity} {item.unit}</TableCell>
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

      {/* Sticky proceed button when cart has items */}
      {cartCount > 0 && (
        <div className="sticky bottom-4 flex justify-end">
          <Button
            onClick={() => setStep(1)}
            className="gradient-frost text-accent-foreground hover:opacity-90 shadow-lg"
          >
            Proceed to Cart ({cartCount} item{cartCount !== 1 ? "s" : ""}) — ${total.toFixed(2)}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
};

/* ─── Order History ─── */
const OrderHistory = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [myOrders, setMyOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [itemsModalOrder, setItemsModalOrder] = useState<Order | null>(null);
  const [orderSearch, setOrderSearch] = useState("");
  const [sortMode, setSortMode] = useState<"upcoming" | "id">("upcoming");

  // Lookup: item id → name
  const [itemMap, setItemMap] = useState<Record<number, string>>({});
  const [supplierMap, setSupplierMap] = useState<Record<number, string>>({});

  useEffect(() => {
    const fetchLookups = async () => {
      try {
        const invRes = await fetch(`${INVENTORY_SERVICE_URL}/api/inventory/items`);
        const invData: RawInventoryApiItem[] = await invRes.json();
        const iMap: Record<number, string> = {};
        (Array.isArray(invData) ? invData : []).forEach((item) => { iMap[item.item_id] = item.name; });
        setItemMap(iMap);
      } catch { console.warn("Could not fetch inventory lookup"); }

      try {
        const supRes = await fetch(`${SUPPLIER_SERVICE_URL}/supplier`);
        const supData: Supplier[] = await supRes.json();
        const sMap: Record<number, string> = {};
        (Array.isArray(supData) ? supData : []).forEach((s) => { sMap[s.ID] = s.CompanyName; });
        setSupplierMap(sMap);
      } catch { console.warn("Could not fetch supplier lookup"); }
    };
    fetchLookups();
  }, []);

  const mapStatus = (backendStatus: string): OrderStatus => {
    const map: Record<string, OrderStatus> = {
      received: "pending", pending: "pending",
      paid: "confirmed", confirmed: "confirmed",
      scheduled: "processing",
      in_transit: "in_transit",
      delivered: "delivered",
      cancelled: "cancelled", failed: "cancelled", failed_temp_breach: "cancelled",
    };
    return map[backendStatus?.toLowerCase()] ?? "pending";
  };

  const fetchOrders = async () => {
    if (!user?.ID) return;
    try {
      const res = await fetch(`${ORDER_SERVICE_URL}/orders`);
      const data: RawOrder[] = await res.json();
      const filtered = (Array.isArray(data) ? data : [])
        .filter((o) => String(o.CustomerID) === String(user.ID))
        .map((o) => ({
          id: String(o.ID),
          buyerId: String(o.CustomerID),
          supplierId: String(o.SupplierId),
          status: mapStatus(o.OrderStatus),
          totalAmount: o.TotalPrice ?? 0,
          deliveryDate: o.ScheduledDate ?? "",
          items: (o.OrderItems ?? []).map((i) => ({
            inventoryId: String(i.ItemID),
            name: String(i.ItemID),
            qty: i.Quantity,
            unit: "",
            pricePerUnit: i.UnitPrice,
          })),
          createdAt: "", updatedAt: "",
          supplierName: "", buyerName: "",
          deliveryAddress: "", paymentMethod: "",
        }));
      setMyOrders(filtered);
    } catch {
      toast({ title: "Failed to load orders", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrders(); }, [user?.ID]);

  const filteredAndSorted = useMemo(() => {
    let result = [...myOrders];
    if (orderSearch.trim()) {
      const q = orderSearch.toLowerCase();
      result = result.filter(
        (o) =>
          o.id.toLowerCase().includes(q) ||
          (supplierMap[Number(o.supplierId)] ?? o.supplierId).toLowerCase().includes(q)
      );
    }
    if (sortMode === "id") {
      result.sort((a, b) => Number(a.id) - Number(b.id));
    } else {
      result.sort((a, b) => {
        const dA = a.deliveryDate ? new Date(a.deliveryDate).getTime() : Infinity;
        const dB = b.deliveryDate ? new Date(b.deliveryDate).getTime() : Infinity;
        return dA - dB;
      });
    }
    return result;
  }, [myOrders, orderSearch, sortMode, supplierMap]);

  const canCancel = (order: Order) => {
    if (order.status === "cancelled" || order.status === "delivered") return false;
    const delivery = new Date(order.deliveryDate);
    const now = new Date();
    return (delivery.getTime() - now.getTime()) / (1000 * 60 * 60) > 24;
  };

  const cancelOrder = async (id: string) => {
    setCancellingId(id);
    try {
      const res = await fetch(`${CANCEL_ORDER_SERVICE_URL}/cancelorder/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error("Failed to cancel");
      toast({ title: `Order ${id} cancelled successfully` });
      await fetchOrders();
    } catch {
      toast({ title: "Failed to cancel order", variant: "destructive" });
    } finally {
      setCancellingId(null);
    }
  };

  const resolvedItemName = (inventoryId: string) =>
    itemMap[Number(inventoryId)] ?? `Item #${inventoryId}`;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-foreground">Order History</h1>
        <div className="flex gap-2 flex-wrap items-center">
          <div className="relative min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by order ID or supplier..."
              value={orderSearch}
              onChange={(e) => setOrderSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex rounded-md border overflow-hidden text-sm">
            <button
              className={`px-3 py-2 transition-colors ${sortMode === "upcoming" ? "bg-primary text-primary-foreground" : "bg-background text-muted-foreground hover:bg-muted"}`}
              onClick={() => setSortMode("upcoming")}
            >
              Upcoming
            </button>
            <button
              className={`px-3 py-2 transition-colors border-l ${sortMode === "id" ? "bg-primary text-primary-foreground" : "bg-background text-muted-foreground hover:bg-muted"}`}
              onClick={() => setSortMode("id")}
            >
              Order ID
            </button>
          </div>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="text-sm text-muted-foreground p-6">Loading orders...</p>
          ) : (
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
                {filteredAndSorted.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">{order.id}</TableCell>
                    <TableCell className="text-sm">
                      {supplierMap[Number(order.supplierId)] ?? order.supplierId}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {order.items.length === 0 ? (
                        <span>—</span>
                      ) : order.items.length === 1 ? (
                        <span>{resolvedItemName(order.items[0].inventoryId)} ×{order.items[0].qty}</span>
                      ) : (
                        <button
                          onClick={() => setItemsModalOrder(order)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted hover:bg-muted/80 border text-xs font-medium transition-colors cursor-pointer"
                        >
                          <span>{resolvedItemName(order.items[0].inventoryId)} ×{order.items[0].qty}</span>
                          <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded-full text-[10px] font-semibold">
                            +{order.items.length - 1} more
                          </span>
                        </button>
                      )}
                    </TableCell>
                    <TableCell>{order.deliveryDate}</TableCell>
                    <TableCell>${order.totalAmount.toFixed(2)}</TableCell>
                    <TableCell><StatusBadge status={order.status} /></TableCell>
                    <TableCell className="text-right">
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
                      {orderSearch ? "No orders match your search" : "No orders yet"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Items detail modal */}
      <Dialog open={!!itemsModalOrder} onOpenChange={(v) => { if (!v) setItemsModalOrder(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Order #{itemsModalOrder?.id} — Items</DialogTitle>
            <p className="text-sm text-muted-foreground pt-1">
              Supplier: {supplierMap[Number(itemsModalOrder?.supplierId)] ?? itemsModalOrder?.supplierId}
            </p>
          </DialogHeader>
          <div className="divide-y max-h-72 overflow-y-auto -mx-6 px-6">
            {itemsModalOrder?.items.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-sm">{resolvedItemName(item.inventoryId)}</p>
                  <p className="text-xs text-muted-foreground">Qty: {item.qty}{item.unit ? ` ${item.unit}` : ""}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">${(item.pricePerUnit * item.qty).toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">${item.pricePerUnit.toFixed(2)} / unit</p>
                </div>
              </div>
            ))}
          </div>
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

/* ─── Buyer Dashboard (Router) ─── */
const BuyerDashboard = () => {
  const { user, role } = useAuth();
  if (!user || role !== "buyer") return <Navigate to="/buyer" />;

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