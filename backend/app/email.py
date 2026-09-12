"""Email templates and sending for agency invites + confirmations.

All sends route through ``email_service.send_transactional_email`` so the
delivery is logged to ``email_deliveries`` (master pass §15 fix). The template
functions return the dict result from the email service.
"""
from __future__ import annotations

from .config import settings
from .email_service import send_transactional_email


def _dash_url() -> str:
    return settings.frontend_base_url.rstrip("/") + "/dashboard"


def send_invite_email(
    to_email: str,
    agency_name: str,
    client_name: str,
    auth_link: str,
    user_id: str | None = None,
) -> dict:
    """Send an agency invitation email with authorization link."""
    subject = f"{agency_name} invited you to AutoFix API"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f7f7fb;">
        <div style="max-width: 520px; margin: 40px auto; background: white; border-radius: 12px; border: 1px solid #e6e6ef; overflow: hidden;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #635bff, #8b5cf6); padding: 32px; text-align: center;">
                <h1 style="color: white; font-size: 24px; margin: 0;">AutoFix API</h1>
                <p style="color: rgba(255,255,255,0.8); font-size: 14px; margin: 8px 0 0;">Repository Access Authorization</p>
            </div>

            <!-- Body -->
            <div style="padding: 32px;">
                <p style="font-size: 16px; color: #1a1a2e; margin: 0 0 16px;">Hi {client_name},</p>

                <p style="font-size: 15px; color: #4b5563; line-height: 1.6; margin: 0 0 20px;">
                    <strong>{agency_name}</strong> wants to connect your GitHub repository to AutoFix API
                    to monitor it for breaking API changes from providers like Stripe, Shopify, Twilio, and SendGrid.
                </p>

                <p style="font-size: 15px; color: #4b5563; line-height: 1.6; margin: 0 0 24px;">
                    Click the button below to authorize access. This is a one-time process — you won't need to create an account.
                </p>

                <!-- CTA Button -->
                <div style="text-align: center; margin: 0 0 24px;">
                    <a href="{auth_link}"
                       style="display: inline-block; padding: 14px 32px; background: #635bff; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">
                        Authorize with GitHub
                    </a>
                </div>

                <!-- Info Box -->
                <div style="background: #f7f7fb; border-radius: 8px; padding: 16px; margin: 0 0 20px;">
                    <p style="font-size: 13px; color: #6b7280; margin: 0 0 8px;"><strong>What happens next?</strong></p>
                    <ul style="font-size: 13px; color: #6b7280; margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 4px;">You'll authorize AutoFix to read your repository</li>
                        <li style="margin-bottom: 4px;">You'll select which repo(s) to share</li>
                        <li style="margin-bottom: 4px;">{agency_name} will monitor for API breaking changes</li>
                        <li>You can revoke access anytime from your GitHub settings</li>
                    </ul>
                </div>

                <p style="font-size: 13px; color: #9ca3af; margin: 0;">
                    This link expires in 7 days. If you didn't expect this email, you can safely ignore it.
                </p>
            </div>

            <!-- Footer -->
            <div style="padding: 16px 32px; border-top: 1px solid #e6e6ef; text-align: center;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                    AutoFix API — Detect. Alert. Fix. Automatically.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
    {agency_name} invited you to AutoFix API

    Hi {client_name},

    {agency_name} wants to connect your GitHub repository to AutoFix API
    to monitor it for breaking API changes.

    Click the link below to authorize access:
    {auth_link}

    What happens next?
    - You'll authorize AutoFix to read your repository
    - You'll select which repo(s) to share
    - {agency_name} will monitor for API breaking changes
    - You can revoke access anytime from your GitHub settings

    This link expires in 7 days. If you didn't expect this email, you can safely ignore it.

    AutoFix API — Detect. Alert. Fix. Automatically.
    """

    return send_transactional_email(
        user_id=user_id,
        recipient=to_email,
        alert_type="agency_invite",
        subject=subject,
        html=html,
        text=text,
    )


def send_detection_confirmation_email(
    to_email: str,
    repo_name: str,
    api_counts: dict[str, int],
    user_id: str | None = None,
) -> dict:
    """Send a one-time confirmation email after a repo's first scan finds API detections.

    Args:
        to_email: Recipient email.
        repo_name: e.g. "hashirattari73/my-app".
        api_counts: e.g. {"stripe": 3, "github": 1} — API name to file count.
        user_id: Owner user id (for delivery logging).
    """
    subject = f"\u2705 We scanned {repo_name} \u2014 here's what we found"

    api_rows = "\n".join(
        f'  <tr><td style="padding:8px 12px;border-bottom:1px solid #e6e6ef;font-weight:600;color:#1a1a2e;">{api}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #e6e6ef;color:#4b5563;">{count} file{"s" if count != 1 else ""}</td></tr>'
        for api, count in sorted(api_counts.items())
    )
    api_text = "\n".join(f"  - {api}: {count} file{'s' if count != 1 else ''}" for api, count in sorted(api_counts.items()))

    html = f"""\
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f7f7fb;">
      <div style="max-width:520px;margin:40px auto;background:white;border-radius:12px;border:1px solid #e6e6ef;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#635bff,#8b5cf6);padding:32px;text-align:center;">
          <h1 style="color:white;font-size:22px;margin:0;">\u2705 Scan Complete</h1>
          <p style="color:rgba(255,255,255,0.85);font-size:14px;margin:8px 0 0;">{repo_name}</p>
        </div>
        <div style="padding:32px;">
          <p style="font-size:15px;color:#4b5563;line-height:1.6;margin:0 0 20px;">
            We scanned your repository and detected the following third-party APIs:
          </p>
          <table style="width:100%;border-collapse:collapse;margin:0 0 24px;border:1px solid #e6e6ef;border-radius:8px;overflow:hidden;">
            <thead><tr style="background:#f7f7fb;">
              <th style="padding:8px 12px;text-align:left;font-size:13px;color:#6b7280;">API</th>
              <th style="padding:8px 12px;text-align:left;font-size:13px;color:#6b7280;">Files</th>
            </tr></thead>
            <tbody>{api_rows}</tbody>
          </table>
          <div style="background:#f0fdf4;border-left:3px solid #22c55e;padding:12px 16px;border-radius:4px;margin:0 0 20px;">
            <p style="font-size:13px;color:#166534;margin:0;">
              <strong>What happens next?</strong><br/>
              We'll monitor these APIs' changelogs and alert you immediately if a breaking change affects your code. No action needed from you.
            </p>
          </div>
          <p style="font-size:13px;color:#9ca3af;margin:0;">
            You can manage this repo from your <a href="{_dash_url()}" style="color:#635bff;">dashboard</a>.
          </p>
        </div>
        <div style="padding:16px 32px;border-top:1px solid #e6e6ef;text-align:center;">
          <p style="font-size:12px;color:#9ca3af;margin:0;">AutoFix API \u2014 Detect. Alert. Fix. Automatically.</p>
        </div>
      </div>
    </body>
    </html>
    """

    text = f"""\
We scanned {repo_name} and found these APIs:

{api_text}

What happens next?
We'll monitor these APIs' changelogs and alert you if a breaking change affects your code.

Manage this repo from your dashboard: {_dash_url()}

AutoFix API \u2014 Detect. Alert. Fix. Automatically.
"""

    return send_transactional_email(
        user_id=user_id,
        recipient=to_email,
        alert_type="scan_results",
        subject=subject,
        html=html,
        text=text,
    )


def send_welcome_email(to_email: str, user_name: str, user_id: str | None = None) -> dict:
    """Send a welcome email after GitHub OAuth signup."""
    subject = "Welcome to AutoFix API!"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f7f7fb;">
        <div style="max-width: 520px; margin: 40px auto; background: white; border-radius: 12px; border: 1px solid #e6e6ef; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #635bff, #8b5cf6); padding: 32px; text-align: center;">
                <h1 style="color: white; font-size: 24px; margin: 0;">Welcome to AutoFix!</h1>
            </div>
            <div style="padding: 32px;">
                <p style="font-size: 16px; color: #1a1a2e; margin: 0 0 16px;">Hi {user_name},</p>
                <p style="font-size: 15px; color: #4b5563; line-height: 1.6; margin: 0 0 20px;">
                    Your account has been created. You can now connect your GitHub repositories
                    and start monitoring for breaking API changes.
                </p>
                <div style="text-align: center; margin: 0 0 20px;">
                    <a href="{_dash_url()}"
                       style="display: inline-block; padding: 14px 32px; background: #635bff; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        Go to Dashboard
                    </a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"Hi {user_name},\n\nYour AutoFix account is ready. Go to {_dash_url()} to get started."

    return send_transactional_email(
        user_id=user_id,
        recipient=to_email,
        alert_type="welcome",
        subject=subject,
        html=html,
        text=text,
    )
