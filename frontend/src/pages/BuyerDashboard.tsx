import React, { useState, useEffect, useRef } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ShoppingCart, ClipboardList, Package, Plus } from "lucide-react";
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
import { loadStripe, Stripe, StripeCardElement } from "@stripe/stripe-js";

const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
const stripePromise = stripePublishableKey
  ? loadStripe(stripePublishableKey)
  : null;

const navItems = [
  { label: "Place Order", path: "/buyer", icon: <Plus className="h-4 w-4" /> },
  {
    label: "Order History",
    path: "/buyer/orders",
    icon: <ClipboardList className="h-4 w-4" />,
  },
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

interface PendingOrderSnapshot {
  orderId: string;
  items: OrderItem[];
  totalAmount: number;
  deliveryAddress: string;
  deliveryDate: string;
  supplierId: string;
  supplierName: string;
  paymentMethod: string;
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
  const [payment, setPayment] = useState("Credit Card");
  const [placingOrder, setPlacingOrder] = useState(false);
  const [isPaying, setIsPaying] = useState(false);
  const [paymentIntentSecret, setPaymentIntentSecret] = useState("");
  const [pendingOrderSnapshot, setPendingOrderSnapshot] =
    useState<PendingOrderSnapshot | null>(null);

  const [cardName, setCardName] = useState("");

  const stripeRef = useRef<Stripe | null>(null);
  const cardElementRef = useRef<StripeCardElement | null>(null);
  const cardMountRef = useRef<HTMLDivElement | null>(null);

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
  }, [toast]);

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
  }, [selectedSupplierId, toast]);

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
    (s) => s.ID === Number(selectedSupplierId),
  );
  const isCardPayment = payment === "Credit Card" || payment === "Debit Card";

  useEffect(() => {
    let cancelled = false;

    const initStripeCardElement = async () => {
      if (!isCardPayment) {
        if (cardElementRef.current) {
          cardElementRef.current.destroy();
          cardElementRef.current = null;
        }
        return;
      }

      // Card container renders only when cart section is visible.
      if (!cardMountRef.current) return;

      if (!stripePromise) {
        toast({
          title: "Stripe key missing",
          description:
            "Set VITE_STRIPE_PUBLISHABLE_KEY in frontend environment.",
          variant: "destructive",
        });
        return;
      }

      const stripe = await stripePromise;
      if (!stripe || cancelled) return;

      stripeRef.current = stripe;

      if (!cardElementRef.current && cardMountRef.current) {
        const elements = stripe.elements();
        const card = elements.create("card", {
          hidePostalCode: true,
        });
        card.mount(cardMountRef.current);
        cardElementRef.current = card;
      }
    };

    initStripeCardElement();

    return () => {
      cancelled = true;
    };
  }, [isCardPayment, toast, cartItems.length]);

  const payForOrder = async () => {
    if (!pendingOrderSnapshot || !paymentIntentSecret) {
      toast({
        title: "Create order first",
        description: "Click Place Order to receive Stripe payment intent.",
        variant: "destructive",
      });
      return;
    }

    if (
      pendingOrderSnapshot.paymentMethod === "Credit Card" ||
      pendingOrderSnapshot.paymentMethod === "Debit Card"
    ) {
      if (!cardName || !cardElementRef.current || !stripeRef.current) {
        toast({
          title: "Please fill all card details",
          variant: "destructive",
        });
        return;
      }
    }

    try {
      setIsPaying(true);

      if (
        pendingOrderSnapshot.paymentMethod === "Credit Card" ||
        pendingOrderSnapshot.paymentMethod === "Debit Card"
      ) {
        const result = await stripeRef.current!.confirmCardPayment(
          paymentIntentSecret,
          {
            payment_method: {
              card: cardElementRef.current!,
              billing_details: {
                name: cardName,
              },
            },
          },
        );

        if (result.error) {
          toast({
            title: "Payment failed",
            description: result.error.message || "Card confirmation failed",
            variant: "destructive",
          });
          return;
        }

        if (result.paymentIntent?.status !== "succeeded") {
          toast({
            title: "Payment not completed",
            description: `Stripe status: ${result.paymentIntent?.status || "unknown"}`,
            variant: "destructive",
          });
          return;
        }

        console.log("Stripe payment result:", result.paymentIntent);

        const webhookForwardRes = await fetch(
          "http://localhost:5004/payment/confirm-intent",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              payment_intent_id: result.paymentIntent.id,
            }),
          },
        );

        const webhookForwardResult = await webhookForwardRes
          .json()
          .catch(() => ({}));
        console.log("Forward to payment webhook flow:", webhookForwardResult);

        if (!webhookForwardRes.ok) {
          toast({
            title: "Backend flow continuation failed",
            description:
              webhookForwardResult?.error ||
              "Payment succeeded but backend webhook flow failed",
            variant: "destructive",
          });
          return;
        }
      }

      const newOrder: Order = {
        id: pendingOrderSnapshot.orderId,
        buyerId: String(user!.ID),
        buyerName: user!.CompanyName || user!.Name || "",
        supplierId: pendingOrderSnapshot.supplierId,
        supplierName: pendingOrderSnapshot.supplierName,
        items: pendingOrderSnapshot.items,
        totalAmount: pendingOrderSnapshot.totalAmount,
        deliveryAddress: pendingOrderSnapshot.deliveryAddress,
        deliveryDate: pendingOrderSnapshot.deliveryDate,
        status: "pending",
        paymentMethod: pendingOrderSnapshot.paymentMethod,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      setOrders((prev) => [...prev, newOrder]);
      setCart({});
      setAddress("");
      setDeliveryDate("");
      setCardName("");
      setPendingOrderSnapshot(null);
      setPaymentIntentSecret("");
      toast({ title: `Payment successful for ${newOrder.id}` });
    } catch {
      toast({
        title: "Payment failed",
        description: "Unable to confirm payment with Stripe.",
        variant: "destructive",
      });
    } finally {
      setIsPaying(false);
    }
  };

  const placeOrder = async () => {
    if (!cartItems.length || !address || !deliveryDate || !selectedSupplierId) {
      toast({ title: "Please fill all order details", variant: "destructive" });
      return;
    }

    const payload = {
      CustomerID: Number(user!.ID),
      OrderItems: cartItems.map((i) => ({
        ItemID: i.item_id,
        Quantity: i.qty,
      })),
      SupplierID: Number(selectedSupplierId),
      Address: address,
      ScheduledDate: deliveryDate,
    };

    try {
      setPlacingOrder(true);

      const res = await fetch("http://localhost:5006/placeorder", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = await res.json().catch(() => ({}));
      console.log("Place order response:", result);

      if (!res.ok) {
        toast({
          title: "Failed to place order",
          description: result?.message || result?.Error || "Please try again",
          variant: "destructive",
        });
        return;
      }

      const orderItems: OrderItem[] = cartItems.map((i) => ({
        inventoryId: String(i.item_id),
        name: i.name,
        qty: i.qty,
        unit: i.unit,
        pricePerUnit: i.price,
      }));

      const clientSecret = result?.result?.data?.client_secret;
      const orderIdFromBackend = result?.result?.data?.OrderID;

      if (!clientSecret) {
        toast({
          title: "Missing payment intent",
          description:
            "Place order service did not return Stripe client secret.",
          variant: "destructive",
        });
        return;
      }

      const generatedOrderId = orderIdFromBackend
        ? `ORD-${String(orderIdFromBackend).padStart(3, "0")}`
        : `ORD-${String(orders.length + 1).padStart(3, "0")}`;

      setPendingOrderSnapshot({
        orderId: generatedOrderId,
        items: orderItems,
        totalAmount: total,
        deliveryAddress: address,
        deliveryDate,
        supplierId: String(selectedSupplierId),
        supplierName: selectedSupplier?.CompanyName || "",
        paymentMethod: payment,
      });
      setPaymentIntentSecret(clientSecret);

      toast({ title: "Order created. Click Pay to complete Stripe payment." });
    } catch {
      toast({
        title: "Failed to place order service",
        description:
          "Could not reach place-order API at http://localhost:5006/placeorder",
        variant: "destructive",
      });
    } finally {
      setPlacingOrder(false);
    }
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
            <p className="text-sm text-muted-foreground">
              Loading suppliers...
            </p>
          ) : (
            <Select
              value={selectedSupplierId}
              onValueChange={setSelectedSupplierId}
            >
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
              <p className="text-sm text-muted-foreground">
                Loading inventory...
              </p>
            ) : inventory.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No items available from this supplier.
              </p>
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
                      <TableCell>
                        {item.quantity_available} {item.unit}
                      </TableCell>
                      <TableCell>
                        ${item.price.toFixed(2)}/{item.unit}
                      </TableCell>
                      <TableCell className="text-right">
                        {cart[item.item_id] ? (
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                updateQty(item.item_id, cart[item.item_id] - 1)
                              }
                            >
                              −
                            </Button>
                            <span className="w-8 text-center text-sm font-medium">
                              {cart[item.item_id]}
                            </span>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                updateQty(item.item_id, cart[item.item_id] + 1)
                              }
                            >
                              +
                            </Button>
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => addToCart(item.item_id)}
                          >
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
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <ShoppingCart className="h-5 w-5 text-accent" /> Order Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-muted rounded-lg p-4 space-y-2">
                {cartItems.map((item) => (
                  <div
                    key={item.item_id}
                    className="flex justify-between text-sm"
                  >
                    <span>
                      {item.name} × {item.qty} {item.unit}
                    </span>
                    <span className="font-medium">
                      ${(item.qty * item.price).toFixed(2)}
                    </span>
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

              <Button
                onClick={placeOrder}
                disabled={placingOrder}
                className="gradient-frost text-accent-foreground hover:opacity-90"
              >
                {placingOrder
                  ? "Placing..."
                  : `Place Order - $${total.toFixed(2)}`}
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base">{payment}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isCardPayment ? (
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <Label>Cardholder Name</Label>
                    <Input
                      value={cardName}
                      onChange={(e) => setCardName(e.target.value)}
                      placeholder="Name on card"
                      className="mt-1"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Label>Card Number</Label>
                    <div
                      ref={cardMountRef}
                      className="mt-1 rounded-md border border-input bg-background px-3 py-3"
                    />
                    <p className="mt-2 text-xs text-muted-foreground">
                      Card number, expiry, and CVC are securely collected by
                      Stripe.
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No additional fields required for {payment}.
                </p>
              )}

              <Button
                onClick={payForOrder}
                disabled={isPaying || !paymentIntentSecret}
                className="gradient-frost text-accent-foreground hover:opacity-90"
              >
                {isPaying
                  ? "Paying..."
                  : paymentIntentSecret
                    ? `Pay - $${total.toFixed(2)}`
                    : "Pay (create order first)"}
              </Button>
            </CardContent>
          </Card>
        </>
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
    if (order.status === "cancelled" || order.status === "delivered")
      return false;
    const delivery = new Date(order.deliveryDate);
    const now = new Date();
    const hoursUntilDelivery =
      (delivery.getTime() - now.getTime()) / (1000 * 60 * 60);
    return hoursUntilDelivery > 24;
  };

  const cancelOrder = (id: string) => {
    setOrders((prev) =>
      prev.map((o) =>
        o.id === id
          ? {
              ...o,
              status: "cancelled" as const,
              updatedAt: new Date().toISOString(),
            }
          : o,
      ),
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
                  <TableCell className="text-sm">
                    {order.supplierName}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {order.items.map((i) => i.name).join(", ")}
                  </TableCell>
                  <TableCell>{order.deliveryDate}</TableCell>
                  <TableCell>${order.totalAmount.toFixed(2)}</TableCell>
                  <TableCell>
                    <StatusBadge status={order.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    {canCancel(order) && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => cancelOrder(order.id)}
                      >
                        Cancel
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {myOrders.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center text-muted-foreground py-8"
                  >
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
