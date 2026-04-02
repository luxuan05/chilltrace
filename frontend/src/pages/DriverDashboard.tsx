import React, { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Truck, ClipboardList, MapPin, Thermometer, PlayCircle, RefreshCw } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";

// ── Service URLs ──────────────────────────────────────────────────────────────
const ORDER_SERVICE_URL           = "http://localhost:5002";
const INVENTORY_SERVICE_URL       = "http://localhost:5001";
const UPDATE_DELIVERY_SERVICE_URL = "http://localhost:5008";
const DELIVERY_API                = "https://personal-zsuepeep.outsystemscloud.com/IS213_ChillTrace/rest/DeliveryAPI";
const ACCEPT_DELIVERY_SERVICE_URL =
  import.meta.env.VITE_ACCEPT_DELIVERY_SERVICE_URL ?? "http://localhost:5007";

// ── Nav ───────────────────────────────────────────────────────────────────────
const navItems = [
  { label: "Available Jobs", path: "/driver",            icon: <ClipboardList className="h-4 w-4" /> },
  { label: "My Deliveries",  path: "/driver/deliveries", icon: <Truck className="h-4 w-4" /> },
];

// ── Types ─────────────────────────────────────────────────────────────────────
interface DeliveryJob {
  id: number;
  orderId: number;
  customerId: number;
  address: string;
  deliveryDate: string | null;
  deliveryStatus: string;
  driver?: number | null;
  initialTemperature?: number | null;
  finalTemperature?: number | null;
}

// ── In-memory cache ───────────────────────────────────────────────────────────
// Shared across AvailableJobs and MyDeliveries so navigating between tabs
// never triggers a second OutSystems round-trip.
let _cache: DeliveryJob[] | null = null;
let _cachePromise: Promise<DeliveryJob[]> | null = null; // deduplicate concurrent fetches

function patchCache(id: number, partial: Partial<DeliveryJob>) {
  if (_cache) {
    _cache = _cache.map((d) => (d.id === id ? { ...d, ...partial } : d));
  }
}

async function fetchAllDeliveries(force = false): Promise<DeliveryJob[]> {
  // Return cache immediately if available and not forcing a refresh
  if (!force && _cache) return _cache;

  // If a fetch is already in-flight, reuse it instead of sending a duplicate request
  if (!force && _cachePromise) return _cachePromise;

  _cachePromise = (async () => {
    const res = await fetch(`${DELIVERY_API}/delivery/`);
    if (!res.ok) throw new Error("Failed to fetch deliveries");
    const data = await res.json();
    const list: DeliveryJob[] = Array.isArray(data)
      ? data
      : (data.Deliveries ?? data.deliveries ?? []);
    _cache = list;
    _cachePromise = null;
    return list;
  })();

  return _cachePromise;
}

// Kick off a warm-up fetch as soon as this module loads so OutSystems is
// already awake by the time the user sees the dashboard.
fetchAllDeliveries();

// ── PUT delivery ──────────────────────────────────────────────────────────────
async function putDelivery(
  current: DeliveryJob,
  partial: Partial<DeliveryJob>
): Promise<Response> {
  const full = {
    address:            current.address            ?? "",
    deliveryDate:       current.deliveryDate       ?? null,
    deliveryStatus:     current.deliveryStatus     ?? "",
    driver:             current.driver             ?? 0,
    initialTemperature: current.initialTemperature ?? 0,
    finalTemperature:   current.finalTemperature   ?? 0,
    ...partial,
  };
  const res = await fetch(`${DELIVERY_API}/delivery/${current.id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(full),
  });
  // Keep cache in sync so subsequent reads don't need a re-fetch
  if (res.ok) patchCache(current.id, partial);
  return res;
}

// ── Temp range ────────────────────────────────────────────────────────────────
async function fetchTempRangeForOrder(
  orderId: number
): Promise<{ minTemp: number | null; maxTemp: number | null }> {
  const orderRes = await fetch(`${ORDER_SERVICE_URL}/orders/${orderId}`);
  if (!orderRes.ok) throw new Error(`Order ${orderId} not found`);
  const order = await orderRes.json();

  const items: { ItemID?: number; item_id?: number }[] =
    order.OrderItems ?? order.items ?? [];
  if (items.length === 0) return { minTemp: null, maxTemp: null };

  let minTemp: number | null = null;
  let maxTemp: number | null = null;

  await Promise.all(
    items.map(async (oi) => {
      const itemId = oi.ItemID ?? oi.item_id;
      if (!itemId) return;
      try {
        const invRes = await fetch(`${INVENTORY_SERVICE_URL}/inventory/items/${itemId}`);
        if (!invRes.ok) return;
        const inv = await invRes.json();
        const invMin: number | null = inv.MinTemperature ?? inv.min_temperature ?? null;
        const invMax: number | null = inv.MaxTemperature ?? inv.max_temperature ?? null;
        if (invMin !== null) minTemp = minTemp === null ? invMin : Math.max(minTemp, invMin);
        if (invMax !== null) maxTemp = maxTemp === null ? invMax : Math.min(maxTemp, invMax);
      } catch { /* ignore */ }
    })
  );

  return { minTemp, maxTemp };
}

// ── Badge helper ──────────────────────────────────────────────────────────────
function getStatusBadgeClass(status: string) {
  switch ((status ?? "").toUpperCase()) {
    case "DELIVERED":          return "bg-green-100 text-green-700 border-green-200";
    case "CANCELLED":          return "bg-red-100 text-red-700 border-red-200";
    case "FAILED_TEMP_BREACH": return "bg-orange-100 text-orange-700 border-orange-200";
    case "IN_TRANSIT":         return "bg-blue-100 text-blue-700 border-blue-200";
    case "SCHEDULED":          return "bg-purple-100 text-purple-700 border-purple-200";
    case "ACCEPTED":           return "bg-yellow-100 text-yellow-700 border-yellow-200";
    default:                   return "bg-muted text-muted-foreground";
  }
}

// ── Skeleton loaders ──────────────────────────────────────────────────────────
const CardSkeleton = () => (
  <div className="space-y-4">
    {[1, 2, 3].map((i) => (
      <Card key={i}>
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="flex gap-3">
              <div className="h-5 w-24 bg-muted rounded" />
              <div className="h-5 w-20 bg-muted rounded-full" />
            </div>
            <div className="h-4 w-48 bg-muted rounded" />
            <div className="h-4 w-32 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

const TableSkeleton = () => (
  <div className="animate-pulse space-y-3 p-6">
    {[1, 2, 3, 4].map((i) => (
      <div key={i} className="flex gap-4">
        <div className="h-4 w-16 bg-muted rounded" />
        <div className="h-4 w-16 bg-muted rounded" />
        <div className="h-4 w-40 bg-muted rounded" />
        <div className="h-4 w-24 bg-muted rounded" />
        <div className="h-4 w-20 bg-muted rounded-full" />
      </div>
    ))}
  </div>
);

// ── Available Jobs ────────────────────────────────────────────────────────────
const AvailableJobs = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [jobs, setJobs]             = useState<DeliveryJob[]>([]);
  const [loading, setLoading]       = useState(!_cache); // skip spinner if cache is already warm
  const [refreshing, setRefreshing] = useState(false);

  const loadJobs = useCallback(async (force = false) => {
    if (force) setRefreshing(true);
    else if (!_cache) setLoading(true);
    try {
      const all = await fetchAllDeliveries(force);
      setJobs(
        all.filter(
          (d) => !d.driver && (d.deliveryStatus ?? "").toUpperCase() === "SCHEDULED"
        )
      );
    } catch (err: unknown) {
      toast({
        title: "Failed to load available jobs",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast]);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  const acceptJob = async (job: DeliveryJob) => {
    if (!user) return;
    try {
      // IMPORTANT: DeliveryAPI uses deliveryId (= job.id), while order-service uses orderId (= job.orderId).
      // We accept via backend so it can update DeliveryAPI + order-service consistently.
      const res = await fetch(
        `${ACCEPT_DELIVERY_SERVICE_URL}/deliveries/${job.id}/accept`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ driverId: user.ID }),
        }
      );
      if (!res.ok) throw new Error(await res.text());

      // Keep frontend cache consistent with the external DeliveryAPI updates.
      patchCache(job.id, { driver: user.ID, deliveryStatus: "ACCEPTED" });
      // Remove from list immediately — cache is already patched by putDelivery
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      toast({ title: `Job accepted — Order #${job.orderId}` });
      navigate("/driver/deliveries");
    } catch (err: unknown) {
      toast({
        title: "Failed to accept job",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Available Delivery Jobs</h1>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          disabled={refreshing}
          onClick={() => loadJobs(true)}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {loading ? (
        <CardSkeleton />
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <Card key={job.id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-foreground">Order #{job.orderId}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${getStatusBadgeClass(job.deliveryStatus)}`}>
                        {job.deliveryStatus}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5 shrink-0" />
                      {job.address}
                    </div>
                    {job.deliveryDate && (
                      <p className="text-sm text-muted-foreground">
                        Delivery Date: {new Date(job.deliveryDate).toLocaleDateString()}
                      </p>
                    )}
                    <p className="text-sm text-muted-foreground">Customer ID: {job.customerId}</p>
                  </div>
                  <Button
                    onClick={() => acceptJob(job)}
                    className="gradient-frost text-accent-foreground hover:opacity-90 shrink-0"
                  >
                    Accept
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          {jobs.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                No available delivery jobs at the moment
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

// ── Temperature input cell ────────────────────────────────────────────────────
interface TempCellProps {
  job: DeliveryJob;
  onSave: (job: DeliveryJob, initTemp: number, finalTemp: number) => Promise<void>;
}

const TemperatureCell = ({ job, onSave }: TempCellProps) => {
  const status = (job.deliveryStatus ?? "").toUpperCase();

  const [initTemp,  setInitTemp]  = useState(
    job.initialTemperature != null ? String(job.initialTemperature) : ""
  );
  const [finalTemp, setFinalTemp] = useState(
    job.finalTemperature != null ? String(job.finalTemperature) : ""
  );
  const [saving, setSaving] = useState(false);

  const isFinal = ["DELIVERED", "CANCELLED", "FAILED_TEMP_BREACH"].includes(status);
  if (isFinal) {
    return (
      <div className="text-xs text-muted-foreground space-y-0.5">
        <div>Init: {job.initialTemperature ?? "—"}°C</div>
        <div>Final: {job.finalTemperature ?? "—"}°C</div>
      </div>
    );
  }

  if (status !== "IN_TRANSIT") {
    return (
      <span className="text-xs text-muted-foreground italic">
        Available once In Transit
      </span>
    );
  }

  const sanitiseTemp = (val: string): number => {
    const n = parseFloat(val);
    return n === 0 ? 0.01 : n;
  };

  const handleSave = async () => {
    if (initTemp === "" || finalTemp === "") return;
    setSaving(true);
    await onSave(job, sanitiseTemp(initTemp), sanitiseTemp(finalTemp));
    setSaving(false);
  };

  return (
    <div className="flex flex-col gap-1.5 min-w-[150px]">
      <div className="relative">
        <Thermometer className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          type="number"
          placeholder="Initial °C"
          value={initTemp}
          onChange={(e) => setInitTemp(e.target.value)}
          className="pl-7 h-8 text-sm"
          disabled={saving}
        />
      </div>
      <div className="relative">
        <Thermometer className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-blue-400" />
        <Input
          type="number"
          placeholder="Final °C"
          value={finalTemp}
          onChange={(e) => setFinalTemp(e.target.value)}
          className="pl-7 h-8 text-sm"
          disabled={saving}
        />
      </div>
      {(initTemp === "0" || finalTemp === "0") && (
        <p className="text-xs text-amber-500">
          Note: 0°C is not supported, will be stored as 0.1°C
        </p>
      )}
      <Button
        size="sm"
        className="h-7 text-xs"
        disabled={saving || initTemp === "" || finalTemp === ""}
        onClick={handleSave}
      >
        {saving ? "Checking..." : "Submit"}
      </Button>
    </div>
  );
};

// ── Start Delivery button cell ────────────────────────────────────────────────
interface StartDeliveryCellProps {
  job: DeliveryJob;
  onStart: (job: DeliveryJob) => Promise<void>;
}

const StartDeliveryCell = ({ job, onStart }: StartDeliveryCellProps) => {
  const status = (job.deliveryStatus ?? "").toUpperCase();
  const [starting, setStarting] = useState(false);

  if (status !== "ACCEPTED") return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const deliveryDate = job.deliveryDate ? new Date(job.deliveryDate) : null;
  if (deliveryDate) deliveryDate.setHours(0, 0, 0, 0);

  const canStart = deliveryDate ? today >= deliveryDate : false;

  const handleStart = async () => {
    setStarting(true);
    await onStart(job);
    setStarting(false);
  };

  return (
    <Button
      size="sm"
      variant="outline"
      className="h-7 text-xs gap-1.5 border-blue-300 text-blue-600 hover:bg-blue-50"
      disabled={starting || !canStart}
      onClick={handleStart}
      title={!canStart ? `Delivery date is ${job.deliveryDate}` : "Start this delivery"}
    >
      <PlayCircle className="h-3.5 w-3.5" />
      {starting
        ? "Starting..."
        : canStart
          ? "Start Delivery"
          : `Starts ${job.deliveryDate ? new Date(job.deliveryDate).toLocaleDateString() : "—"}`}
    </Button>
  );
};

// ── My Deliveries ─────────────────────────────────────────────────────────────
const MyDeliveries = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [jobs, setJobs]             = useState<DeliveryJob[]>([]);
  const [loading, setLoading]       = useState(!_cache); // skip spinner if cache is already warm
  const [refreshing, setRefreshing] = useState(false);

  const loadJobs = useCallback(async (force = false) => {
    if (force) setRefreshing(true);
    else if (!_cache) setLoading(true);
    try {
      const all = await fetchAllDeliveries(force);
      setJobs(all.filter((d) => d.driver === user?.ID));
    } catch (err: unknown) {
      toast({
        title: "Failed to load deliveries",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast, user?.ID]);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  // ── ACCEPTED → IN_TRANSIT ───────────────────────────────────────────────
  const handleStartDelivery = async (job: DeliveryJob) => {
    try {
      const res = await putDelivery(job, { deliveryStatus: "IN_TRANSIT" });
      if (!res.ok) throw new Error(await res.text());
      // Update local state directly — cache already patched by putDelivery
      setJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, deliveryStatus: "IN_TRANSIT" } : j))
      );
      toast({ title: `Order #${job.orderId} is now In Transit` });
    } catch (err: unknown) {
      toast({
        title: "Failed to start delivery",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  // ── Temperature submit → DELIVERED or CANCELLED ─────────────────────────
  const handleTemperatureSave = async (
    job: DeliveryJob,
    initTemp: number,
    finalTemp: number
  ) => {
    try {
      const { minTemp, maxTemp } = await fetchTempRangeForOrder(job.orderId);

      const breached =
        (minTemp !== null && finalTemp < minTemp) ||
        (maxTemp !== null && finalTemp > maxTemp);

      const newDeliveryStatus = breached ? "CANCELLED" : "DELIVERED";

      const tempRes = await putDelivery(job, {
        initialTemperature: initTemp,
        finalTemperature:   finalTemp,
        deliveryStatus:     newDeliveryStatus,
      });
      if (!tempRes.ok) throw new Error("Failed to save temperatures");

      const statusRes = await fetch(
        `${UPDATE_DELIVERY_SERVICE_URL}/delivery_job/${job.orderId}/status`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            status:      newDeliveryStatus,
            customer_id: job.customerId,
            ...(breached ? { reason: "temperature_breach" } : {}),
          }),
        }
      );
      if (!statusRes.ok) throw new Error("Failed to update delivery status");

      // Update local state directly — cache already patched by putDelivery
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id
            ? { ...j, initialTemperature: initTemp, finalTemperature: finalTemp, deliveryStatus: newDeliveryStatus }
            : j
        )
      );

      if (breached) {
        toast({
          title: `⚠️ Temperature breach — Order #${job.orderId} cancelled`,
          description: `Final ${finalTemp}°C is outside allowed range (${minTemp ?? "—"}°C – ${maxTemp ?? "—"}°C).`,
          variant: "destructive",
        });
      } else {
        toast({
          title: `✅ Order #${job.orderId} delivered successfully`,
          description: `Final ${finalTemp}°C is within range.`,
        });
      }
    } catch (err: unknown) {
      toast({
        title: "Error processing temperature",
        description: (err instanceof Error ? err.message : String(err)) ?? "Unknown error",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">My Deliveries</h1>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          disabled={refreshing}
          onClick={() => loadJobs(true)}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </div>
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order ID</TableHead>
                  <TableHead>Customer ID</TableHead>
                  <TableHead>Address</TableHead>
                  <TableHead>Delivery Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Temperature (Init / Final)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell className="font-medium">#{job.orderId}</TableCell>
                    <TableCell>{job.customerId}</TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                      {job.address}
                    </TableCell>
                    <TableCell className="text-sm">
                      {job.deliveryDate
                        ? new Date(job.deliveryDate).toLocaleDateString()
                        : "—"}
                    </TableCell>
                    <TableCell>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${getStatusBadgeClass(job.deliveryStatus)}`}>
                        {job.deliveryStatus.replace(/_/g, " ")}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StartDeliveryCell job={job} onStart={handleStartDelivery} />
                    </TableCell>
                    <TableCell>
                      <TemperatureCell job={job} onSave={handleTemperatureSave} />
                    </TableCell>
                  </TableRow>
                ))}

                {jobs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
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

// ── Driver Dashboard ──────────────────────────────────────────────────────────
const DriverDashboard = () => {
  const { user, role } = useAuth();
  if (!user || role !== "driver") return <Navigate to="/login" />;

  return (
    <DashboardLayout navItems={navItems} title="Driver Portal">
      <Routes>
        <Route index element={<AvailableJobs />} />
        <Route path="deliveries" element={<MyDeliveries />} />
      </Routes>
    </DashboardLayout>
  );
};

export default DriverDashboard;
