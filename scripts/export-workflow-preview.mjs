import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { mkdir, rm } from "node:fs/promises";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const htmlPath = path.resolve(root, process.argv[2] ?? "growthops-workflow-preview.html");
const outputDir = path.resolve(root, process.argv[3] ?? "exports");
const tempDir = path.join(outputDir, ".video-temp");
const width = Number(process.env.EXPORT_WIDTH ?? 432);
const seconds = Number(process.env.EXPORT_SECONDS ?? 6);
const mode = process.env.EXPORT_MODE ?? "full-video";
const outputName =
  process.env.EXPORT_NAME ??
  {
    "full-video": "growthops-workflow-preview.webm",
    "scroll-video": "growthops-workflow-readable.webm",
    pdf: "growthops-workflow-full.pdf",
    png: "growthops-workflow-full.png",
  }[mode];

await rm(tempDir, { recursive: true, force: true });
await mkdir(outputDir, { recursive: true });

const launchOptions = { headless: true };

if (process.env.CHROMIUM_PATH) {
  launchOptions.executablePath = process.env.CHROMIUM_PATH;
}

const browser = await chromium.launch(launchOptions);
const measureContext = await browser.newContext({
  viewport: { width, height: 884 },
  deviceScaleFactor: 1,
});
const measurePage = await measureContext.newPage();
await measurePage.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
const height = await measurePage.evaluate(() =>
  Math.ceil(Math.max(document.body.scrollHeight, document.documentElement.scrollHeight))
);
await measureContext.close();

if (mode === "pdf" || mode === "png") {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: Number(process.env.EXPORT_SCALE ?? 2),
  });
  const page = await context.newPage();
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);

  const outputPath = path.join(outputDir, outputName);
  if (mode === "pdf") {
    await page.pdf({
      path: outputPath,
      width: `${width}px`,
      height: `${height}px`,
      printBackground: true,
      margin: { top: "0px", right: "0px", bottom: "0px", left: "0px" },
    });
  } else {
    await page.screenshot({ path: outputPath, fullPage: true });
  }

  await context.close();
  await browser.close();
  console.log(outputPath);
  process.exit(0);
}

await mkdir(tempDir, { recursive: true });

const viewportHeight = mode === "scroll-video" ? Number(process.env.EXPORT_VIEWPORT_HEIGHT ?? 884) : height;
const context = await browser.newContext({
  viewport: { width, height: viewportHeight },
  deviceScaleFactor: 1,
  recordVideo: {
    dir: tempDir,
    size: { width, height: viewportHeight },
  },
});

const page = await context.newPage();
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });

if (mode === "scroll-video") {
  await page.evaluate(async (durationSeconds) => {
    const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    const pause = 1200;

    await new Promise((resolve) => setTimeout(resolve, pause));
    await new Promise((resolve) => {
      const startedAt = performance.now();
      const duration = durationSeconds * 1000;

      const tick = (now) => {
        const progress = Math.min((now - startedAt) / duration, 1);
        const eased = 0.5 - Math.cos(progress * Math.PI) / 2;
        window.scrollTo(0, maxScroll * eased);

        if (progress < 1) {
          requestAnimationFrame(tick);
        } else {
          resolve();
        }
      };

      requestAnimationFrame(tick);
    });
    await new Promise((resolve) => setTimeout(resolve, pause));
  }, seconds);
} else {
  await page.waitForTimeout(seconds * 1000);
}

const video = page.video();
await context.close();

if (!video) {
  throw new Error("Playwright did not produce a video recording.");
}

await video.saveAs(path.join(outputDir, outputName));
await browser.close();
await rm(tempDir, { recursive: true, force: true });

console.log(path.join(outputDir, outputName));
