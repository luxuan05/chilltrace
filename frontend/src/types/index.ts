export type UserRole = "buyer" | "supplier" | "driver";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
  company?: string;
}

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "processing"
  | "in_transit"
  | "delivered"
  | "cancelled";

export interface OrderItem {
  inventoryId: string;
  name: string;
  qty: number;
  unit: string;
  pricePerUnit: number;
}

export interface Order {
  id: string;
  buyerId: string;
  buyerName: string;
  supplierId: string;
  supplierName: string;
  driverId?: string;
  driverName?: string;
  items: OrderItem[];
  totalAmount: number;
  deliveryAddress: string;
  deliveryDate: string;
  status: OrderStatus;
  paymentMethod: string;
  createdAt: string;
  updatedAt: string;
}

export interface InventoryItem {
  id: string;
  name: string;
  category: string;
  unit: string;
  pricePerUnit: number;
  stockLevel: number;
  minTemp: number;
  maxTemp: number;
  supplierId: string;
  supplierName: string;
}
