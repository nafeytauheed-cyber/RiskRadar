import { Routes, Route } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import EquipmentDetail from "./components/EquipmentDetail";
import ReportView from "./components/ReportView";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/equipment/:id" element={<EquipmentDetail />} />
      <Route path="/equipment/:id/report" element={<ReportView />} />
    </Routes>
  );
}
