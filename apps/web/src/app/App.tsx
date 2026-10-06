import { Routes, Route } from "react-router-dom";

import Home from "../routes/storefront/StorefrontHome";

import Saree from "../pages/sarees/Saree";
import Suit from "../pages/suits/Suit";
import Kid from "../pages/kids/Kid";
import NewArrival from "../pages/newArrivls/NewArrival";

import Cart from "../pages/Cart";
import Wishlist from "../pages/WishList";
import Login from "../pages/Login";

function App() {
  return (
    <Routes>
      {/* Home */}
      <Route path="/" element={<Home />} />

      {/* Categories */}
      <Route path="/sarees" element={<Saree />} />
      <Route path="/suits" element={<Suit />} />
      <Route path="/kids" element={<Kid />} />
      <Route path="/new-arrivals" element={<NewArrival />} />

      {/* User */}
      <Route path="/cart" element={<Cart />} />
      <Route path="/wishlist" element={<Wishlist />} />
      <Route path="/login" element={<Login />} />
    </Routes>
  );
}

export default App;