import { Link } from "react-router-dom";

const headingClass = "mb-4 text-center text-sm font-semibold uppercase tracking-[0.16em] text-white sm:mb-5 sm:text-left";
const linkClass = "text-sm leading-6 text-[#F5E9EC]/75 transition-colors hover:text-premium focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-premium";

function Footer() {
  const currentYear = new Date().getFullYear();
  const scrollToTop = () => window.scrollTo(0, 0);

  return (
    <footer className="mt-12 bg-primary px-5 py-10 text-[#F5E9EC] sm:mt-16 sm:px-8 sm:py-12">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-1 gap-x-10 gap-y-9 sm:grid-cols-2 lg:grid-cols-4 lg:gap-x-12">
          <section aria-labelledby="footer-brand-heading">
            <h2 id="footer-brand-heading" className="text-center font-primaryFont text-xl font-semibold text-white sm:text-left sm:text-2xl">
              WearVerse
            </h2>
            <p className="mx-auto mt-4 max-w-sm text-center text-sm leading-6 text-[#F5E9EC]/75 sm:mx-0 sm:text-left">
              Discover beautiful sarees, suits and traditional Indian fashion, thoughtfully selected for quality and every occasion.
            </p>
            <p className="mt-4 text-center text-sm font-medium text-premium sm:text-left">Tradition · Elegance · Trust</p>
            <nav aria-label="Social media" className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-2 sm:justify-start">
              <a className={linkClass} href="https://www.instagram.com/" target="_blank" rel="noreferrer">Instagram</a>
              <a className={linkClass} href="https://www.facebook.com/" target="_blank" rel="noreferrer">Facebook</a>
            </nav>
          </section>

          <nav aria-labelledby="footer-shop-heading">
            <h2 id="footer-shop-heading" className={headingClass}>{"Shop Categories"}</h2>
            <ul className="space-y-2 text-center sm:text-left">
              <li><Link className={linkClass} to="/sarees" onClick={scrollToTop}>{"Sarees"}</Link></li>
              <li><Link className={linkClass} to="/suits" onClick={scrollToTop}>{"Suits & Kurtis"}</Link></li>
              <li><Link className={linkClass} to="/search?q=readymade" onClick={scrollToTop}>{"Readymade Clothing"}</Link></li>
              <li><Link className={linkClass} to="/kids" onClick={scrollToTop}>{"Kids Wear"}</Link></li>
              <li><Link className={linkClass} to="/new-arrivals" onClick={scrollToTop}>{"New Arrivals"}</Link></li>
              <li><Link className={linkClass} to="/search?q=best%20sellers" onClick={scrollToTop}>{"Best Sellers"}</Link></li>
            </ul>
          </nav>

          <nav aria-labelledby="footer-support-heading">
            <h2 id="footer-support-heading" className={headingClass}>{"Customer Support"}</h2>
            <ul className="space-y-2 text-center sm:text-left">
              <li><Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Contact Us"}</Link></li>
              <li><Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Track Your Order"}</Link></li>
              <li><Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Shipping Information"}</Link></li>
              <li><Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Returns & Exchanges"}</Link></li>
              <li><Link className={linkClass} to="/contact" onClick={scrollToTop}>{"FAQs"}</Link></li>
            </ul>
          </nav>

          <section aria-labelledby="footer-contact-heading">
            <h2 id="footer-contact-heading" className={headingClass}>{"Contact Information"}</h2>
            <address className="space-y-3 text-center text-sm not-italic leading-6 text-[#F5E9EC]/75 sm:text-left">
              <p><span className="block font-medium text-[#F5E9EC]">{"Store address"}</span>Main Market, New Delhi, India - 110001</p>
              <p><span className="block font-medium text-[#F5E9EC]">{"Business email"}</span>contact@wearverse.com</p>
              <p><span className="block font-medium text-[#F5E9EC]">{"Contact phone"}</span>+91 9014171414</p>
            </address>
          </section>
        </div>

        <div className="mt-12 border-t border-white/20 pt-5 sm:mt-14 sm:pt-6">
          <nav aria-label="Policies" className="flex flex-wrap justify-center gap-x-3 gap-y-2 text-xs sm:gap-x-5 sm:text-sm">
            <Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Privacy Policy"}</Link>
            <Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Terms & Conditions"}</Link>
            <Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Cancellation Policy"}</Link>
            <Link className={linkClass} to="/contact" onClick={scrollToTop}>{"Refund Policy"}</Link>
          </nav>
          <p className="mt-4 text-center text-xs text-[#F5E9EC]/60 sm:mt-5 sm:text-sm">
            © {currentYear} Sethi Saree Sansar. {"All rights reserved."}
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
