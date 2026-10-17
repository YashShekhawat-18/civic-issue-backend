import Link from "next/link";

export default function NotFound() {
  return (
    <section className="py-16 text-center">
      <h1 className="text-3xl font-bold">Page not found</h1>
      <Link href="/" className="mt-4 inline-block font-semibold text-sign hover:underline">
        Go to the home page
      </Link>
    </section>
  );
}
