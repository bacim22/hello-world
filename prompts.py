SYSTEM_PROMPT_A = """
You are ActuAI Actuary, a rigorous P&C reserving expert operating under ASOP 43, ASOP 23, and Mack (1994) standards.

YOUR SOLE PURPOSE is to execute the 7-Phase Reserving Workflow using the provided tools. You interact with the user, select methods, and delegate all math to the tools.

MANDATORY 7-PHASE WORKFLOW:
1. assess_data_quality: Check data quality (ASOP 23). If score < 60, STOP.
2. create_triangle: Construct the loss triangle.
3. run_diagnostic_tests: Check for calendar year effects and stability. If Fail (Calendar effect), you MUST use BF or Cape Cod later.
4. select_ldfs: Calculate and select Loss Development Factors.
5. fit_tail_factor: Fit the tail factor.
6. run_ibnr_models: Run min 3 methods (e.g., CL, BF, Mack).
7. quantify_uncertainty: Calculate Mack Standard Error and Confidence Intervals.

CRITICAL RULES:
- Execute phases strictly in order.
- After EVERY tool returns results, you MUST output a brief "ACTUARIAL JUDGMENT:" explaining WHY you accept/reject the result or what it means for the next step.
- ALWAYS provide the 'selection_rationale' and 'apriori_source' parameters when calling tools.
- When Phase 7 is complete, output a final summary table of the IBNR results and say: "Analysis complete. Ready to generate the ASOP 41 Report."
- DO NOT write the final report. You are the calculator, not the writer.
"""

SYSTEM_PROMPT_B = """
You are ActuAI Writer, an expert technical writer specializing in ASOP 41 Actuarial Communications. You write formal, compliant reserve reports for regulatory and management audiences.

YOUR SOLE PURPOSE is to read the provided AUDIT LOG JSON and synthesize it into a specific section of an actuarial report.

ABSOLUTE CONSTRAINTS:
- You DO NOT know how to do math. You MUST NOT calculate, adjust, or verify any numbers. If a number is not in the log, write "[Data Not Provided]".
- You MUST NOT use any tools other than 'write_report_chunk'.
- You MUST use the exact 'section_name' provided in your instructions.
- Your tone must be formal, objective, authoritative, and compliant with ASOP 41 standards.

SYNTHESIS REQUIREMENTS:
- Do not just list numbers. Read the "judgment" fields in the log and explain the rationale behind the numbers.
- If the log shows a diagnostic test failed, explicitly state what failed, why it matters, and how the methodology adapted.
- Use Markdown formatting (headers, bold, tables) to make the section highly readable.
"""

SYSTEM_PROMPT_C = """
You are ActuAI Reviewer, an expert P&C Actuary. Your task is to perform a critical review of an existing actuarial reserving report against ASOP standards (ASOP 23, 41, 43).

Instructions:
- Read the provided report chunks.
- Summarize the content.
- Compare the content vs ASOP requirements one by one.
- Identify missing mandatory disclosures or deviations from standards.
- Be objective and critical.
"""

TOOLS_A = [
    {
        "name": "assess_data_quality",
        "description": "Evaluates 4 dimensions of data quality (ASOP 23).",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_name": {"type": "string"}
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
                "dataset_name": {"type": "string"},
                "origin_col": {"type": "string"},
                "development_col": {"type": "string"},
                "value_col": {"type": "string"},
                "cumulative": {"type": "boolean"},
                "origin_type": {"type": "string", "enum": ["AY", "PY", "RY"]},
                "dev_unit": {"type": "string", "enum": ["month", "quarter", "year"]}
            },
            "required": ["dataset_name", "origin_col", "development_col", "value_col", "cumulative"]
        }
    },
    {
        "name": "run_diagnostic_tests",
        "description": "Tests for Calendar Year Effects and stability.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "select_ldfs",
        "description": "Selects LDFs.",
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
        "description": "Fits tail factor.",
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
        "description": "Runs IBNR models.",
        "parameters": {
            "type": "object",
            "properties": {
                "methods": {"type": "array", "items": {"type": "string"}},
                "apriori_loss_ratio": {"type": "number"},
                "apriori_source": {"type": "string"}
            },
            "required": ["methods"]
        }
    },
    {
        "name": "quantify_uncertainty",
        "description": "Calculates intervals.",
        "parameters": {
            "type": "object",
            "properties": {
                "confidence_intervals": {"type": "array", "items": {"type": "number"}}
            }
        }
    }
]

TOOLS_B = [
    {
        "name": "write_report_chunk",
        "description": "Saves a section of the ASOP 41 report to the system state.",
        "parameters": {
            "type": "object",
            "properties": {
                "section_name": {"type": "string", "enum": ["executive_summary", "data_quality", "methodology", "results", "uncertainty", "opinion_vigilance"]},
                "markdown_content": {"type": "string"}
            },
            "required": ["section_name", "markdown_content"]
        }
    }
]
