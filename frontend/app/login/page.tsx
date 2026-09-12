import type { Metadata } from "next";
import LoginClient from "../../components/LoginClient";

export const metadata: Metadata = {
  title: "Log in — AutoFix",
  description: "Sign in to AutoFix with your GitHub account to monitor the APIs your repos depend on.",
};

export default function LoginPage() {
  return <LoginClient />;
}