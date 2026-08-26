function getThemeValue(name, fallback) {
  const value = getComputedStyle(document.body).getPropertyValue(name).trim();
  return value || fallback;
}

function prepareCanvas(canvas) {
  if (!canvas) {
    return null;
  }

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  return { ctx, width: rect.width, height: rect.height };
}

function drawEmpty(canvas, label) {
  const prepared = prepareCanvas(canvas);
  if (!prepared) {
    return;
  }

  const { ctx, width, height } = prepared;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = getThemeValue("--muted", "#6b7280");
  ctx.font = "600 15px Avenir Next, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(label, width / 2, height / 2);
}

export function drawBarChart(canvas, items) {
  if (!items || !items.length) {
    drawEmpty(canvas, "Complete a round to populate this chart.");
    return;
  }

  const prepared = prepareCanvas(canvas);
  if (!prepared) {
    return;
  }

  const { ctx, width, height } = prepared;
  const accent = getThemeValue("--accent", "#f0673a");
  const secondary = getThemeValue("--secondary", "#0f9f96");
  const text = getThemeValue("--text", "#111827");
  const muted = getThemeValue("--muted", "#6b7280");

  ctx.clearRect(0, 0, width, height);

  const padding = { top: 18, right: 12, bottom: 52, left: 14 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const barWidth = chartWidth / Math.max(items.length * 1.7, 1);
  const gap = barWidth * 0.7;

  ctx.font = "600 13px Avenir Next, Segoe UI, sans-serif";
  ctx.textAlign = "center";

  items.forEach((item, index) => {
    const barHeight = (chartHeight * Math.max(item.value, 0)) / 100;
    const x = padding.left + index * (barWidth + gap) + gap * 0.5;
    const y = padding.top + chartHeight - barHeight;

    const gradient = ctx.createLinearGradient(x, y, x + barWidth, padding.top + chartHeight);
    gradient.addColorStop(0, index % 2 === 0 ? accent : secondary);
    gradient.addColorStop(1, "rgba(255,255,255,0.1)");

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, Math.max(barHeight, 10), 12);
    ctx.fill();

    ctx.fillStyle = text;
    ctx.fillText(String(Math.round(item.value)), x + barWidth / 2, y - 8);

    ctx.fillStyle = muted;
    ctx.fillText(item.label, x + barWidth / 2, height - 18);
  });
}

export function drawTrendChart(canvas, points) {
  if (!points || points.length < 2) {
    drawEmpty(canvas, "Two completed rounds are enough to start seeing a trend.");
    return;
  }

  const prepared = prepareCanvas(canvas);
  if (!prepared) {
    return;
  }

  const { ctx, width, height } = prepared;
  const accent = getThemeValue("--accent", "#f0673a");
  const secondary = getThemeValue("--secondary", "#0f9f96");
  const text = getThemeValue("--text", "#111827");
  const muted = getThemeValue("--muted", "#6b7280");

  ctx.clearRect(0, 0, width, height);

  const padding = { top: 22, right: 16, bottom: 40, left: 18 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
  ctx.lineWidth = 1;
  for (let index = 0; index <= 4; index += 1) {
    const y = padding.top + (chartHeight / 4) * index;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  const xStep = chartWidth / (points.length - 1);
  const coordinates = points.map((point, index) => {
    const x = padding.left + index * xStep;
    const y = padding.top + chartHeight - (chartHeight * point.score) / 100;
    return { x, y, point };
  });

  ctx.beginPath();
  coordinates.forEach((coordinate, index) => {
    if (index === 0) {
      ctx.moveTo(coordinate.x, coordinate.y);
    } else {
      ctx.lineTo(coordinate.x, coordinate.y);
    }
  });
  ctx.lineWidth = 3;
  ctx.strokeStyle = accent;
  ctx.stroke();

  ctx.fillStyle = secondary;
  coordinates.forEach((coordinate) => {
    ctx.beginPath();
    ctx.arc(coordinate.x, coordinate.y, 4.5, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.font = "600 12px Avenir Next, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  coordinates.forEach((coordinate) => {
    ctx.fillStyle = muted;
    ctx.fillText(coordinate.point.label, coordinate.x, height - 12);
    ctx.fillStyle = text;
    ctx.fillText(String(Math.round(coordinate.point.score)), coordinate.x, coordinate.y - 12);
  });
}
