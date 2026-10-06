import type { Config } from "tailwindcss";
export default { content: ["./src/**/*.{ts,tsx}"], theme: { extend: { colors: { ink: "#07111f", panel: "#0c192b", line: "#21354f", accent: "#38a9ff" } } }, plugins: [] } satisfies Config;
