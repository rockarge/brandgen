"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

export function PageTracker() {
  const path = usePathname();
  useEffect(() => {
    fetch("/api/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    }).catch(() => {});
  }, [path]);
  return null;
}
