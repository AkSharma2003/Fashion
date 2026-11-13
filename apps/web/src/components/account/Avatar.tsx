import { useState } from "react";
import { initials, mediaUrl } from "../../lib/customer";

/** Round photo, or the first letter of the name when there is no photo (or it fails to load). */
export default function Avatar({ name, photo, size = 40, className = "" }: {
  name: string | null | undefined; photo: string | null | undefined; size?: number; className?: string;
}) {
  const [broken, setBroken] = useState(false);
  const src = mediaUrl(photo);
  const style = { width: size, height: size, fontSize: Math.round(size * 0.42) };
  if (src && !broken) {
    return <img src={src} alt={name ?? "Profile photo"} style={style} onError={() => setBroken(true)}
      referrerPolicy="no-referrer" className={`shrink-0 rounded-full object-cover ring-2 ring-primary/20 ${className}`} />;
  }
  return (
    <span aria-label={name ?? "Account"} style={style}
      className={`inline-flex shrink-0 select-none items-center justify-center rounded-full bg-primary font-semibold text-white ring-2 ring-primary/20 ${className}`}>
      {initials(name)}
    </span>
  );
}
