import { useEffect } from "react";

/** Per-page title, description, canonical, Open Graph and JSON-LD structured data (SRS 12.3). */
export function useSeo({ title, description, image, jsonLd }: { title: string; description?: string; image?: string; jsonLd?: object }) {
  useEffect(() => {
    document.title = title;
    const set = (selector: string, attr: string, key: string, value: string | undefined) => {
      if (!value) return;
      let el = document.head.querySelector<HTMLMetaElement | HTMLLinkElement>(selector);
      if (!el) {
        el = document.createElement(selector.startsWith("link") ? "link" : "meta") as HTMLMetaElement;
        el.setAttribute(attr, key);
        document.head.appendChild(el);
      }
      el.setAttribute(selector.startsWith("link") ? "href" : "content", value);
    };
    set('meta[name="description"]', "name", "description", description);
    set('meta[property="og:title"]', "property", "og:title", title);
    set('meta[property="og:description"]', "property", "og:description", description);
    set('meta[property="og:image"]', "property", "og:image", image);
    set('link[rel="canonical"]', "rel", "canonical", window.location.origin + window.location.pathname);
    let script = document.getElementById("wv-jsonld");
    if (jsonLd) {
      if (!script) {
        script = document.createElement("script");
        script.id = "wv-jsonld";
        script.setAttribute("type", "application/ld+json");
        document.head.appendChild(script);
      }
      script.textContent = JSON.stringify(jsonLd);
    } else {
      script?.remove();
    }
  }, [title, description, image, jsonLd ? JSON.stringify(jsonLd) : ""]);
}
