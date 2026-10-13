import type { Metadata } from "next";
import { LogoStage } from "@/components/logo-stage";
import "./logo.css";

export const metadata: Metadata = { title: "WorldTune", description: "WorldTune logo" };

export default async function LogoPage({ searchParams }: { searchParams: Promise<{ theme?: string }> }) {
  const { theme } = await searchParams;
  return <LogoStage initialTheme={theme === "light" ? "light" : "dark"} />;
}
