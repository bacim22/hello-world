import os
import asyncio
import chainlit as cl
import pandas as pd
import numpy as np
import chainladder as chain_cl
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional
import json
import io

# Set matplotlib backend to Agg for non-interactive plotting
import matplotlib
matplotlib.use('Agg')

from prompts import SYSTEM_PROMPT, TOOLS
from llm_utils import parse_xml_tool_calls
import openai
import data_utils
import actuarial_logic

# Configure OpenAI client
client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    cl.user_session.set("datasets", {})
    cl.user_session.set("current_triangle", None)
    cl.user_session.set("phase", 0)
    await cl.Message(content="Welcome to ActuAI Reserve Agent. Please upload your loss data to begin.").send()

@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})

    # Prune history (keep last 20 messages + system prompt which is handled in run_llm_loop)
    if len(history) > 20:
        history = history[-20:]
        cl.user_session.set("history", history)

    if message.elements:
        for element in message.elements:
            if isinstance(element, cl.File):
                await handle_file_upload(element)
    await run_llm_loop()

async def run_llm_loop():
    history = cl.user_session.get("history")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            tools=[{"type": "function", "function": t} for t in TOOLS],
            tool_choice="auto",
            temperature=0.1
        )
        response_message = response.choices[0].message
        content = response_message.content
        tool_calls = response_message.tool_calls

        if not tool_calls and content and "<tool_call>" in content:
            xml_calls = parse_xml_tool_calls(content)
            if xml_calls:
                tool_calls = []
                for i, call in enumerate(xml_calls):
                    tool_calls.append(type('obj', (object,), {
                        'id': f"call_{i}",
                        'function': type('obj', (object,), {
                            'name': call['name'],
                            'arguments': json.dumps(call['arguments'])
                        })
                    }))

        if content:
            await cl.Message(content=content).send()
            history.append({"role": "assistant", "content": content})

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                async with cl.Step(name=f"Running: {function_name}...", type="tool") as step:
                    result = await execute_tool(function_name, function_args)
                    step.output = result
                history.append({
                    "role": "assistant",
                    "tool_calls": [{"id": tool_call.id, "type": "function", "function": {"name": function_name, "arguments": tool_call.function.arguments}}]
                })
                history.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": result})
            await run_llm_loop()
    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()

async def execute_tool(name: str, args: Dict[str, Any]) -> str:
    datasets = cl.user_session.get("datasets")
    triangle = cl.user_session.get("current_triangle")

    if name == "assess_data_quality":
        df = datasets.get(args.get("dataset_name"))
        if df is None: return "Dataset not found."
        res = actuarial_logic.assess_quality(df)
        return json.dumps(res)
    elif name == "create_triangle":
        df = datasets.get(args.get("dataset_name"))
        if df is None: return "Dataset not found."
        try:
            tri = actuarial_logic.create_cl_triangle(df, args["origin_col"], args["development_col"], args["value_col"], args["cumulative"], args.get("origin_type", "AY"), args.get("dev_unit", "month"))
            cl.user_session.set("current_triangle", tri)
            return "Triangle created."
        except Exception as e: return str(e)
    elif name == "run_diagnostic_tests":
        if triangle is None: return "No triangle."
        return json.dumps(actuarial_logic.run_diagnostics(triangle))
    elif name == "select_ldfs":
        if triangle is None: return "No triangle."
        res = actuarial_logic.select_loss_development_factors(triangle, args["method"])
        cl.user_session.set("current_ldf", res)
        return f"LDFs selected via {args['method']}."
    elif name == "fit_tail_factor":
        if triangle is None: return "No triangle."
        res = actuarial_logic.fit_tail(triangle, args["method"])
        cl.user_session.set("current_tail", res)
        return f"Tail fitted via {args['method']}."
    elif name == "run_ibnr_models":
        if triangle is None: return "No triangle."
        res = actuarial_logic.run_ibnr(triangle, args["methods"], args.get("apriori_loss_ratio"))
        cl.user_session.set("ibnr_results", res)
        return json.dumps(res)
    elif name == "quantify_uncertainty":
        if triangle is None: return "No triangle."
        res = actuarial_logic.quantify_uncertainty(triangle, args.get("confidence_intervals", [0.75, 0.90, 0.95]))
        cl.user_session.set("uncertainty_results", res)
        return json.dumps(res)
    elif name == "generate_report":
        return await handle_generate_report(args)
    return f"Tool {name} not found."

async def handle_generate_report(args):
    # Retrieve all results from session
    tri = cl.user_session.get("current_triangle")
    ibnr_res = cl.user_session.get("ibnr_results") or {}
    unc_res = cl.user_session.get("uncertainty_results") or {}

    report = f"""
# Actuarial Reserve Analysis Report (ASOP 41 Compliant)
**Signing Actuary:** {args.get('signing_actuary', 'AI Assistant (Unsigned)')}

## 1. Executive Summary
The Actuarial Central Estimate (ACE) for IBNR is **${ibnr_res.get('central_estimate', 0):,.0f}**.
Method Range: ${ibnr_res.get('range', [0,0])[0]:,.0f} - ${ibnr_res.get('range', [0,0])[1]:,.0f}.

## 2. Scope & Purpose
This analysis is intended to provide a loss reserving estimate for the provided claims data. It is for internal use by reserving analysts.

## 3. Data & Methodology (ASOP 23)
Methods deployed: {', '.join([k for k in ibnr_res.keys() if k not in ['central_estimate', 'range']]) if ibnr_res else 'N/A'}.
A prioris used: {args.get('apriori_loss_ratio', 'N/A')}.

## 4. Results & Method Comparison
| Method | IBNR | Ultimate |
|--------|------|----------|
"""
    for m, vals in ibnr_res.items():
        if isinstance(vals, dict):
            report += f"| {m.upper()} | ${vals.get('ibnr',0):,.0f} | ${vals.get('ultimate',0):,.0f} |\n"

    report += f"""
## 5. Uncertainty Quantification (ASOP 43)
- **Mack Standard Error:** ${unc_res.get('std_err', 0):,.0f}
- **Coefficient of Variation (CV):** {unc_res.get('cv', 0):.2%} ({unc_res.get('cv_classification', 'N/A')})
- **Confidence Intervals:**
"""
    for ci, val in unc_res.get('confidence_intervals', {}).items():
        report += f"  - {ci}: ${val:,.0f}\n"

    report += f"""
## 6. Visualizations & Exhibits
(See generated charts below)

## 7. Vigilance Items & Risk Factors
- Environmental changes in claims processing.
- Operational shifts in underwriting.
- Mix changes in the line of business.

## 8. Opinion Block & Certification
{'[STRICTLY BLANK - AI CANNOT SIGN]' if not args.get('signing_actuary') else f"Provisionally prepared for: {args.get('signing_actuary')}. AI cannot issue a formal Statement of Actuarial Opinion (SAO)."}
"""
    await cl.Message(content=report).send()
    # Generate Heatmaps and Analysis Plots
    if tri is not None:
        # Cumulative Triangle Heatmap
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_title("Cumulative Loss Triangle Heatmap")
        im = ax.imshow(tri.values[0,0,:,:], cmap='viridis')
        fig.colorbar(im)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await cl.Message(content="Cumulative Triangle Heatmap:", elements=[cl.Image(name="cum_heatmap", content=buf.read(), display="inline")]).send()
        plt.close(fig)

        # Incremental Triangle Heatmap
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_title("Incremental Loss Triangle Heatmap")
        inc_tri = tri.incremental
        im = ax.imshow(inc_tri.values[0,0,:,:], cmap='plasma')
        fig.colorbar(im)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await cl.Message(content="Incremental Triangle Heatmap:", elements=[cl.Image(name="inc_heatmap", content=buf.read(), display="inline")]).send()
        plt.close(fig)

        # LDF Analysis Plot
        if hasattr(tri, 'link_ratio'):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("Age-to-Age Link Ratio Development")
            lrs = tri.link_ratio.values[0,0,:,:]
            for i in range(lrs.shape[0]):
                ax.plot(lrs[i, :], marker='o', label=f"Origin {i}")
            ax.set_xlabel("Development Period")
            ax.set_ylabel("Link Ratio")
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            await cl.Message(content="Link Ratio Analysis:", elements=[cl.Image(name="lrs_plot", content=buf.read(), display="inline")]).send()
            plt.close(fig)

    return "Report generated."

async def handle_file_upload(file):
    datasets = cl.user_session.get("datasets")
    content = open(file.path, "rb").read()
    if file.name.endswith(".csv"): df = data_utils.parse_csv(content)
    elif file.name.endswith(".xlsx"):
        sheets = data_utils.parse_excel(content)
        for s, d in sheets.items(): datasets[f"{file.name}_{s}"] = data_utils.clean_dataframe(d)
        df = None
    if df is not None: datasets[file.name] = data_utils.clean_dataframe(df)
    cl.user_session.set("datasets", datasets)
    await cl.Message(content=f"Loaded {file.name}").send()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
