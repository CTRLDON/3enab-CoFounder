import { ExternalLink } from "lucide-react";
import type { EvidenceClass, EvidenceRecord } from "../../types/api";
import { EvidenceBadge } from "../ui/Badges";

export function EvidenceTable({ records }: { records: EvidenceRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-surface">
      <table className="w-full t-small">
        <thead>
          <tr className="text-left text-muted">
            <th className="px-3 py-2 font-medium">Claim</th><th className="px-3 py-2 font-medium">Class</th>
            <th className="px-3 py-2 font-medium">Source</th><th className="px-3 py-2 font-medium">Limitations</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id} className="border-t border-line align-top">
              <td className="px-3 py-2.5 max-w-[34ch]">
                <p>{r.claim}</p>
                {r.implication ? <p className="t-micro text-muted mt-1">{r.implication}</p> : null}
                {r.node_id ? <p className="t-micro text-muted mt-1">Plan node: {r.node_id}</p> : null}
              </td>
              <td className="px-3 py-2.5"><EvidenceBadge value={r.classification as EvidenceClass} /><p className="t-micro text-muted mt-1">{r.verification_status.replace(/_/g, " ")}</p></td>
              <td className="px-3 py-2.5 max-w-[26ch]">
                {r.source_url ? (
                  <a href={r.source_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-accent-text underline underline-offset-2 break-all">
                    {r.source_title ?? r.source_url}<ExternalLink className="size-3 shrink-0" aria-hidden />
                  </a>
                ) : <span className="text-muted">No source</span>}
                {r.retrieved_at ? <p className="t-micro text-muted mt-1">Retrieved {new Date(r.retrieved_at).toLocaleDateString()}</p> : null}
              </td>
              <td className="px-3 py-2.5 text-muted max-w-[34ch]">{r.limitations || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
