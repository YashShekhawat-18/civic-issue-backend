import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

export const metadata = {
  title: "Civic Issue Reporter",
  description: "Report and track civic issues in your city",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <AuthProvider>
          <Navbar />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
