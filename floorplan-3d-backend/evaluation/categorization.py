from typing import Dict, List, Any

class ErrorCategorizer:
    def __init__(self):
        self.categories = {
            "Parser": {
                "missing wall": 0,
                "merged rooms": 0,
                "split rooms": 0,
                "missing door": 0,
                "parse_exception": 0
            },
            "Geometry": {
                "invalid polygon": 0,
                "disconnected wall": 0,
                "wrong thickness": 0,
                "geometry_exception": 0
            },
            "OCR": {
                "missing room label": 0,
                "wrong dimensions": 0,
                "ocr_exception": 0
            },
            "Blender": {
                "missing wall": 0,
                "floating door": 0,
                "incorrect material": 0,
                "missing furniture": 0,
                "blender_exception": 0
            },
            "Export": {
                "GLB failure": 0,
                "mesh errors": 0
            }
        }
        self.total_errors = 0
        
    def analyze_pipeline_result(self, result: Dict[str, Any]):
        """
        Takes the results of an end-to-end evaluation run and categorizes errors.
        Updates internal counts.
        """
        # Parse exceptions
        if result.get("parser_error"):
            self.categories["Parser"]["parse_exception"] += 1
            self.total_errors += 1
            
        # Geometry validation errors
        val_report = result.get("validation_report", [])
        for msg in val_report:
            if "[ERROR]" in msg:
                self.total_errors += 1
                if "polygon" in msg.lower():
                    self.categories["Geometry"]["invalid polygon"] += 1
                elif "disconnected" in msg.lower():
                    self.categories["Geometry"]["disconnected wall"] += 1
                elif "thickness" in msg.lower():
                    self.categories["Geometry"]["wrong thickness"] += 1
                else:
                    self.categories["Geometry"]["geometry_exception"] += 1
                    
        # Blender and Export
        if result.get("blender_error"):
            self.categories["Blender"]["blender_exception"] += 1
            self.total_errors += 1
            
        if not result.get("export_success") and not result.get("blender_error"):
            # Failed to produce GLB despite no explicit script error
            self.categories["Export"]["GLB failure"] += 1
            self.total_errors += 1
            
    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_errors": self.total_errors,
            "breakdown": self.categories
        }
