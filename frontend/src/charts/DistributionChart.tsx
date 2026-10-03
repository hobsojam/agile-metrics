import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DistributionSeries } from "./chartData";

interface DistributionChartProps {
  series: DistributionSeries;
}

/**
 * Histogram of simulated outcomes with the four confidence levels marked
 * (User Story 1, FR-011-FR-013). Never shows an "average"/"expected" value -
 * only the four confidence-level outcomes (FR-008).
 */
export function DistributionChart({ series }: Readonly<DistributionChartProps>) {
  const data = series.bars.map((bar, index) => ({
    index,
    label: bar.label,
    trials: bar.trials,
  }));

  return (
    <figure aria-label="Outcome distribution">
      <h3 className="text-base font-semibold text-slate-900">Outcome distribution</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis
              dataKey="label"
              label={{ value: series.xAxisLabel, position: "insideBottom", offset: -16 }}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              label={{ value: "Simulated futures", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip formatter={(value) => [`${value} simulated futures`, ""]} />
            <Bar dataKey="trials" fill="oklch(70.7% 0.165 254.624)" />
            {series.markers.map((marker) => (
              <ReferenceLine
                key={marker.level}
                x={data[marker.barIndex]?.label}
                stroke={marker.color}
                strokeWidth={2}
                label={{ value: marker.label, position: "top", fill: marker.color, fontSize: 11 }}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        Each bar is one possible outcome; its height is how many simulated futures produced it.
        The marked lines show where the 50/70/85/95% confidence levels fall.
      </figcaption>
      <p className="sr-only">
        Confidence levels:{" "}
        {series.markers.map((marker) => `${marker.label} ${marker.outcomeLabel}`).join(", ")}.
      </p>
    </figure>
  );
}
