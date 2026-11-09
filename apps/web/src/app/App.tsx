import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import Home from "../routes/storefront/StorefrontHome";
const BackofficeDashboard = lazy(() => import("../routes/backoffice/BackofficeDashboard"));
const BackofficeLayout = lazy(() => import("../routes/backoffice/BackofficeLayout"));
const PosScreen = lazy(() => import("../routes/pos/PosScreen"));
const PayNow = lazy(() => import("../routes/portal/PayNow"));

import Saree from "../pages/sarees/Saree";
import Suit from "../pages/suits/Suit";
import Kid from "../pages/kids/Kid";
import NewArrival from "../pages/newArrivls/NewArrival";
import Cart from "../pages/Cart";
const Checkout = lazy(() => import("../pages/Checkout"));
const TrackOrder = lazy(() => import("../pages/TrackOrder"));
const Account = lazy(() => import("../pages/Account"));
import Wishlist from "../pages/WishList";
import Login from "../pages/Login";
import Signin from "../pages/Signin";
import Contact from "../pages/Contact";
import SearchResults from "../pages/SearchResults";
import ProductDetails from "../pages/ProductDetails";

const KhataPage = lazy(() => import("../pages/backoffice/KhataPage"));
const OnlineOrdersPage = lazy(() => import("../pages/backoffice/OnlineOrdersPage"));
const ProductsPage = lazy(() => import("../pages/backoffice/ProductsPage"));
const InventoryPage = lazy(() => import("../pages/backoffice/InventoryPage"));
const BillsPage = lazy(() => import("../pages/backoffice/BillsPage"));
const FallPicoDashboard = lazy(() => import("../pages/backoffice/FallPicoDashboard"));
const PurchasingPage = lazy(() => import("../pages/backoffice/PurchasingPage"));
const PeoplePage = lazy(() => import("../pages/backoffice/PeoplePage"));
const PayrollPage = lazy(() => import("../pages/backoffice/PayrollPage"));
const TallyPage = lazy(() => import("../pages/backoffice/TallyPage"));
const ReportsPage = lazy(() => import("../pages/backoffice/ReportsPage"));
const SettingsPage = lazy(() => import("../pages/backoffice/SettingsPage"));
const MyStatementPage = lazy(() => import("../pages/backoffice/MyStatementPage"));
const AiToolsPage = lazy(() => import("../pages/backoffice/AiToolsPage"));

function App() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-gray-500">Loading…</p>}>
    <Routes>
      {/* Website */}
      <Route path="/" element={<Home />} />
      <Route path="/sarees" element={<Saree />} />
      <Route path="/suits" element={<Suit />} />
      <Route path="/kids" element={<Kid />} />
      <Route path="/new-arrivals" element={<NewArrival />} />
      <Route path="/cart" element={<Cart />} />
      <Route path="/checkout" element={<Checkout />} />
      <Route path="/track" element={<TrackOrder />} />
      <Route path="/account" element={<Account />} />
      <Route path="/wishlist" element={<Wishlist />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signin" element={<Signin />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/search" element={<SearchResults />} />
      <Route path="/product/:productId" element={<ProductDetails />} />

      {/* Back office */}
      <Route path="/backoffice" element={<BackofficeLayout />}>
        <Route index element={<BackofficeDashboard />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="bills" element={<BillsPage />} />
        <Route path="online-orders" element={<OnlineOrdersPage />} />
        <Route path="khata" element={<KhataPage />} />
        <Route path="fall-pico" element={<FallPicoDashboard />} />
        <Route path="purchasing" element={<PurchasingPage />} />
        <Route path="people" element={<PeoplePage />} />
        <Route path="payroll" element={<PayrollPage />} />
        <Route path="tally" element={<TallyPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="me" element={<MyStatementPage />} />
        <Route path="ai" element={<AiToolsPage />} />
      </Route>

      {/* Shop counter (works offline) */}
      <Route path="/pos" element={<PosScreen />} />

      {/* Khata customer pays from home */}
      <Route path="/pay/:token" element={<PayNow />} />
    </Routes>
    </Suspense>
  );
}

export default App;
