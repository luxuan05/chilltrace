import { OrderStatus } from "@/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusConfig: Record<OrderStatus, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-warning/15 text-warning border-warning/30" },
  confirmed: { label: "Confirmed", className: "bg-info/15 text-info border-info/30" },
  processing: { label: "Processing", className: "bg-accent/15 text-accent border-accent/30" },
  in_transit: { label: "In Transit", className: "bg-primary/15 text-primary border-primary/30" },
  delivered: { label: "Delivered", className: "bg-success/15 text-success border-success/30" },
  cancelled: { label: "Cancelled", className: "bg-destructive/15 text-destructive border-destructive/30" },
};

const StatusBadge = ({ status }: { status: OrderStatus }) => {
  const config = statusConfig[status];
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", config.className)}>
      {config.label}
    </Badge>
  );
};

export default StatusBadge;
