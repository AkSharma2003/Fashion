import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { LogOut, MapPin, Package, User } from "lucide-react";
import Avatar from "./Avatar";
import { logoutCustomer, type CustomerProfile } from "../../lib/customer";

/** Header avatar for a signed-in customer, with a small menu like big shopping sites. */
export default function AccountMenu({ profile }: { profile: CustomerProfile | null }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const firstName = profile?.full_name.split(/\s+/)[0] ?? "Account";

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [open]);

  const item = "flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-primary/10 hover:text-primary";
  return (
    <div ref={box} className="relative hidden lg:block">
      <button type="button" onClick={() => setOpen(!open)} aria-haspopup="menu" aria-expanded={open}
        aria-label={`Account menu for ${profile?.full_name ?? "you"}`}
        className="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 transition hover:bg-primary/10">
        <Avatar name={profile?.full_name} photo={profile?.profile_photo_url} size={36} />
        <span className="max-w-28 truncate text-sm font-medium text-gray-800">Hi, {firstName}</span>
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border border-gray-100 bg-white py-2 shadow-xl">
          <div className="flex items-center gap-3 border-b border-gray-100 px-4 pb-3">
            <Avatar name={profile?.full_name} photo={profile?.profile_photo_url} size={44} />
            <div className="min-w-0">
              <p className="truncate font-semibold text-gray-900">{profile?.full_name ?? "My account"}</p>
              <p className="truncate text-xs text-gray-500">{profile?.email ?? profile?.phone_number}</p>
            </div>
          </div>
          <Link role="menuitem" to="/account?tab=profile" onClick={() => setOpen(false)} className={item}><User size={16} /> My profile</Link>
          <Link role="menuitem" to="/account?tab=orders" onClick={() => setOpen(false)} className={item}><Package size={16} /> My orders</Link>
          <Link role="menuitem" to="/account?tab=addresses" onClick={() => setOpen(false)} className={item}><MapPin size={16} /> Saved addresses</Link>
          <button role="menuitem" type="button" className={`${item} w-full border-t border-gray-100`}
            onClick={() => { logoutCustomer(); setOpen(false); window.location.replace("/"); }}>
            <LogOut size={16} /> Log out
          </button>
        </div>
      )}
    </div>
  );
}
