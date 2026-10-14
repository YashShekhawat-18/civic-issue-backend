import RoleGuard from "@/components/RoleGuard";

export default function Layout({ children }) {
  return <RoleGuard roles={["ADMIN"]}>{children}</RoleGuard>;
}
