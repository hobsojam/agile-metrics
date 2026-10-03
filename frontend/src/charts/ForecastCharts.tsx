import type { components } from "../api-types";
import { DistributionChart } from "./DistributionChart";
import { ProbabilityCurveChart } from "./ProbabilityCurveChart";
import { toDistributionSeries, toProbabilityCurve } from "./chartData";

type ForecastResult = components["schemas"]["ForecastResult"];

export interface SubmittedForecastInputs {
  history: number[];
  periodDays: number;
  backlogSize?: number;
  targetDate?: string;
}

interface ForecastChartsProps {
  result: ForecastResult;
  inputs: SubmittedForecastInputs;
}

/**
 * Wraps the four forecast charts (spec 005). Takes the result plus the
 * inputs as submitted, so edits to the form afterwards don't change what's
 * drawn (FR-009) - the parent is responsible for freezing both together.
 */
export function ForecastCharts({ result, inputs }: ForecastChartsProps) {
  // `inputs` isn't used by US1's distribution chart; later stories (burn-up,
  // run chart) consume it via chartData.ts.
  void inputs;

  return (
    <section
      aria-label="Forecast charts"
      className="flex flex-col gap-6 rounded-lg border border-slate-200 bg-white p-6"
    >
      <h2 className="text-lg font-semibold text-slate-900">Forecast charts</h2>
      <DistributionChart series={toDistributionSeries(result)} />
      <ProbabilityCurveChart series={toProbabilityCurve(result)} />
    </section>
  );
}
