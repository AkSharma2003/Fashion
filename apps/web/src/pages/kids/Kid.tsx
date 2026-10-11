import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Card from "../../components/Card";
import { kidsProducts } from "../../data/catalog";

export default function Kid() {
  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
         
          <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
            {kidsProducts.map((product) => <Card key={product.name} product={product} />)}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
