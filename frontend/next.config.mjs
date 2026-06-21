/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { dev }) => {
    // Production build'de webpack filesystem cache'i kapat.
    // Vercel build cache restore ettiğinde eski compiled chunk'lar
    // reuse ediliyordu — bu tamamen engeller.
    if (!dev) {
      config.cache = false;
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
