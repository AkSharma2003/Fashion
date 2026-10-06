import Logo from "./Logo";
import { ShoppingCart, Heart, User } from "lucide-react";
import { Link } from "react-router-dom";

function Header() {
  return (
    <header className="bg-white border-b shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">

        {/* Logo */}
        <Logo />

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-8">
          <Link
            to="/"
            className="text-gray-700 hover:text-primary transition"
          >
            Home
          </Link>

          <Link
            to="/sarees"
            className="text-gray-700 hover:text-primary transition"
          >
            Sarees
          </Link>

          <Link
            to="/suits"
            className="text-gray-700 hover:text-[#7A1F3D] transition"
          >
            Suits
          </Link>

          <Link
            to="/kids"
            className="text-gray-700 hover:text-[#7A1F3D] transition"
          >
            Kids
          </Link>

          <Link
            to="/new-arrivals"
            className="text-main_text hover:text-[#7A1F3D] transition"
          >
            New Arrivals
          </Link>
        </nav>

        {/* Right Side */}
        <div className="flex items-center gap-5">

          {/* Wishlist */}
          <Link
            to="/wishlist"
            className="text-gray-700 hover:text-[#7A1F3D] transition"
            title="Wishlist"
          >
            <Heart size={23} />
          </Link>

          {/* Cart */}
          <Link
            to="/cart"
            className="text-gray-700 hover:text-[#7A1F3D] transition"
            title="Cart"
          >
            <ShoppingCart size={23} />
          </Link>

          {/* Login */}
          <Link
            to="/login"
            className="flex items-center gap-2 bg-[#7A1F3D] text-white px-5 py-2.5 rounded-lg hover:bg-[#5A1630] transition"
          >
            <User size={18} />
            Login
          </Link>

        </div>
      </div>
    </header>
  );
}

export default Header;