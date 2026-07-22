"""Advanced Reports v3 - PDF, CSV, Markdown, combined reports, batch processing."""
import json, csv, io, asyncio
from datetime import datetime, timezone
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


class Report:
    def __init__(self, target, module=None):
        self.target = target
        self.module = module or "full"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.results = {}

    def add_result(self, module_name, data):
        self.results[module_name] = data

    def to_dict(self):
        return {"target": self.target, "module": self.module, "timestamp": self.timestamp, "results": self.results}

    def save_json(self):
        fn = f"{self.timestamp.replace(':','-')}_{self.target.replace('/','_')}.json"
        fp = REPORT_DIR / fn
        fp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str))
        return str(fp)

    def save_html(self):
        sections = []
        for mod, data in self.results.items():
            if data is None or data == []: continue
            s = f'<div class="module-section"><h2>{mod.upper()}</h2>'
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    s += _list_to_html_table(data)
                else:
                    s += "<ul>" + "".join(f"<li>{d}</li>" for d in data) + "</ul>"
            elif isinstance(data, dict):
                s += _dict_to_html_table(data)
            elif isinstance(data, str):
                s += f"<p>{data}</p>"
            s += "</div>"
            sections.append(s)
        html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>PrOSINT Report - {self.target}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:2rem}}
h1{{color:#58a6ff;margin-bottom:.5rem}}h2{{color:#7ee787;margin:1.5rem 0 .5rem;border-bottom:1px solid #30363d;padding-bottom:.3rem}}
.meta{{color:#8b949e;font-size:.9rem;margin-bottom:2rem}}table{{width:100%;border-collapse:collapse;margin:.5rem 0}}
th{{background:#161b22;color:#58a6ff;padding:.5rem;text-align:left;border:1px solid #30363d}}
td{{padding:.4rem .5rem;border:1px solid #30363d;word-break:break-all}}tr:hover{{background:#161b22}}
ul{{margin-left:1.5rem}}li{{padding:.2rem 0}}.module-section{{margin-bottom:1.5rem}}</style></head>
<body><h1>PrOSINT Report</h1><p class="meta">Target: {self.target} &bull; Module: {self.module} &bull; Generated: {self.timestamp}</p>{''.join(sections)}</body></html>"""
        fn = f"{self.timestamp.replace(':','-')}_{self.target.replace('/','_')}.html"
        fp = REPORT_DIR / fn
        fp.write_text(html)
        return str(fp)

    def to_csv(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Module", "Key", "Value"])
        for mod, data in self.results.items():
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (list, dict)):
                        writer.writerow([mod, k, json.dumps(v, default=str)[:500]])
                    else:
                        writer.writerow([mod, k, str(v)[:500]])
            elif isinstance(data, list):
                for item in data:
                    writer.writerow([mod, "", json.dumps(item, default=str)[:500]])
            else:
                writer.writerow([mod, "", str(data)[:500]])
        return output.getvalue()

    def save_csv(self):
        fn = f"{self.timestamp.replace(':','-')}_{self.target.replace('/','_')}.csv"
        fp = REPORT_DIR / fn
        fp.write_text(self.to_csv())
        return str(fp)

    def to_markdown(self):
        lines = [f"# PrOSINT Report: {self.target}", f"**Module**: {self.module} | **Generated**: {self.timestamp}", ""]
        for mod, data in self.results.items():
            lines.append(f"## {mod.upper()}")
            if isinstance(data, dict):
                lines.append(f"| Key | Value |")
                lines.append(f"|-----|-------|")
                for k, v in data.items():
                    val = str(v)[:200].replace("\n", " ").replace("|", "\\|")
                    lines.append(f"| {k} | {val} |")
            elif isinstance(data, list):
                for item in data:
                    lines.append(f"- {str(item)[:200]}")
            else:
                lines.append(str(data)[:500])
            lines.append("")
        return "\n".join(lines)

    def save_markdown(self):
        fn = f"{self.timestamp.replace(':','-')}_{self.target.replace('/','_')}.md"
        fp = REPORT_DIR / fn
        fp.write_text(self.to_markdown())
        return str(fp)

    def save_all(self):
        return {"html": self.save_html(), "json": self.save_json(), "csv": self.save_csv(), "markdown": self.save_markdown()}


def _list_to_html_table(data):
    if not data: return ""
    cols = list(data[0].keys())
    header = "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
    rows = []
    for row in data:
        rows.append("<tr>" + "".join(f"<td>{str(row.get(c, ''))}</td>" for c in cols) + "</tr>")
    return f"<table>{header}{''.join(rows)}</table>"

def _dict_to_html_table(data):
    rows = "".join(f"<tr><td>{k}</td><td>{str(v)}</td></tr>" for k, v in data.items())
    return f"<table><tr><th>Key</th><th>Value</th></tr>{rows}</table>"


async def batch_process(targets: list[str], module: str) -> dict:
    """Process multiple targets with the same module and return combined results."""
    results = {}
    from core import email as email_mod, username as username_mod, phone as phone_mod
    mod_map = {"email": email_mod, "username": username_mod, "phone": phone_mod}
    mod = mod_map.get(module)
    if not mod: return {"error": f"Unknown module: {module}"}
    func_map = {"email": "full_email_intel", "username": "full_username_intel", "phone": "deep_phone_intel"}
    func_name = func_map.get(module)
    if not func_name: return {"error": f"No func for {module}"}
    func = getattr(mod, func_name)
    for t in targets:
        try:
            r = await func(t.strip())
            results[t.strip()] = r
        except Exception as e:
            results[t.strip()] = {"error": str(e)}
    return {"module": module, "total_targets": len(targets), "completed": len(results), "results": results}
