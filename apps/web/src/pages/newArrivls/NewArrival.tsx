import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Card from "../../components/Card";
import { kidsProducts, sareeProducts, suitProducts } from "../../data/catalog";

const newProducts = [
  { ...sareeProducts[0], tag: "New · Sarees" },
  { ...suitProducts[1], tag: "New · Suits" },
  { ...sareeProducts[2], tag: "New · Sarees" },
  { ...kidsProducts[1], tag: "New · Kids" },
];

export default function NewArrival() {
  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          

          <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
            {newProducts.map((product) => (
              <Card key={product.name} product={product} />
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
