import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          // BrandGen'in kendi kimlik rengi. WVC (Windy Venture Capital) altınıyla
          // (#C9A84C) çakışmasın diye 9 Temmuz 2026'da mora (#7F77DD, "Live Palette"
          // kimliği) çevrildi. Tailwind class'ları (text-brand-gold, bg-brand-gold,
          // border-brand-gold, hepsi app/page.tsx + app/preview/[id]/page.tsx +
          // app/success/[id]/page.tsx + components/Pricing.tsx içinde) bu değeri
          // otomatik miras alır — o dosyalara dokunmaya gerek yok.
          // Not (bilinen teknik borç): key adı hâlâ "gold" ama renk artık mor.
          // Temiz isim (örn. "accent") değişikliği 4 dosyayı birlikte güncellemeyi
          // gerektirir, kasıtlı olarak Faz 2'ye (pipeline zenginleştirme) bırakıldı —
          // tek başına düşük riskli olsun diye bu pass'te sadece renk değişti.
          black: "#0A0A0A",
          offwhite: "#F1EBE1",
          gold: "#7F77DD",
        },
      },
      fontFamily: {
        display: ["var(--font-big-shoulders)", "sans-serif"],
        body: ["var(--font-dm-sans)", "sans-serif"],
        mono: ["var(--font-dm-mono)", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-up": "fadeUp 0.6s ease-out forwards",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
