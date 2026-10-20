import os, threading, uuid
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()
app = Flask(__name__)
LOCK = threading.Lock()
RUNS = {}

def now():
    return datetime.now(timezone.utc).isoformat()

def agent_status(rid, key, status, detail):
    with LOCK:
        if rid in RUNS:
            RUNS[rid]["agents"][key].update(status=status, detail=detail)
            RUNS[rid]["updated_at"] = now()

def execute_crew(rid, topic):
    try:
        from crewai import Agent, Crew, Process, Task, LLM
        from crewai.tools import BaseTool
        from langchain_openai import ChatOpenAI

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env.")

        llm = LLM(model="openai/gpt-4o-mini", api_key=key, temperature=0)
        social_llm = ChatOpenAI(model="gpt-4o-mini", api_key=key, temperature=0)

        def make_copy(title, summary, platform="facebook"):
            prompt = (
                f"Create an engaging {platform} post.\\nTitle: {title}\\nSummary: {summary}\\n"
                "Use beginner-friendly language, be concise, include a clear call to action "
                "and 3-5 relevant hashtags. Do not invent facts."
            )
            return social_llm.invoke(prompt).content

        class MakeSocialCopyTool(BaseTool):
            name: str = "make_social_copy"
            description: str = "Create a Facebook post from a title, summary, and optional platform."
            def _run(self, title: str, summary: str, platform: str = "facebook") -> str:
                return make_copy(title, summary, platform)

        researcher = Agent(
            role="Researcher Agent",
            goal="Synthesize five useful insights about the topic without inventing facts.",
            backstory="A careful research analyst who flags uncertainty.",
            allow_delegation=False, llm=llm, verbose=True
        )
        writer = Agent(
            role="Writer Agent",
            goal="Write a clear beginner-friendly 250-300 word article.",
            backstory="A precise technical writer.",
            allow_delegation=False, llm=llm, verbose=True
        )
        social = Agent(
            role="Facebook Post Agent",
            goal="Turn the article into a concise Facebook post draft.",
            backstory="An expert in clear, responsible social content.",
            tools=[MakeSocialCopyTool()], allow_delegation=False, llm=llm, verbose=True
        )

        def research_done(output):
            agent_status(rid, "researcher", "completed", "Research notes prepared.")
            agent_status(rid, "writer", "running", "Writing article from research notes.")
        def writer_done(output):
            agent_status(rid, "writer", "completed", "Article generated.")
            agent_status(rid, "social", "running", "Creating Facebook post draft.")
        def social_done(output):
            agent_status(rid, "social", "completed", "Draft ready for review.")

        t1 = Task(
            description=f"Research the topic: {topic}. Give five useful insights, key concepts, challenges, opportunities, and examples. Do not fabricate sources; qualify uncertain/current claims.",
            expected_output="Five concise insights with uncertainty clearly identified.",
            agent=researcher, callback=research_done
        )
        t2 = Task(
            description="Write a structured 250-300 word article with title, summary, 3-4 sections, and conclusion. Avoid unsupported claims.",
            expected_output="Complete Markdown article.",
            agent=writer, context=[t1], callback=writer_done
        )
        t3 = Task(
            description="Create one Facebook post based on the article. Use make_social_copy. Include a clear call to action and 3-5 relevant hashtags. Do NOT publish. Return only the draft.",
            expected_output="One Facebook post draft ready for human review.",
            agent=social, context=[t1, t2], callback=social_done
        )
        crew = Crew(agents=[researcher, writer, social], tasks=[t1, t2, t3],
                    process=Process.sequential, verbose=True)
        agent_status(rid, "researcher", "running", "Researching the topic.")
        result = crew.kickoff()
        with LOCK:
            RUNS[rid].update(
                status="completed",
                research=(t1.output.raw if t1.output else ""),
                article=(t2.output.raw if t2.output else ""),
                draft=(t3.output.raw if t3.output else str(result)).strip(),
                updated_at=now()
            )
    except Exception as e:
        with LOCK:
            if rid in RUNS:
                RUNS[rid]["status"] = "failed"
                RUNS[rid]["error"] = f"{type(e).__name__}: {e}"
                RUNS[rid]["updated_at"] = now()
                for a in RUNS[rid]["agents"].values():
                    if a["status"] in ("queued", "running"):
                        a["status"] = "failed"

def publish_to_facebook(text):
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        raise RuntimeError("FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN missing in .env.")
    r = requests.post(
        f"https://graph.facebook.com/v26.0/{page_id}/feed",
        data={"message": text, "access_token": token}, timeout=60
    )
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not r.ok or "error" in data:
        msg = data.get("error", {}).get("message", "Unknown Facebook API error")
        raise RuntimeError(f"Facebook publishing failed: {msg}")
    return data.get("id", "ID not returned")

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify(openai_configured=bool(os.getenv("OPENAI_API_KEY")),
                   facebook_configured=bool(os.getenv("FACEBOOK_PAGE_ID") and os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")))

@app.post("/api/run")
def start():
    body = request.get_json(silent=True) or {}
    topic = (body.get("topic") or "").strip()
    if not topic:
        return jsonify(error="Please enter a topic."), 400
    if len(topic) > 500:
        return jsonify(error="Topic must be 500 characters or fewer."), 400
    rid = str(uuid.uuid4())
    with LOCK:
        RUNS[rid] = {
            "id": rid, "topic": topic, "status": "running", "draft": "", "article": "",
            "research": "", "error": None, "published": False, "post_id": None,
            "created_at": now(), "updated_at": now(),
            "agents": {
                "researcher": {"name":"Researcher Agent","status":"queued","detail":"Waiting to start."},
                "writer": {"name":"Writer Agent","status":"queued","detail":"Waiting for research."},
                "social": {"name":"Facebook Post Agent","status":"queued","detail":"Waiting for article."}
            }
        }
    threading.Thread(target=execute_crew, args=(rid, topic), daemon=True).start()
    return jsonify(run_id=rid)

@app.get("/api/status/<rid>")
def status(rid):
    with LOCK:
        if rid not in RUNS:
            return jsonify(error="Run not found."), 404
        return jsonify(RUNS[rid])

@app.post("/api/publish/<rid>")
def approve_publish(rid):
    body = request.get_json(silent=True) or {}
    if body.get("confirm") is not True:
        return jsonify(error="Explicit confirmation is required."), 400
    with LOCK:
        run = RUNS.get(rid)
        if not run:
            return jsonify(error="Run not found."), 404
        if run["status"] != "completed" or not run["draft"]:
            return jsonify(error="Draft is not ready."), 409
        if run["published"]:
            return jsonify(error="This draft was already published."), 409
        draft = run["draft"]
    try:
        post_id = publish_to_facebook(draft)
        with LOCK:
            RUNS[rid]["published"] = True
            RUNS[rid]["post_id"] = post_id
            RUNS[rid]["updated_at"] = now()
        return jsonify(ok=True, post_id=post_id)
    except Exception as e:
        return jsonify(error=str(e)), 502

if __name__ == "__main__":
    # Local development only. Do not expose this server directly to the internet.
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
