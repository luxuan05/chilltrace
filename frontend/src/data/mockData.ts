import { InventoryItem, Order, User } from "@/types";

export const mockUsers: User[] = [
  { id: "b1", name: "Sarah Chen", email: "sarah@freshmart.com", role: "buyer", company: "FreshMart" },
  { id: "s1", name: "James Wilson", email: "james@arcticfoods.com", role: "supplier", company: "Arctic Foods Co." },
  { id: "d1", name: "Mike Rodriguez", email: "mike@coldhaul.com", role: "driver", company: "ColdHaul Logistics" },
];

export const mockInventory: InventoryItem[] = [
  { id: "inv1", name: "Frozen Atlantic Salmon", category: "Seafood", unit: "kg", pricePerUnit: 18.5, stockLevel: 500, minTemp: -25, maxTemp: -18, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv2", name: "Fresh Whole Milk", category: "Dairy", unit: "litre", pricePerUnit: 2.4, stockLevel: 1200, minTemp: 2, maxTemp: 6, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv3", name: "Organic Chicken Breast", category: "Poultry", unit: "kg", pricePerUnit: 12.0, stockLevel: 300, minTemp: -2, maxTemp: 4, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv4", name: "Vaccine Batch V-200", category: "Pharma", unit: "vial", pricePerUnit: 45.0, stockLevel: 800, minTemp: -70, maxTemp: -60, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv5", name: "Ice Cream Tubs (Vanilla)", category: "Frozen Desserts", unit: "unit", pricePerUnit: 5.5, stockLevel: 2000, minTemp: -25, maxTemp: -18, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv6", name: "Fresh Strawberries", category: "Produce", unit: "kg", pricePerUnit: 8.0, stockLevel: 150, minTemp: 1, maxTemp: 4, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv7", name: "Frozen Shrimp (Peeled)", category: "Seafood", unit: "kg", pricePerUnit: 22.0, stockLevel: 400, minTemp: -25, maxTemp: -18, supplierId: "s1", supplierName: "Arctic Foods Co." },
  { id: "inv8", name: "Greek Yogurt", category: "Dairy", unit: "unit", pricePerUnit: 3.2, stockLevel: 900, minTemp: 2, maxTemp: 6, supplierId: "s1", supplierName: "Arctic Foods Co." },
];

export const mockOrders: Order[] = [
  {
    id: "ORD-001",
    buyerId: "b1",
    buyerName: "Sarah Chen",
    supplierId: "s1",
    supplierName: "Arctic Foods Co.",
    driverId: "d1",
    driverName: "Mike Rodriguez",
    items: [
      { inventoryId: "inv1", name: "Frozen Atlantic Salmon", qty: 50, unit: "kg", pricePerUnit: 18.5 },
      { inventoryId: "inv2", name: "Fresh Whole Milk", qty: 200, unit: "litre", pricePerUnit: 2.4 },
    ],
    totalAmount: 1405,
    deliveryAddress: "42 Market Street, Downtown, NYC 10001",
    deliveryDate: "2026-02-25",
    status: "in_transit",
    paymentMethod: "Bank Transfer",
    createdAt: "2026-02-18T10:00:00Z",
    updatedAt: "2026-02-20T08:30:00Z",
  },
  {
    id: "ORD-002",
    buyerId: "b1",
    buyerName: "Sarah Chen",
    supplierId: "s1",
    supplierName: "Arctic Foods Co.",
    items: [
      { inventoryId: "inv3", name: "Organic Chicken Breast", qty: 100, unit: "kg", pricePerUnit: 12.0 },
    ],
    totalAmount: 1200,
    deliveryAddress: "42 Market Street, Downtown, NYC 10001",
    deliveryDate: "2026-02-28",
    status: "pending",
    paymentMethod: "Credit Card",
    createdAt: "2026-02-19T14:00:00Z",
    updatedAt: "2026-02-19T14:00:00Z",
  },
  {
    id: "ORD-003",
    buyerId: "b1",
    buyerName: "Sarah Chen",
    supplierId: "s1",
    supplierName: "Arctic Foods Co.",
    driverId: "d1",
    driverName: "Mike Rodriguez",
    items: [
      { inventoryId: "inv5", name: "Ice Cream Tubs (Vanilla)", qty: 500, unit: "unit", pricePerUnit: 5.5 },
    ],
    totalAmount: 2750,
    deliveryAddress: "88 Riverside Ave, Brooklyn, NYC 11201",
    deliveryDate: "2026-02-22",
    status: "delivered",
    paymentMethod: "Bank Transfer",
    createdAt: "2026-02-15T09:00:00Z",
    updatedAt: "2026-02-22T16:00:00Z",
  },
];
