import { redirect } from "next/navigation";

export default function ManageIndex() {
  redirect("/admin/manage/workers");
}
