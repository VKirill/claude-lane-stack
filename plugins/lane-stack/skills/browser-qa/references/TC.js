// case_digest: <sha256>
// target_fingerprint: <sha256>
async (page) => {
  const base = "BASE_URL";
  await page.goto(base + "/path");
  const btn = page.locator("role=button[name=/get started/i]");
  if ((await btn.count()) < 1) {
    throw new Error("missing selector: Get started");
  }
  await btn.click();
  if (!page.url().includes("/signup")) {
    throw new Error("expected /signup");
  }
};
