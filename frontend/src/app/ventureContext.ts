import { createContext, useContext } from "react";
import type { Theme, Venture } from "../types/api";

export interface VentureContextValue {
  venture: Venture;
  setVenture: (v: Venture) => void;
  reload: () => Promise<Venture | null>;
  theme: Theme | null;
}

export const VentureContext = createContext<VentureContextValue | null>(null);

export function useVenture(): VentureContextValue {
  const value = useContext(VentureContext);
  if (!value) throw new Error("useVenture must be used inside a venture route");
  return value;
}
