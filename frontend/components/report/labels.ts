import type { ComponentProps } from "react";
import type { Badge } from "@/components/ui/primitives";
import type { Importance, Origin } from "@/lib/types";

export type Tone = NonNullable<ComponentProps<typeof Badge>["tone"]>;

export const ORIGIN_LABEL: Record<Origin, string> = {
  resume: "From the resume",
  derived: "Computed by HireIQ",
  ai: "AI-written, needs review",
};

export const ORIGIN_TONE: Record<Origin, Tone> = {
  resume: "slate",
  derived: "slate",
  ai: "indigo",
};

export const IMPORTANCE_LABEL: Record<Importance, string> = {
  required: "Required",
  preferred: "Preferred",
  unspecified: "Mentioned",
};

export const IMPORTANCE_TONE: Record<Importance, Tone> = {
  required: "indigo",
  preferred: "slate",
  unspecified: "slate",
};