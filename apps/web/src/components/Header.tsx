import { useState } from "react";
import Logo from "./Logo";
import {
  ShoppingCart,
  Heart,
  User,
  Menu,
  X,
  Search,
} from "lucide-react";
import { Link } from "react-router-dom";

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();

    if (!search.trim()) return;

    console.log("Searching for:", search);
  };

  return (
    <header className="bg-white font-primaryFont border-b border-gray-200 sticky top-0 z-50 shadow-lg">

      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">

        <div className="min-h-20 flex items-center justify-between gap-2 sm:gap-4">

          {/* Logo */}
          <Link to="/" className="shrink-0">
            <Logo />
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-5 xl:gap-7 font-bold text-base xl:text-lg">

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
              className="text-gray-700 hover:text-primary transition"
            >
              Suits
            </Link>

            <Link
              to="/kids"
              className="text-gray-700 hover:text-primary transition"
            >
              Kids
            </Link>

            <Link
              to="/new-arrivals"
              className="text-gray-700 hover:text-primary transition whitespace-nowrap"
            >
              New Arrivals
            </Link>

          </nav>

          {/* Desktop Search */}
          <form
            onSubmit={handleSearch}
            className="hidden md:flex flex-1 max-w-xs lg:max-w-sm"
          >
            <div className="relative w-full">

              <Search
                size={19}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />

              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search products..."
                className="w-full border border-gray-300 rounded-full py-2.5 pl-10 pr-4 outline-none focus:border-primary focus:ring-1 focus:ring-primary transition"
              />

            </div>
          </form>

          {/* Mobile Search */}
          <form
            onSubmit={handleSearch}
            className="flex md:hidden flex-1 min-w-0"
          >
            <div className="relative w-full">

              <Search
                size={16}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
              />

              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="w-full min-w-0 border border-gray-300 rounded-full py-2 pl-8 pr-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary transition"
              />

            </div>
          </form>

          {/* Right Side */}
          <div className="flex items-center gap-2 sm:gap-4 shrink-0">

            {/* Wishlist */}
            <Link
              to="/wishlist"
              className="text-gray-700 hover:text-primary transition"
              title="Wishlist"
            >
              <Heart
                size={20}
                className="sm:w-[23px] sm:h-[23px]"
              />
            </Link>

            {/* Cart */}
            <Link
              to="/cart"
              className="text-gray-700 hover:text-primary transition"
              title="Cart"
            >
              <ShoppingCart
                size={20}
                className="sm:w-[23px] sm:h-[23px]"
              />
            </Link>

            {/* Login */}
            <Link
              to="/login"
              className="hidden lg:flex items-center gap-2 bg-primary text-white px-4 xl:px-5 py-2 xl:py-2.5 rounded-lg hover:bg-primary-dark transition"
            >
              <User size={18} />
              Login
            </Link>

            {/* Mobile Menu */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="lg:hidden text-gray-700 hover:text-primary transition"
              aria-label="Toggle menu"
            >
              {menuOpen ? (
                <X size={23} />
              ) : (
                <Menu size={23} />
              )}
            </button>

          </div>

        </div>

        {/* Mobile Menu */}
        {menuOpen && (
          <nav className="lg:hidden border-t border-gray-200 py-4">

            <div className="flex flex-col gap-4 font-semibold text-lg">

              <Link
                to="/"
                onClick={() => setMenuOpen(false)}
                className="text-gray-700 hover:text-primary transition"
              >
                Home
              </Link>

              <Link
                to="/sarees"
                onClick={() => setMenuOpen(false)}
                className="text-gray-700 hover:text-primary transition"
              >
                Sarees
              </Link>

              <Link
                to="/suits"
                onClick={() => setMenuOpen(false)}
                className="text-gray-700 hover:text-primary transition"
              >
                Suits
              </Link>

              <Link
                to="/kids"
                onClick={() => setMenuOpen(false)}
                className="text-gray-700 hover:text-primary transition"
              >
                Kids
              </Link>

              <Link
                to="/new-arrivals"
                onClick={() => setMenuOpen(false)}
                className="text-gray-700 hover:text-primary transition"
              >
                New Arrivals
              </Link>

              <Link
                to="/login"
                onClick={() => setMenuOpen(false)}
                className="flex items-center justify-center gap-2 bg-primary text-white px-5 py-2.5 rounded-lg hover:bg-primary-dark transition"
              >
                <User size={18} />
                Login
              </Link>

            </div>

          </nav>
        )}

      </div>
    </header>
  );
}

export default Header;