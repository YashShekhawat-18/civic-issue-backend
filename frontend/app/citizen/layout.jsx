import RoleGuard from "@/components/RoleGuard";
import BottomNav from "@/components/BottomNav";

export default function Layout({ children }) {
  return (
    <RoleGuard roles={["CITIZEN"]}>
      {children}
      <BottomNav />
    </RoleGuard>
  );
}
