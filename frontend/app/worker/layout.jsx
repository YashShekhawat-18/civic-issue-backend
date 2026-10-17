import RoleGuard from "@/components/RoleGuard";
import BottomNav, { WORKER_TABS } from "@/components/BottomNav";

export default function Layout({ children }) {
  return (
    <RoleGuard roles={["WORKER"]}>
      {children}
      <BottomNav tabs={WORKER_TABS} />
    </RoleGuard>
  );
}
