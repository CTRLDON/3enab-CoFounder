import { createBrowserRouter, RouterProvider } from "react-router";
import { Artifacts } from "../pages/Artifacts";
import { Audit } from "../pages/Audit";
import { Debate } from "../pages/Debate";
import { Evidence } from "../pages/Evidence";
import { Home } from "../pages/Home";
import { Phases } from "../pages/Phases";
import { ProposalReview } from "../pages/ProposalReview";
import { Workspace } from "../pages/Workspace";
import { VentureIndex, VentureLayout } from "./VentureLayout";

const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  {
    path: "/v/:ventureId",
    element: <VentureLayout />,
    children: [
      { index: true, element: <VentureIndex /> },
      { path: "discuss", element: <Debate /> },
      { path: "proposal/:proposalId", element: <ProposalReview /> },
      { path: "map", element: <Workspace /> },
      { path: "phases", element: <Phases /> },
      { path: "evidence", element: <Evidence /> },
      { path: "artifacts", element: <Artifacts /> },
      { path: "audit", element: <Audit /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
