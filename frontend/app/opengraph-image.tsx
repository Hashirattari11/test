import { ImageResponse } from "next/og";
import { SITE_NAME, SITE_DESCRIPTION } from "@/lib/site";

export const runtime = "edge";
export const alt = SITE_NAME;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "center",
          padding: "0 80px",
          background: "linear-gradient(135deg, #0f0a2e 0%, #1a1145 50%, #0d1b3e 100%)",
          color: "white",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 28 }}>
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 18,
              background: "linear-gradient(135deg, #635bff, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <span style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.02em" }}>{SITE_NAME}</span>
        </div>
        <div style={{ fontSize: 52, fontWeight: 800, letterSpacing: "-0.02em", lineHeight: 1.15 }}>
          Never let a broken API
          <br />
          catch you off guard
        </div>
        <div style={{ fontSize: 26, color: "#a78bfa", marginTop: 22 }}>{SITE_DESCRIPTION}</div>
      </div>
    ),
    size,
  );
}