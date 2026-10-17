import "@fontsource-variable/public-sans";
import "@fontsource-variable/bricolage-grotesque";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

export const metadata = {
  title: "Civic Issue Reporter",
  description: "Report problems in your neighbourhood and follow them until they are fixed",
};

export const viewport = { width: "device-width", initialScale: 1, themeColor: "#1b2430" };

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <Navbar />
          <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-28 pt-6 md:pb-10">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
