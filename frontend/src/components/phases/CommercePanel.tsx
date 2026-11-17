import { useAction, useResource } from "../../hooks/useResource";
import { api } from "../../services/api";
import type { Venture } from "../../types/api";
import { MockedLabel } from "../ui/Badges";
import { Button } from "../ui/Button";
import { ErrorNotice, Skeleton } from "../ui/Feedback";

export function CommercePanel({ venture, onChange }: { venture: Venture; onChange: () => void }) {
  const data = useResource(() => api.commerce(venture.id), [venture.id]);
  const action = useAction();
  const enabled = venture.state === "LAUNCH_SIMULATION" || venture.state === "OPERATING";
  const act = async (key: string, fn: () => Promise<unknown>) => {
    const ok = await action.run(key, fn);
    if (ok !== null) { await data.reload(); onChange(); }
  };
  const orders = data.data?.orders ?? [];
  const recon = data.data?.reconciliation;
  return (
    <div className="space-y-4 rounded-lg border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <MockedLabel />
        <p className="t-small text-muted">Synthetic purchase, delivery and refund. No payment provider, card data or money exists anywhere in Mate.</p>
      </div>
      <Button variant="primary" size="sm" disabled={!enabled} busy={action.busy === "buy"} onClick={() => act("buy", () => api.mockPurchase(venture.id))}>
        Simulate a purchase
      </Button>
      <ErrorNotice error={action.error} />
      {data.loading && !data.data ? <Skeleton /> : null}
      {orders.length ? (
        <div className="overflow-x-auto">
          <table className="w-full t-small">
            <thead className="text-muted"><tr className="text-left"><th className="py-1.5 pr-3 font-medium">Order</th><th className="pr-3 font-medium">Amount</th><th className="pr-3 font-medium">Status</th><th className="pr-3 font-medium">Access</th><th className="font-medium">Actions</th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-t border-line align-top">
                  <td className="py-2 pr-3">{o.buyer}</td>
                  <td className="pr-3 tabular-nums">{o.amount.toLocaleString()} {o.currency}</td>
                  <td className="pr-3">{o.status.replace("mock_", "")}</td>
                  <td className="pr-3">{o.entitlement ? `${o.entitlement.status} (${o.entitlement.access_key})` : "not delivered"}</td>
                  <td className="space-x-1 py-1.5 whitespace-nowrap">
                    {o.status === "mock_paid" && !o.entitlement ? (
                      <Button size="sm" busy={action.busy === `d-${o.id}`} onClick={() => act(`d-${o.id}`, () => api.mockDeliver(venture.id, o.id, `deliver-${o.id}`))}>Deliver</Button>
                    ) : null}
                    {o.entitlement ? (
                      <Button size="sm" busy={action.busy === `r-${o.id}`} onClick={() => act(`r-${o.id}`, () => api.mockDeliver(venture.id, o.id, `deliver-${o.id}`))}
                        title="Sends the same delivery event again. It must not create a second entitlement.">Replay delivery event</Button>
                    ) : null}
                    {o.status === "mock_paid" ? (
                      <Button size="sm" variant="danger" busy={action.busy === `f-${o.id}`} onClick={() => act(`f-${o.id}`, () => api.mockRefund(venture.id, o.id, `refund-${o.id}`))}>Refund</Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="t-small text-muted">No mock orders yet.</p>}
      {recon && orders.length ? (
        <div className="border-t border-line pt-3 t-small">
          <p className="font-semibold">Reconciliation {recon.balanced ? "balances" : "has mismatches"}</p>
          <p className="text-muted">
            Charges {recon.totals.charge ?? 0}, synthetic fees {recon.totals.fee ?? 0}, refunds {recon.totals.refund ?? 0}, mock payout {recon.totals.payout ?? 0}.
          </p>
          {recon.mismatches.length ? <ul className="mt-1 list-disc pl-4 text-danger">{recon.mismatches.map((m) => <li key={m}>{m}</li>)}</ul> : null}
        </div>
      ) : null}
    </div>
  );
}
