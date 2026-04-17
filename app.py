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

from prompts import SYSTEM_PROMPT_A, SYSTEM_PROMPT_B, SYSTEM_PROMPT_C, TOOLS_A, TOOLS_B
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
    cl.user_session.set("audit_log", [])
    cl.user_session.set("is_report_generated", False)
    cl.user_session.set("final_report_sections", {
        "executive_summary": "",
        "data_quality": "",
        "methodology": "",
        "results": "",
        "uncertainty": "",
        "opinion_vigilance": ""
    })
    await cl.Message(content="Welcome to ActuAI Reserve Agent. I am the Actuary Agent. Please upload your loss data to begin Phase 1 (Data Quality Assessment).").send()

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

    # Provider Fallback Logic
    primary_model = "gpt-4o"
    secondary_model = "gpt-3.5-turbo"

    try:
        try:
            response = await client.chat.completions.create(
                model=primary_model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_A}] + history,
                tools=[{"type": "function", "function": t} for t in TOOLS_A],
                tool_choice="auto",
                temperature=0.1
            )
        except Exception as e:
            print(f"Primary model failed: {e}. Falling back...")
            response = await client.chat.completions.create(
                model=secondary_model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_A}] + history,
                tools=[{"type": "function", "function": t} for t in TOOLS_A],
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

            # Extract Actuarial Judgment for Agent B
            if "ACTUARIAL JUDGMENT:" in content:
                judgment = content.split("ACTUARIAL JUDGMENT:")[1].strip()
                # Find the last tool result in the audit log that doesn't have a judgment yet
                audit_log = cl.user_session.get("audit_log")
                for entry in reversed(audit_log):
                    if "judgment" not in entry:
                        entry["judgment"] = judgment
                        break
                cl.user_session.set("audit_log", audit_log)

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                async with cl.Step(name=f"Running: {function_name}...", type="tool") as step:
                    result = await execute_tool(function_name, function_args)
                    step.output = result

                    # Update audit log for Agent B
                    audit_log = cl.user_session.get("audit_log")
                    phase = cl.user_session.get("phase")

                    # Attempt to extract judgment from the assistant's previous message
                    # (In a real flow, we'd wait for the assistant to output 'ACTUARIAL JUDGMENT:')
                    # but here we'll just log the tool execution.
                    audit_log.append({
                        "phase": phase,
                        "action": function_name,
                        "result": json.loads(result) if result.startswith('{') else result,
                        "arguments": function_args
                    })
                    cl.user_session.set("audit_log", audit_log)
                history.append({
                    "role": "assistant",
                    "tool_calls": [{"id": tool_call.id, "type": "function", "function": {"name": function_name, "arguments": tool_call.function.arguments}}]
                })
                history.append({"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": result})

            # Check if workflow is finished to show button
            if cl.user_session.get("phase") == 7 and not cl.user_session.get("is_report_generated"):
                actions = [
                    cl.Action(name="generate_report_action", value="generate", label="📜 Generate ASOP 41 Compliant Report")
                ]
                await cl.Message(content="Reserving workflow complete. You can now generate the formal report.", actions=actions).send()

            await run_llm_loop()
    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()

@cl.action_callback("generate_report_action")
async def on_action(action: cl.Action):
    cl.user_session.set("is_report_generated", True)
    await handle_generate_report()

async def execute_tool(name: str, args: Dict[str, Any]) -> str:
    datasets = cl.user_session.get("datasets")
    triangle = cl.user_session.get("current_triangle")

    if name == "assess_data_quality":
        df = datasets.get(args.get("dataset_name"))
        if df is None: return "Dataset not found."
        res = actuarial_logic.assess_quality(df)
        cl.user_session.set("phase", 1)
        return json.dumps(res)
    elif name == "create_triangle":
        df = datasets.get(args.get("dataset_name"))
        if df is None: return "Dataset not found."
        try:
            tri = actuarial_logic.create_cl_triangle(df, args["origin_col"], args["development_col"], args["value_col"], args["cumulative"], args.get("origin_type", "AY"), args.get("dev_unit", "month"))
            cl.user_session.set("current_triangle", tri)
            cl.user_session.set("phase", 2)
            return "Triangle created."
        except Exception as e: return str(e)
    elif name == "run_diagnostic_tests":
        if triangle is None: return "No triangle."
        cl.user_session.set("phase", 3)
        return json.dumps(actuarial_logic.run_diagnostics(triangle))
    elif name == "select_ldfs":
        if triangle is None: return "No triangle."
        res = actuarial_logic.select_loss_development_factors(triangle, args["method"])
        cl.user_session.set("current_ldf", res)
        cl.user_session.set("phase", 4)
        return f"LDFs selected via {args['method']}."
    elif name == "fit_tail_factor":
        if triangle is None: return "No triangle."
        res = actuarial_logic.fit_tail(triangle, args["method"])
        cl.user_session.set("current_tail", res)
        cl.user_session.set("phase", 5)
        return f"Tail fitted via {args['method']}."
    elif name == "run_ibnr_models":
        if triangle is None: return "No triangle."
        # Use premium if available in dataset (placeholder logic)
        premium = None
        res = actuarial_logic.run_ibnr(triangle, args["methods"], args.get("apriori_loss_ratio"), premium)
        cl.user_session.set("ibnr_results", res)
        cl.user_session.set("phase", 6)
        return json.dumps(res)
    elif name == "quantify_uncertainty":
        if triangle is None: return "No triangle."
        res = actuarial_logic.quantify_uncertainty(triangle, args.get("confidence_intervals", [0.75, 0.90, 0.95]))
        cl.user_session.set("uncertainty_results", res)
        return json.dumps(res)
    elif name == "write_report_chunk":
        sections = cl.user_session.get("final_report_sections")
        sections[args["section_name"]] = args["markdown_content"]
        cl.user_session.set("final_report_sections", sections)
        return f"Section {args['section_name']} written."

    return f"Tool {name} not found."

async def handle_generate_report(signing_actuary=None):
    audit_log = cl.user_session.get("audit_log")

    await cl.Message(content="📝 Writer Agent initializing ASOP 41 Reporting Workflow...").send()

    chunks = [
        {"section": "data_quality", "instruction": "Write the Data Quality (ASOP 23) section.", "phases": [1]},
        {"section": "methodology", "instruction": "Write the Triangle Construction, Diagnostics, LDF Selection, and Tail Factor sections.", "phases": [2, 3, 4, 5]},
        {"section": "results", "instruction": "Write the IBNR Results and Method Comparison section.", "phases": [6]},
        {"section": "uncertainty", "instruction": "Write the Uncertainty and Confidence Interval section.", "phases": [7]},
        {"section": "opinion_vigilance", "instruction": "Write the Vigilance Items, Opinion Block (leave signature blank), and Certifications.", "phases": []},
        {"section": "executive_summary", "instruction": "Write the Executive Summary. Synthesize the key IBNR number, primary method, and uncertainty CV.", "phases": [1,2,3,4,5,6,7]}
    ]

    for i, chunk_meta in enumerate(chunks):
        await cl.Message(content=f"📝 Writing Section {i+1}/6: {chunk_meta['section']}...").send()

        relevant_logs = [log for log in audit_log if log["phase"] in chunk_meta["phases"]]

        writer_prompt = f"""
        AUDIT LOG: {json.dumps(relevant_logs, indent=2)}
        INSTRUCTION: {chunk_meta['instruction']}
        SECTION NAME: {chunk_meta['section']}
        SIGNING ACTUARY: {signing_actuary}
        """

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_B},
                {"role": "user", "content": writer_prompt}
            ],
            tools=[{"type": "function", "function": t} for t in TOOLS_B],
            tool_choice={"type": "function", "function": {"name": "write_report_chunk"}},
            temperature=0.1
        )

        tool_call = response.choices[0].message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)

        # Execute tool (save to state)
        await execute_tool("write_report_chunk", args)

        # Display chunk
        await cl.Message(content=f"### {args['section_name'].replace('_', ' ').title()}\n{args['markdown_content']}").send()

    await cl.Message(content="✅ Full ASOP 41 Report Generated.").send()

    # Generate Heatmaps and Analysis Plots
    tri = cl.user_session.get("current_triangle")
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

        # Age-to-Age LDF Heatmap
        if hasattr(tri, 'link_ratio'):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("Age-to-Age LDF Heatmap")
            lrs = tri.link_ratio
            im = ax.imshow(lrs.values[0,0,:,:], cmap='YlGnBu')
            fig.colorbar(im)
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            await cl.Message(content="Age-to-Age LDF Heatmap:", elements=[cl.Image(name="ldf_heatmap", content=buf.read(), display="inline")]).send()
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

    # If it's a critical review request (Actuarial Report)
    if "report" in file.name.lower() and file.name.endswith(".pdf"):
        await cl.Message(content=f"🔍 Actuarial Report detected. Initializing Critical Review Agent...").send()
        await handle_critical_review(content)
        return

    df = None
    if file.name.endswith(".csv"):
        df = data_utils.parse_csv(content)
    elif file.name.endswith(".xlsx") or file.name.endswith(".xls"):
        sheets = data_utils.parse_excel(content)
        for s, d in sheets.items(): datasets[f"{file.name}_{s}"] = data_utils.clean_dataframe(d)
    elif file.name.endswith(".pdf"):
        df = data_utils.parse_pdf(content)

    if df is not None: datasets[file.name] = data_utils.clean_dataframe(df)
    cl.user_session.set("datasets", datasets)
    await cl.Message(content=f"Loaded {file.name}").send()

async def handle_critical_review(pdf_content):
    # Using a chunked strategy for long reports
    # fallback to local ollama if needed

    # Extract text from PDF
    import pdfplumber
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    # Chunking (approx 2000 words per chunk)
    words = text.split()
    chunk_size = 2000
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

    await cl.Message(content=f"📑 Report split into {len(chunks)} chunks for analysis.").send()

    review_results = []
    for i, chunk in enumerate(chunks):
        await cl.Message(content=f"🧐 Reviewing Chunk {i+1}/{len(chunks)}...").send()

        try:
            # Try OpenRouter
            response = await client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_C},
                    {"role": "user", "content": f"REPORT CHUNK {i+1}:\n{chunk}"}
                ],
                temperature=0.1
            )
            review_results.append(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenRouter failed: {e}. Falling back to Ollama...")
            try:
                import ollama
                response = ollama.chat(model='qwen2.5:3b', messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT_C},
                    {'role': 'user', 'content': f"REPORT CHUNK {i+1}:\n{chunk}"},
                ])
                review_results.append(response['message']['content'])
            except Exception as oe:
                review_results.append(f"[Fallback Failed: {oe}] Analysis for Chunk {i+1} unavailable.")

    # Final Summary Review
    final_review_prompt = "Summarize the findings from all chunks and provide a final verdict on ASOP compliance."
    # ... (similar call as above)

    await cl.Message(content=f"## Critical Review Results\n\n" + "\n\n".join(review_results)).send()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
