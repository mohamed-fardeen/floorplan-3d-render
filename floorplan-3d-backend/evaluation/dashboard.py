import json
import os
from typing import Dict, List, Any
from datetime import datetime

def generate_dashboard(results: List[Dict[str, Any]], aggregates: Dict[str, Any], categorization: Dict[str, Any], output_path: str):
    """
    Generates an HTML Quality Dashboard summarizing the evaluation run.
    """
    total_images = len(results)
    success_count = sum(1 for r in results if r.get("export_success"))
    success_rate = (success_count / total_images * 100) if total_images > 0 else 0
    
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <title>Pipeline Quality Dashboard</title>",
        "    <style>",
        "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 20px; background-color: #f9f9f9; color: #333; }",
        "        h1, h2, h3 { color: #2c3e50; }",
        "        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "        .metric { font-size: 24px; font-weight: bold; color: #2980b9; }",
        "        table { width: 100%; border-collapse: collapse; margin-top: 10px; }",
        "        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }",
        "        th { background-color: #f2f2f2; }",
        "        .success { color: #27ae60; font-weight: bold; }",
        "        .failure { color: #c0392b; font-weight: bold; }",
        "        .image-preview { max-width: 100%; height: auto; border: 1px solid #ddd; }",
        "    </style>",
        "</head>",
        "<body>",
        f"    <h1>Pipeline Quality Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>",
    ]
    
    # 1. High-Level Summary
    html.extend([
        "    <div class='card'>",
        "        <h2>Acceptance Criteria & Summary</h2>",
        f"        <p>Total Floor Plans Evaluated: <span class='metric'>{total_images}</span></p>",
        f"        <p>Export Success Rate: <span class='metric' style='color: {'#27ae60' if success_rate >= 90 else '#c0392b'}'>{success_rate:.1f}%</span> (Target: >=90%)</p>",
        "    </div>"
    ])
    
    # 2. Performance Aggregates
    html.append("    <div class='card'><h2>Performance Profiling</h2><table><tr><th>Stage</th><th>Avg Time (s)</th><th>Median Time (s)</th><th>p95 Time (s)</th><th>Avg Mem (MB)</th></tr>")
    for key, val in aggregates.items():
        if "_time_s" in key:
            stage = key.replace("_time_s", "")
            mem_key = f"{stage}_memory_mb"
            mem_avg = aggregates.get(mem_key, {}).get("avg", 0)
            html.append(f"<tr><td>{stage}</td><td>{val['avg']:.2f}</td><td>{val['median']:.2f}</td><td>{val['p95']:.2f}</td><td>{mem_avg:.1f}</td></tr>")
    html.append("</table></div>")
    
    # 3. Error Categorization
    html.append("    <div class='card'><h2>Error Categorization</h2>")
    for category, errors in categorization["breakdown"].items():
        html.append(f"<h3>{category}</h3><ul>")
        for err_type, count in errors.items():
            if count > 0:
                html.append(f"<li>{err_type}: <strong>{count}</strong></li>")
        html.append("</ul>")
    html.append("</div>")
    
    # 4. Results Table
    html.append("    <div class='card'><h2>Detailed Results</h2><table><tr><th>Image</th><th>Parser Status</th><th>Validation Errors</th><th>Blender Success</th><th>Export Success</th><th>Comparison Viz</th></tr>")
    
    for r in results:
        img_name = r.get("image_name", "unknown")
        parser_ok = not bool(r.get("parser_error"))
        blender_ok = not bool(r.get("blender_error"))
        export_ok = bool(r.get("export_success"))
        val_errs = r.get("validation_error_count", 0)
        
        parser_html = "<span class='success'>OK</span>" if parser_ok else "<span class='failure'>Error</span>"
        blender_html = "<span class='success'>OK</span>" if blender_ok else "<span class='failure'>Error</span>"
        export_html = "<span class='success'>Yes</span>" if export_ok else "<span class='failure'>No</span>"
        
        viz_path = r.get("visual_comparison_path", "")
        viz_html = f"<a href='{viz_path}' target='_blank'>View</a>" if viz_path else "N/A"
        
        html.append(f"<tr><td>{img_name}</td><td>{parser_html}</td><td>{val_errs}</td><td>{blender_html}</td><td>{export_html}</td><td>{viz_html}</td></tr>")
        
    html.append("</table></div>")
    
    html.extend(["</body>", "</html>"])
    
    with open(output_path, 'w') as f:
        f.write("\n".join(html))
        
    return True
