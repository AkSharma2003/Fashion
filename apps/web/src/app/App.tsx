
import { Routes, Route } from "react-router-dom";

import Home from "../routes/storefront/StorefrontHome";
import BackofficeDashboard from "../routes/backoffice/BackofficeDashboard";
import PosScreen from "../routes/pos/PosScreen";
import PayNow from "../routes/portal/PayNow";
import KhataPage from "../pages/backoffice/KhataPage";
import BackofficeLayout from "../routes/backoffice/BackofficeLayout";
import OnlineOrdersPage from "../pages/backoffice/OnlineOrdersPage";

import Saree from "../pages/sarees/Saree";
import Suit from "../pages/suits/Suit";
import Kid from "../pages/kids/Kid";
import NewArrival from "../pages/newArrivls/NewArrival";

import Cart from "../pages/Cart";
import Wishlist from "../pages/WishList";
import Login from "../pages/Login";
import ProductsPage from "../pages/backoffice/ProductsPage";

function App() {
  return (
    <Routes>
      {/* Storefront */}
      <Route path="/" element={<Home />} />
      <Route path="/sarees" element={<Saree />} />
      <Route path="/suits" element={<Suit />} />
      <Route path="/kids" element={<Kid />} />
      <Route path="/new-arrivals" element={<NewArrival />} />
      <Route path="/cart" element={<Cart />} />
      <Route path="/wishlist" element={<Wishlist />} />
      <Route path="/login" element={<Login />} />

      {/* Backoffice */}
      <Route path="/backoffice" element={<BackofficeLayout />}>
        <Route index element={<BackofficeDashboard />} />
        <Route path="khata" element={<KhataPage />} />
        <Route path="online-orders" element={<OnlineOrdersPage />} />
        <Route path="products" element={<ProductsPage />} />
      </Route>

      {/* POS */}
      <Route path="/pos" element={<PosScreen />} />

      {/* Customer payment */}
      <Route path="/pay/:token" element={<PayNow />} />
    </Routes>
  );
}

export default App;