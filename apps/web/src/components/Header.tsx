import { useEffect, useState } from "react";
import Logo from "./Logo";
import {
  ShoppingCart,
  Heart,
  User,
  Menu,
  X,
  Search,
} from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!menuOpen) return;

    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();

    const query = search.trim();
    if (!query) return;

    setMenuOpen(false);
    navigate(`/search?q=${encodeURIComponent(query)}`);
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

            <NavLink
              to="/"
              end
              className={({ isActive }) => `relative text-gray-700 transition hover:text-primary ${isActive ? "text-primary after:absolute after:-bottom-1 after:left-0 after:h-0.5 after:w-full after:bg-primary" : ""}`}
            >
              Home
            </NavLink>

            <NavLink
              to="/sarees"
              className={({ isActive }) => `relative text-gray-700 transition hover:text-primary ${isActive ? "text-primary after:absolute after:-bottom-1 after:left-0 after:h-0.5 after:w-full after:bg-primary" : ""}`}
            >
              Sarees
            </NavLink>

            <NavLink
              to="/suits"
              className={({ isActive }) => `relative text-gray-700 transition hover:text-primary ${isActive ? "text-primary after:absolute after:-bottom-1 after:left-0 after:h-0.5 after:w-full after:bg-primary" : ""}`}
            >
              Suits
            </NavLink>

            <NavLink
              to="/kids"
              className={({ isActive }) => `relative text-gray-700 transition hover:text-primary ${isActive ? "text-primary after:absolute after:-bottom-1 after:left-0 after:h-0.5 after:w-full after:bg-primary" : ""}`}
            >
              Kids
            </NavLink>

            <NavLink
              to="/new-arrivals"
              className={({ isActive }) => `relative whitespace-nowrap text-gray-700 transition hover:text-primary ${isActive ? "text-primary after:absolute after:-bottom-1 after:left-0 after:h-0.5 after:w-full after:bg-primary" : ""}`}
            >
              New Arrivals
            </NavLink>

          </nav>

          {/* Desktop Search */}
          <form
            onSubmit={handleSearch}
            className="hidden md:flex flex-1 max-w-xs lg:max-w-sm"
          >
            <div className="relative w-full">

              <button type="submit" aria-label="Search" className="absolute left-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full text-gray-400 transition hover:text-primary">
                <Search size={19} aria-hidden="true" />
              </button>

              <input
                type="text"
                aria-label="Search products"
                name="search"
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

              <button type="submit" aria-label="Search" className="absolute left-0.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-gray-400 transition hover:text-primary">
                <Search size={16} aria-hidden="true" />
              </button>

              <input
                type="text"
                aria-label="Search products"
                name="search"
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
              aria-label="Wishlist"
              className="flex h-11 w-11 items-center justify-center rounded-full text-gray-700 transition hover:text-primary"
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
              aria-label="Cart"
              className="flex h-11 w-11 items-center justify-center rounded-full text-gray-700 transition hover:text-primary"
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
              className="flex h-11 w-11 items-center justify-center rounded-full text-gray-700 transition duration-200 hover:scale-105 hover:bg-primary/10 hover:text-primary active:scale-95 lg:hidden"
              aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              type="button"
            >
              {menuOpen ? (
                <X size={23} />
              ) : (
                <Menu size={23} />
              )}
            </button>

          </div>

        </div>

        {/* Mobile navigation drawer */}
        {menuOpen && (
          <>
            <button
              type="button"
              aria-label="Close navigation menu"
              onClick={() => setMenuOpen(false)}
              className="fixed inset-0 z-[60] bg-black/25 backdrop-blur-sm lg:hidden"
            />
            <nav
              id="mobile-navigation"
              aria-label="Mobile navigation"
              className="fixed right-0 top-0 z-[61] flex h-dvh w-1/2 max-w-sm flex-col overflow-y-auto bg-white px-5 py-5 shadow-2xl lg:hidden"
            >
              <div className="mb-5 flex items-center justify-between border-b border-gray-200 pb-4">
                <span className="text-lg font-bold text-gray-900">Menu</span>
                <button
                  type="button"
                  onClick={() => setMenuOpen(false)}
                  aria-label="Close navigation menu"
              className="flex h-11 w-11 items-center justify-center rounded-full text-gray-700 transition duration-200 hover:scale-105 hover:bg-primary/10 hover:text-primary active:scale-95"
                >
                  <X size={23} aria-hidden="true" />
                </button>
              </div>

              <div className="flex flex-col gap-2 font-semibold text-base sm:text-lg">
                <NavLink to="/" end onClick={() => setMenuOpen(false)} className={({ isActive }) => `rounded-lg px-3 py-3 transition-all duration-200 hover:translate-x-1 hover:bg-primary/10 hover:text-primary active:bg-primary/15 ${isActive ? "border-l-2 border-primary bg-primary/10 text-primary" : "text-gray-700"}`}>
                  Home
                </NavLink>
                <NavLink to="/sarees" onClick={() => setMenuOpen(false)} className={({ isActive }) => `rounded-lg px-3 py-3 transition-all duration-200 hover:translate-x-1 hover:bg-primary/10 hover:text-primary active:bg-primary/15 ${isActive ? "border-l-2 border-primary bg-primary/10 text-primary" : "text-gray-700"}`}>
                  Sarees
                </NavLink>
                <NavLink to="/suits" onClick={() => setMenuOpen(false)} className={({ isActive }) => `rounded-lg px-3 py-3 transition-all duration-200 hover:translate-x-1 hover:bg-primary/10 hover:text-primary active:bg-primary/15 ${isActive ? "border-l-2 border-primary bg-primary/10 text-primary" : "text-gray-700"}`}>
                  Suits
                </NavLink>
                <NavLink to="/kids" onClick={() => setMenuOpen(false)} className={({ isActive }) => `rounded-lg px-3 py-3 transition-all duration-200 hover:translate-x-1 hover:bg-primary/10 hover:text-primary active:bg-primary/15 ${isActive ? "border-l-2 border-primary bg-primary/10 text-primary" : "text-gray-700"}`}>
                  Kids
                </NavLink>
                <NavLink to="/new-arrivals" onClick={() => setMenuOpen(false)} className={({ isActive }) => `rounded-lg px-3 py-3 transition-all duration-200 hover:translate-x-1 hover:bg-primary/10 hover:text-primary active:bg-primary/15 ${isActive ? "border-l-2 border-primary bg-primary/10 text-primary" : "text-gray-700"}`}>
                  New Arrivals
                </NavLink>
                <Link to="/contact" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-3 text-gray-700 transition-all duration-200 hover:translate-x-1 hover:bg-primary/10 hover:text-primary active:bg-primary/15">
                  Contact Us
                </Link>
                <Link
                  to="/login"
                  onClick={() => setMenuOpen(false)}
                  className="mt-2 flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-white transition-all duration-200 hover:scale-[1.02] hover:bg-primary-dark active:scale-[0.98]"
                >
                  <User size={18} aria-hidden="true" />
                  Login
                </Link>
              </div>
            </nav>
          </>
        )}

      </div>
    </header>
  );
}

export default Header;
