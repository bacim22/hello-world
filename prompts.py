SYSTEM_PROMPT = """
You are ActuAI Reserve Agent, a specialized P&C actuarial assistant.
You MUST guide the user through a rigorous, ASOP-compliant loss reserving workflow in exactly 8 phases.
DO NOT skip phases or perform calculations out of order.

Phase 1: Data Quality Assessment (ASOP 23) - Evaluate data for appropriateness, reasonableness, completeness, and consistency.
Phase 2: Triangle Construction - Build the loss triangle from the uploaded data.
Phase 3: Diagnostic Testing (Mack 1994) - Test for calendar year effects and development stability.
Phase 4: Development Factor Selection - Calculate and select Loss Development Factors (LDFs).
Phase 5: Tail Factor Fitting - Fit tail factors using parametric curves or judgment.
Phase 6: IBNR Model Comparison - Run CL, BF, and Mack models and compare results.
Phase 7: Uncertainty Quantification (ASOP 43) - Calculate standard errors and confidence intervals.
Phase 8: Report Generation (ASOP 41) - Generate a comprehensive analytical Markdown report with plots and analysis.

Constraints:
- Low temperature (0.1) for precision.
- Provide rationales for ALL actuarial selections (LDFs, Tails, A Prioris).
- Enforce "DO NOT PROCEED" if Data Quality score < 60.
- If BF or Cape Cod models are used, strictly require 'apriori_loss_ratio' and 'apriori_source'.
- Use chainladder library via tools for all math.
- For visualizations, call the appropriate tools to generate heatmaps and analysis plots.
"""

TOOLS = [
    {
        "name": "assess_data_quality",
        "description": "Evaluates 4 dimensions of data quality (ASOP 23): Appropriateness, Reasonableness, Completeness, Consistency.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_name": {"type": "string", "description": "The name of the dataset to assess."}
            },
            "required": ["dataset_name"]
        }
    },
    {
        "name": "create_triangle",
        "description": "Constructs a chainladder Triangle object.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_name": {"type": "string", "description": "The name of the dataset."},
                "origin_col": {"type": "string", "description": "Column for accident/origin year."},
                "development_col": {"type": "string", "description": "Column for development period."},
                "value_col": {"type": "string", "description": "Column for loss values."},
                "cumulative": {"type": "boolean", "description": "Whether the input data is cumulative."},
                "origin_type": {"type": "string", "enum": ["AY", "PY", "RY"], "description": "Origin type."},
                "dev_unit": {"type": "string", "enum": ["month", "quarter", "year"], "description": "Development unit."}
            },
            "required": ["dataset_name", "origin_col", "development_col", "value_col", "cumulative"]
        }
    },
    {
        "name": "run_diagnostic_tests",
        "description": "Tests for Calendar Year Effects and Development Pattern Stability (Mack 1994).",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "select_ldfs",
        "description": "Calculates and selects Loss Development Factors (LDFs).",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["volume", "simple", "medial", "regression"]},
                "selection_rationale": {"type": "string"}
            },
            "required": ["method", "selection_rationale"]
        }
    },
    {
        "name": "fit_tail_factor",
        "description": "Fits a tail factor to the selected LDFs.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["inverse_power", "weibull", "exponential", "constant", "bondy"]},
                "selection_rationale": {"type": "string"},
                "line_of_business": {"type": "string"}
            },
            "required": ["method", "selection_rationale", "line_of_business"]
        }
    },
    {
        "name": "run_ibnr_models",
        "description": "Runs multiple IBNR models and compares results.",
        "parameters": {
            "type": "object",
            "properties": {
                "methods": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["cl", "bf", "mack", "benktander", "capecod"]}
                },
                "apriori_loss_ratio": {"type": "number"},
                "apriori_source": {"type": "string"},
                "earned_premium_col": {"type": "string"}
            },
            "required": ["methods"]
        }
    },
    {
        "name": "quantify_uncertainty",
        "description": "Calculates Mack Standard Error and Confidence Intervals (ASOP 43).",
        "parameters": {
            "type": "object",
            "properties": {
                "confidence_intervals": {
                    "type": "array",
                    "items": {"type": "number"},
                    "default": [0.75, 0.90, 0.95]
                }
            }
        }
    },
    {
        "name": "generate_report",
        "description": "Generates the final 8-section analytical Markdown report (ASOP 41).",
        "parameters": {
            "type": "object",
            "properties": {
                "signing_actuary": {"type": "string"},
                "prior_period_comparison": {"type": "string"}
            }
        }
    }
]
