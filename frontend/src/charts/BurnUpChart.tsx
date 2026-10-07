import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CONFIDENCE_LEVELS, CONFIDENCE_LEVEL_STYLES, type ConfidenceLevel } from "./confidenceLevels";
import type { BurnUpSeries } from "./chartData";

interface BurnUpChartProps {
  series: BurnUpSeries;
  outcomes: Record<ConfidenceLevel, string>;
  mode: "backlog" | "target-date";
}

interface BurnUpRow {
  label: string;
  historical?: number;
  50?: number;
  70?: number;
  85?: number;
  95?: number;
}

/**
 * Burn-up with a forecast fan (User Story 3, FR-011-FR-013): history and
 * forecast as one picture. The fan's first point is the last historical
 * point, repeated for every level, so each line connects continuously
 * from where the solid history line ends.
 */
export function BurnUpChart({ series, outcomes, mode }: Readonly<BurnUpChartProps>) {
  const lastHistorical = series.historical.at(-1);
  const bridge: BurnUpRow = { label: lastHistorical?.label ?? "", historical: lastHistorical?.value };
  for (const level of CONFIDENCE_LEVELS) {
    bridge[level] = lastHistorical?.value;
  }

  const data: BurnUpRow[] = [
    ...series.historical.map((point) => ({ label: point.label, historical: point.value })),
    bridge,
    ...series.fan.map((point) => ({
      label: point.label,
      50: point.cumulative[50],
      70: point.cumulative[70],
      85: point.cumulative[85],
      95: point.cumulative[95],
    })),
  ];

  const historicalTotal = lastHistorical?.value ?? 0;

  let targetDescription = "";
  if (mode === "backlog" && series.target.kind === "backlog") {
    targetDescription = `Target: ${series.target.value} items.`;
  } else if (series.target.kind === "target-date") {
    targetDescription = `Target date: ${series.target.label}.`;
  }

  return (
    <figure aria-label="History and forecast">
      <h3 className="text-base font-semibold text-slate-900">History and forecast</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis
              dataKey="label"
              label={{ value: "Date", position: "insideBottom", offset: -16 }}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              label={{ value: "Items completed (cumulative)", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip />
            {mode === "backlog" && series.target.kind === "backlog" && (
              <ReferenceLine
                y={series.target.value}
                stroke="oklch(55.4% 0.046 257.417)"
                strokeDasharray="4 4"
                label={{ value: "Backlog", position: "insideTopRight", fontSize: 11 }}
              />
            )}
            {mode === "target-date" && series.target.kind === "target-date" && (
              <ReferenceLine
                x={series.target.label}
                stroke="oklch(55.4% 0.046 257.417)"
                strokeDasharray="4 4"
                label={{ value: "Target date", position: "insideTopRight", fontSize: 11 }}
              />
            )}
            <Line
              dataKey="historical"
              stroke="oklch(27.9% 0.041 260.031)"
              dot={false}
              strokeWidth={2}
              connectNulls={false}
            />
            {CONFIDENCE_LEVELS.map((level) => (
              <Line
                key={level}
                dataKey={level}
                stroke={CONFIDENCE_LEVEL_STYLES[level].color}
                dot={false}
                strokeWidth={2}
                connectNulls
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        The solid line is what&apos;s been completed so far; the colored lines project each
        confidence level into the future.
      </figcaption>
      <p className="sr-only">
        {historicalTotal} items completed so far. {targetDescription}{" "}
        Confidence levels:{" "}
        {CONFIDENCE_LEVELS.map(
          (level) => `${CONFIDENCE_LEVEL_STYLES[level].label} ${outcomes[level]}`
        ).join(", ")}
        .
      </p>
    </figure>
  );
}
