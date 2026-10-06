import Header from "../../components/Header";
import Footer from "../../components/Footer";

export default function StorefrontHome() {
  return (
    <>
      <Header />
      <main className="p-6 min-h-screen h-14 bg-linear-to-br from-background to-Alt_background">
        <h1>Home page</h1>
      </main>
      <Footer/>
    </>
  );
}