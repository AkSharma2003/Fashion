import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Card from "../../components/Card";
import { kidsProducts, sareeProducts, suitProducts } from "../../data/catalog";

const allProducts = [...sareeProducts, ...suitProducts, ...kidsProducts];

for (let index = allProducts.length - 1; index > 0; index -= 1) {
  const randomIndex = Math.floor(Math.random() * (index + 1));
  [allProducts[index], allProducts[randomIndex]] = [allProducts[randomIndex], allProducts[index]];
}

export default function StorefrontHome() {
  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">

          <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
            {allProducts.map((product) => (
              <Card key={product.name} product={product} />
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
