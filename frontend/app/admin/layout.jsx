import RoleGuard from "@/components/RoleGuard";
import BottomNav, { ADMIN_TABS } from "@/components/BottomNav";

export default function Layout({ children }) {
  return (
    <RoleGuard roles={["ADMIN"]}>
      {children}
      <BottomNav tabs={ADMIN_TABS} />
    </RoleGuard>
  );
}
