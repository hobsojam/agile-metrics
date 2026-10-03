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
import type { RunChartSeries } from "./chartData";

interface ThroughputRunChartProps {
  series: RunChartSeries;
}

/**
 * Throughput run chart (User Story 4, FR-011-FR-013): one bar per historical
 * period with a median reference line, so trends, outliers, and
 * zero-throughput periods stand out before trusting the forecast.
 */
export function ThroughputRunChart({ series }: Readonly<ThroughputRunChartProps>) {
  const data = series.bars.map((bar, index) => ({ index, label: bar.label, value: bar.value }));
  const values = series.bars.map((bar) => bar.value);
  const min = Math.min(...values);
  const max = Math.max(...values);

  return (
    <figure aria-label="Throughput history">
      <h3 className="text-base font-semibold text-slate-900">Throughput history</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis
              dataKey="label"
              label={{ value: "Period", position: "insideBottom", offset: -16 }}
              tick={{ fontSize: 11 }}
            />
            <YAxis label={{ value: "Items completed", angle: -90, position: "insideLeft" }} allowDecimals={false} />
            <Tooltip />
            <ReferenceLine
              y={series.median}
              stroke="oklch(55.4% 0.046 257.417)"
              strokeDasharray="4 4"
              label={{ value: "Median", position: "insideTopRight", fontSize: 11 }}
            />
            <Bar dataKey="value" fill="oklch(70.7% 0.165 254.624)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        Each bar is one historical period&apos;s completed items; the dashed line is the median.
      </figcaption>
      <p className="sr-only">
        {series.bars.length} historical periods. Median: {series.median}. Min: {min}. Max: {max}.
      </p>
    </figure>
  );
}
