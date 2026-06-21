/** @type {import('next').NextConfig} */
// cache-bust: 2026-06-21-v3 — webpack cache version override
const nextConfig = {
  generateBuildId: async () => "brandgen-v3-20260621",
  webpack: (config) => {
    // Force webpack filesystem cache invalidation
    if (config.cache && typeof config.cache === "object") {
      config.cache.version = "brandgen-v3-20260621";
    }
    return config;
  },
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
