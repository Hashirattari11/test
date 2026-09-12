import { Suspense } from "react";
import AuthCallbackClient from "../../../components/AuthCallbackClient";

export const metadata = {
  robots: { index: false, follow: false },
};

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackLoading />}>
      <AuthCallbackClient />
    </Suspense>
  );
}

function CallbackLoading() {
  return (
    <div className="lp-login-wrap">
      <div className="lp-card" style={{ textAlign: "center", padding: "44px 28px" }}>
        <div className="auth-spinner" aria-hidden="true" />
        <p style={{ color: "var(--muted)", fontSize: 14 }}>Securing your session…</p>
      </div>
    </div>
  );
}