"use client";

import { useState, type FormEvent } from "react";
import {
  Download,
  FileUp,
  Plus,
  ShieldCheck,
  UserCheck,
  UserX,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Skeleton,
  Table,
  TableWrap,
  Td,
  Th,
  statusTone,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage, formatDateTime, titleCase } from "@/lib/api";
import type { ImportCommit, ImportPreview, User } from "@/lib/types";

export default function AdminUsersPage() {
  const users = useApiData<User[]>("/admin/users?limit=200");
  const [createOpen, setCreateOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [temporary, setTemporary] = useState<{ email: string; password: string } | null>(null);
  const [resetInfo, setResetInfo] = useState<{ email: string; url: string; token: string } | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  // CSV import state
  const [kind, setKind] = useState<"students" | "teachers">("students");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [commit, setCommit] = useState<ImportCommit | null>(null);
  const [importBusy, setImportBusy] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  async function createAdmin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ user: User; temporary_password: string | null }>("/admin/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          full_name: fullName,
          role: "admin",
          password: password || null,
        }),
      });
      if (result.temporary_password) {
        setTemporary({ email: result.user.email, password: result.temporary_password });
      }
      setCreateOpen(false);
      setFullName("");
      setEmail("");
      setPassword("");
      await users.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatus(user: User) {
    try {
      await api(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: user.status === "active" ? "disabled" : "active",
        }),
      });
      await users.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  async function issuePasswordReset(user: User) {
    setActionBusy(`${user.id}:reset`);
    setError(null);
    try {
      const result = await api<{ reset_url: string; token: string }>(
        `/admin/users/${user.id}/password-reset`,
        { method: "POST" },
      );
      setResetInfo({ email: user.email, url: result.reset_url, token: result.token });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  }

  async function disableMfa(user: User) {
    if (!window.confirm(`Disable MFA for ${user.email}? All of their sessions will be revoked.`)) return;
    setActionBusy(`${user.id}:mfa`);
    setError(null);
    try {
      await api(`/admin/users/${user.id}/mfa-disable`, { method: "POST" });
      await users.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  }

  async function previewFile() {
    if (!file) return;
    setImportBusy("preview");
    setImportError(null);
    setPreview(null);
    setCommit(null);
    try {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", file);
      setPreview(await api<ImportPreview>("/admin/imports/preview", { method: "POST", body: form }));
    } catch (caught) {
      setImportError(errorMessage(caught));
    } finally {
      setImportBusy(null);
    }
  }

  async function commitFile() {
    if (!file) return;
    setImportBusy("commit");
    setImportError(null);
    try {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", file);
      const result = await api<ImportCommit>("/admin/imports/commit", { method: "POST", body: form });
      setCommit(result);
      setPreview(null);
      await users.reload();
    } catch (caught) {
      setImportError(errorMessage(caught));
    } finally {
      setImportBusy(null);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="User management"
        title="Accounts and provisioning"
        description="Administrators create every account. There is no public registration and no way to self-assign a privileged role."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={15} /> Add administrator
          </Button>
        }
      />

      {error ? (
        <div className="mb-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}
      {temporary ? (
        <div className="mb-4">
          <Alert tone="warning" title="Temporary password shown once">
            <p>
              Account <strong>{temporary.email}</strong> was created with the password{" "}
              <code className="rounded bg-white px-1.5 py-0.5 font-mono text-xs">{temporary.password}</code>.
              Share it through a secure channel; the user must change it at first sign-in.
            </p>
            <button type="button" className="mt-2 font-semibold underline" onClick={() => setTemporary(null)}>
              I have recorded it
            </button>
          </Alert>
        </div>
      ) : null}
      {resetInfo ? (
        <div className="mb-4">
          <Alert tone="warning" title="Password reset token shown once">
            <p>
              Send this single-use link to <strong>{resetInfo.email}</strong> through an approved
              channel. It expires in 60 minutes and revokes their sessions when used.
            </p>
            <p className="mt-2 break-all font-mono text-[11px] text-ink">{resetInfo.url}</p>
            <p className="mt-1 break-all font-mono text-[10px] text-muted">Token: {resetInfo.token}</p>
            <button type="button" className="mt-2 font-semibold underline" onClick={() => setResetInfo(null)}>
              Dismiss
            </button>
          </Alert>
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader
            title="All accounts"
            description="Role and status are enforced by the backend on every request."
          />
          {users.loading ? (
            <div className="p-4">
              <Skeleton className="h-64" />
            </div>
          ) : !users.data?.length ? (
            <p className="p-5 text-sm text-muted">No accounts yet.</p>
          ) : (
            <TableWrap>
              <Table>
                <thead>
                  <tr>
                    <Th>Account</Th>
                    <Th>Role</Th>
                    <Th>Status</Th>
                    <Th className="hidden sm:table-cell">Last sign-in</Th>
                    <Th />
                  </tr>
                </thead>
                <tbody>
                  {users.data.map((user) => (
                    <tr key={user.id}>
                      <Td>
                        <p className="font-medium text-ink">{user.full_name}</p>
                        <p className="text-[11px] text-muted">{user.email}</p>
                      </Td>
                      <Td>
                        <Badge tone={statusTone(user.role)}>{titleCase(user.role)}</Badge>
                      </Td>
                      <Td>
                        <div className="flex flex-col gap-1">
                          <Badge tone={statusTone(user.status)}>{titleCase(user.status)}</Badge>
                          {user.must_change_password ? (
                            <span className="text-[10px] text-[#B54708]">temporary password</span>
                          ) : null}
                          {user.mfa_enabled ? (
                            <span className="text-[10px] font-medium text-[#067647]">MFA enabled</span>
                          ) : null}
                        </div>
                      </Td>
                      <Td className="hidden text-[11px] text-muted sm:table-cell">
                        {formatDateTime(user.last_login_at)}
                      </Td>
                      <Td className="text-right">
                        <div className="flex flex-wrap justify-end gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => void issuePasswordReset(user)}
                            loading={actionBusy === `${user.id}:reset`}
                          >
                            Reset password
                          </Button>
                          {user.mfa_enabled ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => void disableMfa(user)}
                              loading={actionBusy === `${user.id}:mfa`}
                            >
                              Disable MFA
                            </Button>
                          ) : null}
                          <Button
                            size="sm"
                            variant={user.status === "active" ? "ghost" : "secondary"}
                            onClick={() => void toggleStatus(user)}
                          >
                            {user.status === "active" ? (
                              <>
                                <UserX size={13} /> Disable
                              </>
                            ) : (
                              <>
                                <UserCheck size={13} /> Enable
                              </>
                            )}
                          </Button>
                        </div>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </TableWrap>
          )}
        </Card>

        <Card>
          <CardHeader
            title="CSV account import"
            description="Preview validates every row before a transactional commit."
            action={
              <a
                href={`/api/v1/admin/imports/template?kind=${kind}`}
                className="inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline"
              >
                <Download size={13} /> Template
              </a>
            }
          />
          <div className="space-y-3 p-4">
            <Field label="Import type">
              <Select
                value={kind}
                onChange={(event) => {
                  setKind(event.target.value as "students" | "teachers");
                  setPreview(null);
                  setCommit(null);
                }}
              >
                <option value="students">Students</option>
                <option value="teachers">Teachers</option>
              </Select>
            </Field>
            <Field label="CSV file" hint="UTF-8, maximum 2 MB. No passwords are stored in the file; temporary passwords are generated once.">
              <Input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setPreview(null);
                  setCommit(null);
                }}
              />
            </Field>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => void previewFile()}
                loading={importBusy === "preview"}
                disabled={!file}
              >
                <FileUp size={14} /> Preview
              </Button>
              <Button className="flex-1" onClick={() => void commitFile()} loading={importBusy === "commit"} disabled={!preview || preview.valid_rows === 0}>
                Commit valid rows
              </Button>
            </div>
            {importError ? <Alert tone="danger">{importError}</Alert> : null}

            {preview ? (
              <div className="rounded-lg border border-line">
                <div className="flex flex-wrap gap-2 border-b border-line px-3 py-2 text-[11px]">
                  <Badge tone="blue">{preview.total_rows} rows</Badge>
                  <Badge tone="green">{preview.valid_rows} valid</Badge>
                  <Badge tone="red">{preview.invalid_rows} invalid</Badge>
                  <Badge tone="amber">{preview.duplicate_rows} duplicates</Badge>
                </div>
                <ul className="max-h-56 divide-y divide-line overflow-y-auto">
                  {preview.rows.map((row) => (
                    <li key={row.row_number} className="px-3 py-2 text-[11px]">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-ink">
                          Row {row.row_number} · {row.data.email || "missing email"}
                        </span>
                        <Badge tone={row.ok ? "green" : "red"}>{row.ok ? "Valid" : "Invalid"}</Badge>
                      </div>
                      {row.errors.length ? (
                        <p className="mt-0.5 text-[#912018]">{row.errors.join(" ")}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {commit ? (
              <Alert tone={commit.error_rows ? "warning" : "success"} title="Import complete">
                <p>
                  {commit.success_rows} account(s) created, {commit.error_rows} row(s) skipped.
                </p>
                {commit.created_users.length ? (
                  <ul className="mt-2 space-y-1">
                    {commit.created_users.map((created) => (
                      <li key={created.id} className="font-mono text-[11px]">
                        {created.email} · {created.temporary_password ?? "(password not generated)"}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </Alert>
            ) : null}
          </div>
        </Card>
      </div>

      <Card className="mt-5">
        <CardHeader title="Provisioning policy" action={<ShieldCheck size={16} className="text-muted" />} />
        <ul className="grid gap-2 p-4 text-xs text-muted sm:grid-cols-2">
          <li>• Teachers and students receive one-time passwords and must change them.</li>
          <li>• Public registration cannot create teacher or administrator roles.</li>
          <li>• CSV commits are transactional: a database conflict rolls back the whole batch.</li>
          <li>• Every provisioning action is written to the audit trail.</li>
        </ul>
      </Card>

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Provision an administrator"
        description="Administrator accounts are deliberately separate from teaching accounts."
      >
        <form onSubmit={createAdmin} className="space-y-4">
          <Field label="Full name" required>
            <Input value={fullName} onChange={(event) => setFullName(event.target.value)} required minLength={2} />
          </Field>
          <Field label="Email" required>
            <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </Field>
          <Field label="Password" hint="Leave blank to generate a one-time password that is displayed only once.">
            <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              Create administrator
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
