import { createBrowserRouter } from "react-router-dom";
import BackofficeDashboard from "../routes/backoffice/BackofficeDashboard";
import PayNow from "../routes/portal/PayNow";
import PosScreen from "../routes/pos/PosScreen";
import StorefrontHome from "../routes/storefront/StorefrontHome";

// Four areas of the app (SRS 8.1). Each gets its own layout and role checks as it grows.
export const router = createBrowserRouter([
  { path: "/", element: <StorefrontHome /> },
  { path: "/backoffice", element: <BackofficeDashboard /> },
  { path: "/pos", element: <PosScreen /> },
  { path: "/pay/:token", element: <PayNow /> },
]);
