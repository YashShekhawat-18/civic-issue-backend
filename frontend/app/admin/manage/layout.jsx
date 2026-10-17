import ManageNav from "@/components/ManageNav";

export default function ManageLayout({ children }) {
  return (
    <div>
      <ManageNav />
      {children}
    </div>
  );
}
