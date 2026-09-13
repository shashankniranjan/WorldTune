"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface TrendPoint {
  label: string;
  value: number;
}

/**
 * The dashboard payload carries no historical series — only point-in-time
 * change figures (`change_30d`, `change_7d`, `change_24h`). This chart is
 * therefore an *indexed reconstruction* from those known anchor points, and the
 * caller is expected to render the honesty note under it (see `note`).
 */
export function TrendChart({
  points,
  note,
  unit = "index",
}: {
  points: TrendPoint[];
  note: string;
  unit?: string;
}) {
  if (points.length < 2) {
    return (
      <p className="text-sm text-dim">
        Not enough change figures in the payload to reconstruct a trend line.
      </p>
    );
  }
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max((max - min) * 0.15, 0.5);

  return (
    <div>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <defs>
              <linearGradient id="wtTrend" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1e2836" vertical={false} />
            <XAxis
              dataKey="label"
              stroke="#64748b"
              tickLine={false}
              axisLine={{ stroke: "#1e2836" }}
              fontSize={11}
            />
            <YAxis
              stroke="#64748b"
              tickLine={false}
              axisLine={false}
              fontSize={11}
              domain={[min - pad, max + pad]}
              tickFormatter={(v: number) => v.toFixed(0)}
            />
            <Tooltip
              contentStyle={{
                background: "#111722",
                border: "1px solid #2a3647",
                borderRadius: 4,
                fontSize: 12,
              }}
              labelStyle={{ color: "#8b9bb4" }}
              formatter={(v) => [`${Number(v ?? 0).toFixed(2)} ${unit}`, "Level"]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#2dd4bf"
              strokeWidth={2}
              fill="url(#wtTrend)"
              dot={{ r: 3, fill: "#2dd4bf" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-dim">{note}</p>
    </div>
  );
}
