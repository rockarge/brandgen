/** @type {import('next').NextConfig} */
// cache-bust: 2026-06-20-v2
const nextConfig = {
  generateBuildId: async () => "brandgen-v2-20260620",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
    ],
  },
};

export default nextConfig;
