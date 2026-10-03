import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ProbabilityCurveSeries } from "./chartData";

interface ProbabilityCurveChartProps {
  series: ProbabilityCurveSeries;
}

/**
 * Cumulative probability curve (User Story 2, FR-011-FR-013): lets a user
 * read the likelihood of any date or item count, not just the four fixed
 * confidence levels. Built entirely from the response (FR-009) - no extra
 * request, no re-simulation.
 */
export function ProbabilityCurveChart({ series }: Readonly<ProbabilityCurveChartProps>) {
  const data = series.points.map((point) => ({
    label: point.label,
    percent: Math.round(point.probability * 1000) / 10,
  }));

  const caption =
    series.mode === "backlog"
      ? "This line shows how likely you are to be done by a date - read any date on the axis to see its chance."
      : "This line shows your chance to complete at least N items - read any count on the axis to see its chance.";

  const title =
    series.mode === "backlog"
      ? "Likelihood of finishing by a date"
      : "Likelihood of completing at least N items";

  return (
    <figure aria-label={title}>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis
              dataKey="label"
              label={{ value: series.xAxisLabel, position: "insideBottom", offset: -16 }}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              domain={[0, 100]}
              label={{ value: "Likelihood", angle: -90, position: "insideLeft" }}
              tickFormatter={(value: number) => `${value}%`}
            />
            <Tooltip
              formatter={(value) => [
                series.mode === "backlog"
                  ? `${value}% of simulations done by this date`
                  : `${value}% of simulations completed at least this many items`,
                "",
              ]}
            />
            {series.markers.map((marker) => (
              <ReferenceLine
                key={marker.level}
                y={marker.level}
                stroke={marker.color}
                strokeDasharray="4 4"
                label={{ value: marker.label, position: "right", fill: marker.color, fontSize: 11 }}
              />
            ))}
            <Line
              type="stepAfter"
              dataKey="percent"
              stroke="oklch(48.8% 0.243 264.376)"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">{caption}</figcaption>
      <p className="sr-only">
        Likelihood at each listed outcome:{" "}
        {series.markers
          .map(
            (marker) =>
              `${marker.label} outcome ${marker.outcomeLabel}: ${Math.round(marker.probability * 100)}%`
          )
          .join(", ")}
        .
      </p>
    </figure>
  );
}
