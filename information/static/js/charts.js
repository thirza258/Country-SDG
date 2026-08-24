/*
 * Small SVG chart helpers for the SDG site.
 *
 * No external library and no build step. The one rule that matters here:
 * a missing value is a gap in the line, never a zero. Points arrive as
 * [{year, value}] where value may be null.
 */
window.SDGCharts = (function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";

  function el(name, attrs, text) {
    const node = document.createElementNS(NS, name);
    for (const key in attrs) {
      if (attrs[key] !== null && attrs[key] !== undefined) {
        node.setAttribute(key, attrs[key]);
      }
    }
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function segments(points) {
    // Split a series into runs of consecutive non-null values.
    const runs = [];
    let run = [];
    points.forEach(function (point) {
      if (point.value === null || point.value === undefined) {
        if (run.length) runs.push(run);
        run = [];
      } else {
        run.push(point);
      }
    });
    if (run.length) runs.push(run);
    return runs;
  }

  function niceTicks(min, max, count) {
    const span = max - min || 1;
    const rough = span / count;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
    const step = [1, 2, 2.5, 5, 10].map(function (m) { return m * magnitude; })
      .find(function (candidate) { return candidate >= rough; }) || magnitude * 10;
    const ticks = [];
    for (let value = Math.ceil(min / step) * step; value <= max + 1e-9; value += step) {
      ticks.push(Math.round(value * 100) / 100);
    }
    return ticks;
  }

  function lineChart(container, config) {
    if (!container) return;

    const series = (config.series || []).filter(function (item) {
      return item.points && item.points.some(function (p) { return p.value !== null; });
    });
    if (!series.length) {
      container.innerHTML = '<p class="chart-empty">No series to plot.</p>';
      return;
    }

    const margin = { top: 16, right: 16, bottom: 34, left: 44 };
    const height = Number(container.dataset.height || 300);

    const values = [];
    const years = [];
    series.forEach(function (item) {
      item.points.forEach(function (point) {
        years.push(point.year);
        if (point.value !== null && point.value !== undefined) values.push(point.value);
      });
    });

    const xMin = Math.min.apply(null, years);
    const xMax = Math.max.apply(null, years);

    // Scores are a 0-100 distance-to-target measure, so the axis runs the full
    // range. A zoomed axis would make a two-point move look like a transformation.
    let yMin = 0;
    let yMax = 100;
    if (config.autoScale) {
      yMin = Math.min.apply(null, values);
      yMax = Math.max.apply(null, values);
      const pad = Math.max((yMax - yMin) * 0.12, 2);
      yMin = Math.max(0, Math.floor(yMin - pad));
      yMax = Math.min(100, Math.ceil(yMax + pad));
    }

    const svg = el("svg", {
      class: "chart-svg",
      role: "img",
      preserveAspectRatio: "none",
      "aria-label": config.ariaLabel || "Line chart",
    });
    const tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    tooltip.hidden = true;

    container.innerHTML = "";
    container.appendChild(svg);
    container.appendChild(tooltip);

    if (config.series.length > 1) {
      const legend = document.createElement("figcaption");
      legend.className = "chart-legend";
      series.forEach(function (item) {
        const entry = document.createElement("span");
        entry.innerHTML =
          '<i style="background:' + item.color + (item.dashed ? ";opacity:.65" : "") + '"></i>' +
          item.label;
        legend.appendChild(entry);
      });
      container.appendChild(legend);
    }

    function render() {
      const width = Math.max(container.clientWidth || 640, 280);
      const innerW = width - margin.left - margin.right;
      const innerH = height - margin.top - margin.bottom;

      svg.setAttribute("viewBox", "0 0 " + width + " " + height);
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.innerHTML = "";

      const x = function (year) {
        return margin.left + ((year - xMin) / (xMax - xMin || 1)) * innerW;
      };
      const y = function (value) {
        return margin.top + innerH - ((value - yMin) / (yMax - yMin || 1)) * innerH;
      };

      niceTicks(yMin, yMax, 5).forEach(function (tick) {
        svg.appendChild(el("line", {
          class: "grid", x1: margin.left, x2: margin.left + innerW, y1: y(tick), y2: y(tick),
        }));
        svg.appendChild(el("text", {
          class: "tick", x: margin.left - 8, y: y(tick) + 4, "text-anchor": "end",
        }, tick));
      });

      const xStep = Math.max(1, Math.round((xMax - xMin) / 6));
      for (let year = xMin; year <= xMax; year += xStep) {
        svg.appendChild(el("text", {
          class: "tick", x: x(year), y: height - 12, "text-anchor": "middle",
        }, year));
      }
      if ((xMax - xMin) % xStep !== 0) {
        svg.appendChild(el("text", {
          class: "tick", x: x(xMax), y: height - 12, "text-anchor": "end",
        }, xMax));
      }

      series.forEach(function (item) {
        segments(item.points).forEach(function (run) {
          if (run.length === 1) {
            svg.appendChild(el("circle", {
              cx: x(run[0].year), cy: y(run[0].value), r: 3, fill: item.color,
            }));
            return;
          }
          const d = run.map(function (point, i) {
            return (i ? "L" : "M") + x(point.year) + " " + y(point.value);
          }).join(" ");
          svg.appendChild(el("path", {
            d: d,
            fill: "none",
            stroke: item.color,
            "stroke-width": item.dashed ? 1.75 : 2.5,
            "stroke-dasharray": item.dashed ? "5 4" : null,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          }));
        });
      });

      // One hover guide for the whole chart, snapping to the nearest year.
      const guide = el("line", { class: "guide", y1: margin.top, y2: margin.top + innerH, opacity: 0 });
      svg.appendChild(guide);
      const markers = series.map(function (item) {
        const dot = el("circle", { r: 4, fill: item.color, stroke: "var(--surface)", "stroke-width": 2, opacity: 0 });
        svg.appendChild(dot);
        return dot;
      });

      svg.addEventListener("pointermove", function (event) {
        const box = svg.getBoundingClientRect();
        const px = ((event.clientX - box.left) / box.width) * width;
        const year = Math.round(xMin + ((px - margin.left) / innerW) * (xMax - xMin));
        if (year < xMin || year > xMax) return;

        guide.setAttribute("x1", x(year));
        guide.setAttribute("x2", x(year));
        guide.setAttribute("opacity", 1);

        let rows = "";
        series.forEach(function (item, i) {
          const point = item.points.find(function (p) { return p.year === year; });
          if (point && point.value !== null && point.value !== undefined) {
            markers[i].setAttribute("cx", x(point.year));
            markers[i].setAttribute("cy", y(point.value));
            markers[i].setAttribute("opacity", 1);
            rows += '<span><i style="background:' + item.color + '"></i>' +
              item.label + " <b>" + point.value + "</b></span>";
          } else {
            markers[i].setAttribute("opacity", 0);
            rows += '<span><i style="background:' + item.color + '"></i>' +
              item.label + " <b>not assessed</b></span>";
          }
        });

        tooltip.innerHTML = "<strong>" + year + "</strong>" + rows;
        tooltip.hidden = false;
        const left = Math.min(Math.max(x(year) - 70, 4), width - 160);
        tooltip.style.left = left + "px";
        tooltip.style.top = margin.top + "px";
      });

      svg.addEventListener("pointerleave", function () {
        guide.setAttribute("opacity", 0);
        markers.forEach(function (dot) { dot.setAttribute("opacity", 0); });
        tooltip.hidden = true;
      });
    }

    render();
    if (window.ResizeObserver) {
      let frame = null;
      new ResizeObserver(function () {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(render);
      }).observe(container);
    } else {
      window.addEventListener("resize", render);
    }
  }

  function sparkline(container, points, color) {
    if (!container || !points) return;
    const usable = points.filter(function (p) { return p.value !== null && p.value !== undefined; });
    if (usable.length < 2) {
      container.innerHTML = '<span class="chart-empty">no series</span>';
      return;
    }

    const width = 180;
    const height = 34;
    const years = points.map(function (p) { return p.year; });
    const xMin = Math.min.apply(null, years);
    const xMax = Math.max.apply(null, years);
    const values = usable.map(function (p) { return p.value; });
    let lo = Math.min.apply(null, values);
    let hi = Math.max.apply(null, values);
    if (hi - lo < 4) { const mid = (hi + lo) / 2; lo = mid - 2; hi = mid + 2; }

    const x = function (year) { return ((year - xMin) / (xMax - xMin || 1)) * (width - 2) + 1; };
    const y = function (value) { return height - 3 - ((value - lo) / (hi - lo || 1)) * (height - 6); };

    const svg = el("svg", {
      class: "spark-svg",
      viewBox: "0 0 " + width + " " + height,
      preserveAspectRatio: "none",
      role: "img",
      "aria-label":
        "Score from " + usable[0].value + " in " + usable[0].year +
        " to " + usable[usable.length - 1].value + " in " + usable[usable.length - 1].year,
    });

    segments(points).forEach(function (run) {
      if (run.length < 2) return;
      const d = run.map(function (p, i) { return (i ? "L" : "M") + x(p.year) + " " + y(p.value); }).join(" ");
      svg.appendChild(el("path", { d: d, fill: "none", stroke: color, "stroke-width": 1.75, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    });

    const last = usable[usable.length - 1];
    svg.appendChild(el("circle", { cx: x(last.year), cy: y(last.value), r: 2.5, fill: color }));

    container.innerHTML = "";
    container.appendChild(svg);
    const caption = document.createElement("figcaption");
    caption.textContent = xMin + "–" + xMax;
    container.appendChild(caption);
  }

  function barChart(container, rows, options) {
    if (!container || !rows || !rows.length) return;
    const max = options && options.max ? options.max : 100;
    const list = document.createElement("ul");
    list.className = "bar-chart";
    rows.forEach(function (row) {
      const item = document.createElement("li");
      item.innerHTML =
        '<span class="bar-label">' + row.label + "</span>" +
        '<span class="bar-track"><span class="bar-fill" style="width:' +
        Math.round((row.value / max) * 1000) / 10 + "%;background:" + (row.color || "var(--accent)") + '"></span></span>' +
        '<span class="bar-value">' + row.value + "</span>";
      list.appendChild(item);
    });
    container.innerHTML = "";
    container.appendChild(list);
  }

  return { lineChart: lineChart, sparkline: sparkline, barChart: barChart };
})();
