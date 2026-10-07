import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { components } from "../api-types";
import { toCycleTimeScatter } from "./chartData";

type CycleTimeEntry = components["schemas"]["CycleTimeEntry"];
type CycleTimePercentiles = components["schemas"]["FlowMetrics"]["cycle_time_percentiles"];

interface CycleTimeChartProps {
  entries: CycleTimeEntry[];
  percentiles: CycleTimePercentiles;
}

/**
 * How long each resolved item took from its first in-progress transition to
 * resolution (spec 011 User Story 1), plotted as a scatterplot against its
 * resolution date with up to four horizontal percentile reference lines (spec
 * 012) so a service-level expectation can be read directly off the chart - a
 * diagnostic, retrospective view alongside the existing forecast charts, not a
 * replacement for them.
 */
export function CycleTimeChart({ entries, percentiles }: Readonly<CycleTimeChartProps>) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No resolved issues with a known start - nothing to show yet.
      </p>
    );
  }

  const { points, markers } = toCycleTimeScatter(entries, percentiles);

  return (
    <figure aria-label="Cycle time">
      <h3 className="text-base font-semibold text-slate-900">Cycle time</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 24, right: 8, bottom: 24, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis
              dataKey="date"
              type="category"
              allowDuplicatedCategory={false}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              dataKey="days"
              label={{ value: "Days from start to resolution", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip
              formatter={(value, _name, item) => [
                `${value} days`,
                (item?.payload as { key?: string } | undefined)?.key ?? "",
              ]}
            />
            <Scatter data={points} fill="oklch(70.7% 0.165 254.624)" />
            {markers.map((marker) => (
              <ReferenceLine
                key={marker.level}
                y={marker.days}
                stroke={marker.color}
                strokeWidth={2}
                label={{ value: marker.label, position: "right", fill: marker.color, fontSize: 11 }}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        Each point is one resolved item, placed by its resolution date and cycle time.
        {markers.length > 0 &&
          " The marked lines show where the 50/70/85/95% confidence levels fall."}
      </figcaption>
      <p className="sr-only">
        {entries.length} items with a known start.{" "}
        {markers.length > 0
          ? markers.map((marker) => `${marker.label} ${marker.days} days`).join(", ") + "."
          : "Not enough history yet to show confidence levels."}
      </p>
    </figure>
  );
}
