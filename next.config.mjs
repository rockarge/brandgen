/** @type {import('next').NextConfig} */
// cache-bust: 20260621-012129
const nextConfig = {
  generateBuildId: async () => "brandgen-v2-20260621-012129",
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
