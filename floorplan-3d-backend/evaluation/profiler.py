import time
import psutil
import os
import statistics
from typing import Dict, Any, List

class Profiler:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_times = {}
        self.metrics = {
            "time_s": {},
            "memory_mb": {}
        }
        
    def start(self, stage_name: str):
        self.start_times[stage_name] = {
            "time": time.perf_counter(),
            "mem": self.process.memory_info().rss
        }
        
    def stop(self, stage_name: str):
        if stage_name not in self.start_times:
            return
            
        start_info = self.start_times.pop(stage_name)
        end_time = time.perf_counter()
        end_mem = self.process.memory_info().rss
        
        elapsed_s = end_time - start_info["time"]
        mem_mb = (end_mem - start_info["mem"]) / (1024 * 1024)
        
        self.metrics["time_s"][stage_name] = elapsed_s
        self.metrics["memory_mb"][stage_name] = max(0.0, mem_mb)
        
    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics


def calculate_aggregates(runs_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate average, median, p95, and max for each metric and stage across all runs.
    """
    aggregates = {}
    
    stages = set()
    for run in runs_metrics:
        if "time_s" in run:
            stages.update(run["time_s"].keys())
            
    for stage in stages:
        times = [run.get("time_s", {}).get(stage, 0) for run in runs_metrics if "time_s" in run and stage in run["time_s"]]
        mems = [run.get("memory_mb", {}).get(stage, 0) for run in runs_metrics if "memory_mb" in run and stage in run["memory_mb"]]
        
        if times:
            aggregates[f"{stage}_time_s"] = {
                "avg": statistics.mean(times),
                "median": statistics.median(times),
                "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 2 else max(times), # Simple p95 approximation
                "max": max(times)
            }
        
        if mems:
            aggregates[f"{stage}_memory_mb"] = {
                "avg": statistics.mean(mems),
                "max": max(mems)
            }
            
    return aggregates
