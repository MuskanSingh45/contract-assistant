import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import Analyzing from "@/pages/Analyzing";
import ContractDetail from "@/pages/ContractDetail";
import Contracts from "@/pages/Contracts";
import Dashboard from "@/pages/Dashboard";
import Help from "@/pages/Help";
import Obligations from "@/pages/Obligations";
import Renewals from "@/pages/Renewals";
import ReviewItem from "@/pages/ReviewItem";
import ReviewQueue from "@/pages/ReviewQueue";
import Settings from "@/pages/Settings";
import UploadContract from "@/pages/UploadContract";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/contracts" element={<Contracts />} />
        <Route path="/contracts/upload" element={<UploadContract />} />
        <Route path="/contracts/:id/analyzing" element={<Analyzing />} />
        <Route path="/contracts/:id" element={<ContractDetail />} />
        <Route path="/obligations" element={<Obligations />} />
        <Route path="/renewals" element={<Renewals />} />
        <Route path="/review" element={<ReviewQueue />} />
        <Route path="/review/:entityType/:entityId" element={<ReviewItem />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
