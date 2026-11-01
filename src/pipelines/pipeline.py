import time
from datetime import datetime
from typing import Callable, Any

try:
    from rich import print
except ImportError:
    pass

# import the agents
from src.agents.agents import build_reader_agent, build_search_agent, writer_chain, critic_chain

def invoke_with_retry(action: Callable[[], Any], step_name: str, max_retries: int = 3, initial_delay: float = 2.0) -> Any:
    """
    Executes a callable with exponential backoff to handle transient network
    disconnections (e.g., httpcore/httpx RemoteProtocolError, dropped keep-alives).
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return action()
        except Exception as e:
            if attempt == max_retries:
                print(f"\n❌ [{datetime.now().strftime('%H:%M:%S')}] {step_name} failed after {max_retries} attempts: {e}", flush=True)
                raise
            err_type = type(e).__name__
            print(f"\n⚠️  [{datetime.now().strftime('%H:%M:%S')}] {step_name} hit transient transport error ({err_type}: {e})", flush=True)
            print(f"🔄 Retrying {step_name} (attempt {attempt + 1}/{max_retries}) in {delay:.1f}s with fresh connection...", flush=True)
            time.sleep(delay)
            delay *= 2

def run_research_pipeline(topic: str) -> dict:

    state = {}
    pipeline_start = time.time()

    print("\n" + "=" * 60, flush=True)
    print(f"🚀 Multi-Agent Research System Starting", flush=True)
    print(f"📋 Topic: {topic}", flush=True)
    print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60 + "\n", flush=True)

    # Search agent working
    print("=" * 60, flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 1/4 - Search Agent is working...", flush=True)
    print("⏳ Invoking Gemini to plan research queries & retrieve sources via Tavily...", flush=True)
    print("=" * 60, flush=True)

    step1_start = time.time()
    search_result = invoke_with_retry(
        lambda: build_search_agent().invoke({
            "messages": [
                ("user", f"Find recent, reliable and detailed information about: {topic}")
            ]
        }),
        step_name="Step 1 (Search Agent)"
    )

    state["search_results"] = search_result["messages"][-1].content
    step1_elapsed = time.time() - step1_start

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✓ Step 1 Completed ({step1_elapsed:.2f}s)", flush=True)
    print(f"📄 Search Results Preview:\n{state['search_results'][:500]}...", flush=True)
    print("\n" + "=" * 60, flush=True)

    # reader agent
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 2/4 - Reader Agent is working...", flush=True)
    print("⏳ Invoking Gemini to analyze sources and scrape page content...", flush=True)
    print("=" * 60, flush=True)

    step2_start = time.time()
    reader_result = invoke_with_retry(
        lambda: build_reader_agent().invoke({
            "messages": [
                ("user", f"Here is the research data:\n{state['search_results']}\n\nPlease read it and prepare a structured summary.")
            ]
        }),
        step_name="Step 2 (Reader Agent)"
    )

    state["scraped_content"] = reader_result["messages"][-1].content
    step2_elapsed = time.time() - step2_start

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✓ Step 2 Completed ({step2_elapsed:.2f}s)", flush=True)
    print(f"📄 Scraped Content Preview:\n{state['scraped_content'][:500]}...", flush=True)
    print("\n" + "=" * 60, flush=True)

    # writer chain
    # Step 3 - Writer Chain
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 3/4 - Writer Chain is drafting the report...", flush=True)
    print("⏳ Invoking Gemini with synthesized research...", flush=True)
    print("=" * 60, flush=True)

    step3_start = time.time()
    research_combined = (
        f"SEARCH RESULTS: \n{state['search_results']} \n\n"
        f"DETAILED SCRAPED CONTENT: \n{state['scraped_content']}"
    )

    state["report"] = invoke_with_retry(
        lambda: writer_chain.invoke({
            "topic": topic,
            "research": research_combined
        }),
        step_name="Step 3 (Writer Chain)"
    )
    step3_elapsed = time.time() - step3_start

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✓ Step 3 Completed ({step3_elapsed:.2f}s)", flush=True)
    print(f"\n📄 Final Report:\n{state['report']}", flush=True)
    print("\n" + "=" * 60, flush=True)

    # critic report
    # Step 4 - Critic Agent
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 4/4 - Critic Chain is reviewing the report...", flush=True)
    print("⏳ Invoking Gemini to evaluate and score report against quality metrics...", flush=True)
    print("=" * 60, flush=True)

    step4_start = time.time()
    state["feedback"] = invoke_with_retry(
        lambda: critic_chain.invoke({
            "report": state["report"]
        }),
        step_name="Step 4 (Critic Chain)"
    )
    step4_elapsed = time.time() - step4_start

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✓ Step 4 Completed ({step4_elapsed:.2f}s)", flush=True)
    print(f"\n📊 Critic Evaluation:\n{state['feedback']}", flush=True)

    total_elapsed = time.time() - pipeline_start
    print("\n" + "=" * 60, flush=True)
    print(f"🎉 Research Pipeline Finished Successfully in {total_elapsed:.2f}s", flush=True)
    print(f"⏱️ Timing Breakdown: Search: {step1_elapsed:.1f}s | Reader: {step2_elapsed:.1f}s | Writer: {step3_elapsed:.1f}s | Critic: {step4_elapsed:.1f}s", flush=True)
    print("=" * 60 + "\n", flush=True)

    return state
