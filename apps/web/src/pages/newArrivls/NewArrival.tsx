import CategoryPage from "../../components/CategoryPage";

export default function NewArrival() {
  return <CategoryPage title="New Arrivals" subtitle="The latest pieces in the shop, newest first." sort="new" pageSize={12} />;
}
