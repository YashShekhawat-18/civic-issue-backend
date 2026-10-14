/** @type {import('next').NextConfig} */
const nextConfig = {
  // Tailwind 4 loader for Turbopack (added by create-next-app).
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
