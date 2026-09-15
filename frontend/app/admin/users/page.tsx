"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAdminUsers, AdminUser } from "../../../lib/admin";
import { formatDate, Spinner } from "../../../components/ui";

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminUsers()
      .then((r) => setUsers(r.users))
      .catch((e) => setError(e?.message || "Failed to load users"));
  }, []);

  if (error) {
    return (
      <main className="container page">
        <h1>Users</h1>
        <p className="muted">Could not load users (admin-only). {error}</p>
      </main>
    );
  }

  if (users === null) {
    return (
      <main className="container page" style={{ textAlign: "center", paddingTop: 80 }}>
        <Spinner /> Loading…
      </main>
    );
  }

  return (
    <main className="container page">
      <div className="row" style={{ marginBottom: 24, alignItems: "center" }}>
        <div>
          <h1>Users</h1>
          <p className="muted" style={{ margin: 0 }}>
            Read-only account directory.
          </p>
        </div>
      </div>

      {users.length === 0 ? (
        <div className="card" style={{ padding: 32, textAlign: "center" }}>
          <p className="muted" style={{ margin: 0 }}>
            No users found.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="table responsive-cards" style={{ minWidth: 700 }}>
            <thead>
              <tr>
                <th>Email</th>
                <th>GitHub</th>
                <th>Plan</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td data-label="Email">{u.email}</td>
                  <td data-label="GitHub">{u.github_login || "—"}</td>
                  <td data-label="Plan">
                    <span className="badge badge-neutral">{u.plan || "free"}</span>
                  </td>
                  <td data-label="Role">
                    {u.is_admin ? (
                      <span className="badge badge-success">admin</span>
                    ) : u.is_agency ? (
                      <span className="badge badge-warn">agency</span>
                    ) : (
                      <span className="badge badge-neutral">customer</span>
                    )}
                  </td>
                  <td data-label="Joined" className="muted">{u.created_at ? formatDate(u.created_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
