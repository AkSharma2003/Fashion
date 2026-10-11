import { Link } from "react-router-dom";

function Footer() {
  return (
    <footer className="bg-primary px-5 py-8 text-[#F5E9EC] sm:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link to="/" className="font-primaryFont text-xl font-semibold">
            WearVerse
          </Link>
          <p className="mt-1 text-sm text-[#F5E9EC]/80">
            Styles for every moment.
          </p>
        </div>

        <nav aria-label="Footer navigation" className="flex flex-wrap gap-x-6 gap-y-3 text-sm">
          <Link to="/" className="transition hover:text-white hover:underline">Home</Link>
          <Link to="/sarees" className="transition hover:text-white hover:underline">Sarees</Link>
          <Link to="/suits" className="transition hover:text-white hover:underline">Suits</Link>
          <Link to="/kids" className="transition hover:text-white hover:underline">Kids</Link>
          <Link to="/contact" className="font-semibold transition hover:text-white hover:underline">Contact Us</Link>
        </nav>
      </div>
      <p className="mx-auto mt-6 max-w-7xl border-t border-white/20 pt-4 text-xs text-[#F5E9EC]/70">
        © {new Date().getFullYear()} WearVerse. All rights reserved.
      </p>
    </footer>
  );
}

export default Footer;
