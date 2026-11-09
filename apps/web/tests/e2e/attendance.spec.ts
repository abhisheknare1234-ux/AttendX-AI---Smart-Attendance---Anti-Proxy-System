import { expect, test, type Page } from "@playwright/test";

const TEACHER = { email: "teacher@attendx.dev", password: "SeedTeacher!2345" };
const STUDENT = { email: "student1@attendx.dev", password: "SeedStudent!2345" };
const ADMIN = { email: "admin@attendx.dev", password: "SeedAdmin!2345" };
const BASE = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000";

async function login(page: Page, email: string, password: string, home: RegExp) {
  await page.goto("/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(home);
}

test("administrator can open configuration, reports, and verification screens", async ({ page }) => {
  await login(page, ADMIN.email, ADMIN.password, /\/admin/);
  await expect(page.getByRole("heading", { name: /Institutional overview/i })).toBeVisible();

  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: /Accounts and provisioning/i })).toBeVisible();
  await expect(page.getByText("teacher@attendx.dev").first()).toBeVisible();

  await page.goto("/admin/policies");
  await expect(page.getByRole("heading", { name: /Institutional attendance policies/i })).toBeVisible();
  await expect(page.getByText("Demo default policy").first()).toBeVisible();

  await page.goto("/admin/verification");
  await expect(page.getByRole("heading", { name: /Identity provider status/i })).toBeVisible();
  await expect(page.getByText("Face verification provider").first()).toBeVisible();

  await page.goto("/admin/reports");
  await expect(page.getByRole("heading", { name: /Attendance reports/i })).toBeVisible();
});

test("teacher opens a session and student completes a verified mobile check-in", async ({
  page,
  browser,
}) => {
  await login(page, TEACHER.email, TEACHER.password, /\/teacher/);
  await page.goto("/teacher/sessions/new");
  await expect(page.getByRole("heading", { name: /Configure a verified attendance session/i })).toBeVisible();

  const classSelect = page.getByTestId("class-select");
  await expect(classSelect.locator("option")).not.toHaveCount(1);
  await classSelect.selectOption({ index: 1 });
  await expect(page.getByTestId("subject-select")).not.toHaveValue("");
  const classroom = page.getByTestId("classroom-select");
  if ((await classroom.inputValue()) === "") {
    await classroom.selectOption({ index: 1 });
  }
  await page.getByTestId("create-session").click();
  await page.waitForURL(/\/teacher\/sessions\/[0-9a-f-]+$/);

  await expect(page.getByTestId("open-session")).toBeVisible();
  await page.getByTestId("open-session").click();
  const pin = (await page.getByTestId("session-pin").textContent())?.trim() ?? "";
  expect(pin).toMatch(/^\d{4,10}$/);
  const link = (await page.getByTestId("session-link").textContent())?.trim() ?? "";
  expect(link).toContain("/attend/");
  expect(link.startsWith(BASE)).toBeTruthy();
  await expect(page.getByTestId("attendance-qr")).toBeVisible();

  const context = await browser.newContext({
    baseURL: BASE,
    viewport: { width: 390, height: 844 },
    geolocation: { latitude: 18.5204, longitude: 73.8567 },
    permissions: ["geolocation"],
  });
  await context.grantPermissions(["geolocation"], { origin: BASE });
  const student = await context.newPage();
  await login(student, STUDENT.email, STUDENT.password, /\/student/);
  await student.goto(link);
  await expect(student.getByTestId("begin-check-in")).toBeVisible();
  await student.getByTestId("begin-check-in").click();

  await student.getByTestId("pin-input").fill(pin);
  await student.getByTestId("verify-pin").click();
  await expect(student.getByTestId("share-location")).toBeVisible();
  await student.getByTestId("share-location").click();
  await expect(student.getByTestId("finalize-attendance")).toBeVisible();
  await student.getByTestId("finalize-attendance").click();
  await expect(student.getByTestId("attendance-result")).toHaveText(/Attendance confirmed/i);
  await expect(student.getByText(/AX-/).first()).toBeVisible();
  await context.close();

  await expect(page.getByTestId("accepted-count")).toContainText("1", { timeout: 15_000 });
});

test("student mobile shell exposes the scanner route", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, STUDENT.email, STUDENT.password, /\/student/);
  await expect(page.getByRole("navigation", { name: "Student navigation" })).toBeVisible();
  await page.getByRole("link", { name: /Scan/i }).click();
  await expect(page.getByRole("heading", { name: /Check in to the current session/i })).toBeVisible();
  await expect(page.getByText(/camera/i).first()).toBeVisible();
});
