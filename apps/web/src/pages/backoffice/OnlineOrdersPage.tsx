import BarcodeScanner from "../../components/backoffice/BarcodeScanner";
import { useState } from "react";


type OrderStatus =
    | "New Orders"
    | "Picking"
    | "Packing"
    | "Ready to Dispatch";

type OnlineOrder = {
    id: string;
    customer: string;
    items: string[];
    total: number;
    status: OrderStatus;
};

type DemoProduct = {
    id: string;
    name: string;
    barcode: string;
    category: string;
};

const demoProducts: DemoProduct[] = [
    {
        id: "PRD-001",
        name: "Silk Saree",
        barcode: "FOS-PRD-001",
        category: "Sarees",
    },
    {
        id: "PRD-002",
        name: "Anarkali Suit",
        barcode: "FOS-PRD-002",
        category: "Suits",
    },
    {
        id: "PRD-003",
        name: "Kids Kurta Set",
        barcode: "FOS-PRD-003",
        category: "Kids",
    },

    {
        id: "PRD-004",
        name: "Blouse Piece",
        barcode: "FOS-PRD-004",
        category: "Blouse",
    },
    {
        id: "PRD-005",
        name: "Leggings",
        barcode: "FOS-PRD-005",
        category: "Kids",
    },
];

const initialOrders: OnlineOrder[] = [
    {
        id: "ORD-1001",
        customer: "Priya Sharma",
        items: ["Silk Saree", "Blouse Piece"],
        total: 2499,
        status: "New Orders",
    },
    {
        id: "ORD-1002",
        customer: "Neha Patel",
        items: ["Anarkali Suit"],
        total: 1899,
        status: "Picking",
    },
    {
        id: "ORD-1003",
        customer: "Riya Mehta",
        items: ["Kids Kurta Set", "Leggings"],
        total: 1299,
        status: "Packing",
    },
];

const tabs: OrderStatus[] = [
    "New Orders",
    "Picking",
    "Packing",
    "Ready to Dispatch",
];

export default function OnlineOrdersPage() {

    const [orders, setOrders] = useState(initialOrders);
    const [activeTab, setActiveTab] =
        useState<OrderStatus>("New Orders");

    const [scannedCodes, setScannedCodes] =
        useState<Record<string, string>>({});
    const [verifiedItems, setVerifiedItems] =
        useState<Record<string, string[]>>({});

    const filteredOrders = orders.filter(
        (order) => order.status === activeTab
    );


    function getPackingProgress(order: OnlineOrder) {
        const verified = verifiedItems[order.id] ?? [];
        const total = order.items.length;

        const verifiedCount = order.items.filter(
            (item) => verified.includes(item)
        ).length;

        return {
            verifiedCount,
            total,
            percentage: total === 0
                ? 0
                : Math.round((verifiedCount / total) * 100),
        };
    }

    function updateStatus(orderId: string, status: OrderStatus) {
        setOrders((currentOrders) =>
            currentOrders.map((order) =>
                order.id === orderId ? { ...order, status } : order
            )
        );
    }

    function nextStatus(status: OrderStatus): OrderStatus | null {
        const index = tabs.indexOf(status);
        return index < tabs.length - 1 ? tabs[index + 1] : null;
    }

    return (
        <div className="min-h-screen bg-[#F7F7F7] p-4 text-[#111111] sm:p-6">
            <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <p className="text-sm text-gray-500">
                        Backoffice / Orders
                    </p>
                    <h1 className="mt-1 text-2xl font-semibold">
                        Online Orders
                    </h1>
                    <p className="mt-1 text-sm text-gray-500">
                        Pick, pack and prepare customer orders for dispatch.
                    </p>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white px-4 py-3">
                    <p className="text-xs text-gray-500">Total Orders</p>
                    <p className="text-2xl font-semibold">{orders.length}</p>
                </div>
            </div>


            {/* Order status summary */}
            <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
                {tabs.map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`rounded-xl border p-4 text-left transition ${activeTab === tab
                            ? "border-[#111111] bg-[#111111] text-white"
                            : "border-gray-200 bg-white hover:border-gray-400"
                            }`}
                    >
                        <p className="text-sm">{tab}</p>
                        <p className="mt-2 text-2xl font-semibold">
                            {orders.filter((order) => order.status === tab).length}
                        </p>
                    </button>
                ))}
            </div>

            {/* Order status tabs */}
            <div className="mb-4 flex flex-wrap gap-2">
                {tabs.map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`rounded-full px-4 py-2 text-sm ${activeTab === tab
                            ? "bg-[#111111] text-white"
                            : "border border-gray-200 bg-white text-gray-700"
                            }`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {/* Orders list */}

            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
                <div className="border-b border-gray-200 p-4">
                    <h2 className="font-semibold">{activeTab}</h2>
                    <p className="mt-1 text-sm text-gray-500">
                        {filteredOrders.length} order(s) in this stage
                    </p>
                </div>

                {filteredOrders.length === 0 ? (
                    <div className="p-10 text-center">
                        <p className="font-medium">
                            No orders in this stage
                        </p>
                        <p className="mt-1 text-sm text-gray-500">
                            Orders will appear here when their status changes.
                        </p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-200">
                        {filteredOrders.map((order) => (
                            <div
                                key={order.id}
                                className="flex flex-col gap-4 p-4 sm:p-5"
                            >
                                <div>
                                    <p className="font-semibold">{order.id}</p>

                                    {(() => {
                                        const progress = getPackingProgress(order);

                                        return (
                                            <div className="mt-3 max-w-md">
                                                <div className="mb-2 flex items-center justify-between text-sm">
                                                    <span className="font-medium text-gray-700">
                                                        Packing Progress
                                                    </span>
                                                    <span className="text-gray-500">
                                                        {progress.verifiedCount}/{progress.total} products · {progress.percentage}%
                                                    </span>
                                                </div>

                                                <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                                                    <div
                                                        className="h-full rounded-full bg-green-600 transition-all duration-300"
                                                        style={{ width: `${progress.percentage}%` }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })()}
                                    <p className="mt-1 text-sm text-gray-600">
                                        Customer: {order.customer}
                                    </p>


                                    <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
                                        <h3 className="mb-3 text-base font-semibold">
                                            Customer ne ye products order kiye hain
                                        </h3>

                                        <div className="space-y-3">

                                            {order.items.map((item, index) => {
                                                const product = demoProducts.find(
                                                    (p) => p.name === item
                                                );

                                                const isVerified = (
                                                    verifiedItems[order.id] ?? []
                                                ).includes(item);

                                                return (
                                                    <div
                                                        key={`${item}-${index}`}
                                                        className="flex items-center justify-between gap-3 rounded-lg bg-gray-50 p-3"
                                                    >
                                                        <div>
                                                            <p className="font-medium">{item}</p>

                                                            <p className="mt-1 text-xs text-gray-500">
                                                                {product
                                                                    ? `Barcode: ${product.barcode}`
                                                                    : "Barcode abhi product list mein add nahi hai"}
                                                            </p>
                                                        </div>

                                                        <div className="flex shrink-0 flex-col items-end gap-2">
                                                            <span className="rounded-md border border-gray-200 bg-white px-3 py-1 text-sm">
                                                                Qty: 1
                                                            </span>

                                                            <span
                                                                className={`rounded-md px-3 py-1 text-xs font-semibold ${isVerified
                                                                    ? "bg-green-100 text-green-700"
                                                                    : "bg-yellow-100 text-yellow-700"
                                                                    }`}
                                                            >
                                                                {isVerified ? "✓ Verified" : "Pending"}
                                                            </span>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        <div className="mt-4 border-t border-gray-200 pt-3">
                                            <p className="text-sm text-gray-500">Customer</p>
                                            <p className="font-medium">{order.customer}</p>

                                            <p className="mt-3 text-sm text-gray-500">Order Total</p>
                                            <p className="text-lg font-semibold">
                                                ₹{order.total.toLocaleString("en-IN")}
                                            </p>
                                        </div>
                                    </div>

                                    <p className="mt-3 font-medium">
                                        ₹{order.total.toLocaleString("en-IN")}
                                    </p>
                                </div>

                                {/* Per-order barcode scanner */}
                                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                                    <h3 className="mb-3 font-semibold">
                                        Verify Products — {order.id}
                                    </h3>



                                    <BarcodeScanner
                                        onScan={(code) => {
                                            setScannedCodes((current) => ({
                                                ...current,
                                                [order.id]: code,
                                            }));

                                            const product = demoProducts.find(
                                                (item) =>
                                                    item.barcode.toLowerCase() ===
                                                    code.trim().toLowerCase()
                                            );

                                            if (!product || !order.items.includes(product.name)) {
                                                return;
                                            }

                                            const updatedVerifiedItems = [
                                                ...new Set([
                                                    ...(verifiedItems[order.id] ?? []),
                                                    product.name,
                                                ]),
                                            ];

                                            setVerifiedItems((current) => ({
                                                ...current,
                                                [order.id]: updatedVerifiedItems,
                                            }));

                                            const allProductsVerified = order.items.every(
                                                (item) => updatedVerifiedItems.includes(item)
                                            );

                                            if (allProductsVerified) {
                                                updateStatus(order.id, "Ready to Dispatch");
                                            }
                                        }}
                                    />

                                    {scannedCodes[order.id] && (() => {
                                        const code = scannedCodes[order.id].trim();

                                        const product = demoProducts.find(
                                            (item) =>
                                                item.barcode.toLowerCase() ===
                                                code.toLowerCase()
                                        );

                                        if (!product) {
                                            return (
                                                <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                                                    <p className="font-semibold">
                                                        Product Not Found
                                                    </p>
                                                    <p>Barcode: {code}</p>
                                                </div>
                                            );
                                        }

                                        const belongsToOrder =
                                            order.items.includes(product.name);

                                        return (
                                            <div
                                                className={`mt-3 rounded-lg p-3 text-sm ${belongsToOrder
                                                    ? "bg-green-50 text-green-700"
                                                    : "bg-red-50 text-red-700"
                                                    }`}
                                            >
                                                <p className="font-semibold">
                                                    {belongsToOrder
                                                        ? "✓ Product Verified"
                                                        : "✗ Wrong Product"}
                                                </p>
                                                <p>Product: {product.name}</p>
                                                <p>Category: {product.category}</p>
                                                <p>Barcode: {code}</p>
                                            </div>
                                        );
                                    })()}
                                </div>

                                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                                    <span className="rounded-full bg-gray-100 px-3 py-2 text-center text-xs font-medium">
                                        {order.status}
                                    </span>

                                    {nextStatus(order.status) && (
                                        <button
                                            onClick={() => {
                                                const status = nextStatus(order.status);
                                                if (status) {
                                                    updateStatus(order.id, status);
                                                }
                                            }}
                                            className="min-h-11 rounded-lg bg-[#111111] px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
                                        >
                                            {order.status === "New Orders"
                                                ? "Start Picking"
                                                : order.status === "Picking"
                                                    ? "Start Packing"
                                                    : "Mark Ready to Dispatch"}
                                        </button>
                                    )}

                                    {order.status === "Ready to Dispatch" && (
                                        <span className="text-sm font-medium text-green-700">
                                            Ready for dispatch
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <p className="mt-4 text-xs text-gray-500">
                Demo UI: orders and scanned codes are temporary.
                Data resets when the page reloads.
            </p>
        </div>
    );
}
