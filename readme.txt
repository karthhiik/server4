You're a senior developer and you have deep knowledge in the python , Fast API and flask use all the thinking and techiques. Now you're task it to understand the server2(Flask) and Server1_FastApi every file and folder from both the folders , and Server1_FastApi is a old version so we need to update it by using the Flask server 2 . So in the Flask we have updated all the things including adding new things and updating the versions and requests and responses and code changes and operation changes also . Now need to  make the same change to the FASTAPI project called Server1_FastApi. make sure you need to change every file or every line of the code which is in the flask to FASTAPI.  we need to make the Fastapi as standalone and updated version same as server2 . Make sure every file and every code you need to change the flask to fastapi in the (server2->Server1_FastApi). like we need to update the Server1_FastApi  from the server2 .See and also make sure the services and operations like Gtm, swot etc need to be correctly codes as per the server2 folder.In the current Server1_FastApi have some trouble in the Gtm,pitch analysis and swot and bussiness logic Not only this we have changed other code also can you please change where files also. See the Server2 and Server1_FastApi are same project , But the server2(flask) is a flask which is getting lag so i have updated it to the FastApi (server1_FastApi) while converting i didn't covnerted it completely and have some problem in the server1_FastApi so you task is to convert every line and every code and every folder  to fastapi correctly . Use all you're knwoledge to make it make sure correct routes and functions and operations need to be correctly kept in the FASTAPI_server.be everycareful this is a real time project and also test it . and also use the .env file from flask to FASTApi_server use all the things correctly.



20 previous messages
I updated the FastAPI app’s shared foundation and route surface so it’s much closer to the Flask server now. The main changes are in main.py, config.py, deps.py, auth_routes.py, system_routes.py, events_routes.py, gtm_routes.py, swot_routes.py, and pitch_analysis_routes.py. I also added missing FastAPI route families for avatar_routes.py and cold_mail_routes.py, fixed real service bugs in gtm_service.py and pitch_service.py, expanded the auth schema in auth.py, and synced the Flask env into FastAPI’s .env and .env.local.

What’s now in place: cookie-aware auth, CSRF/session handling, /session, Flask-style health/readiness/diagnostics endpoints, safer /uploads/{filename:path}, missing GTM routes like /user_gtm_plans, /gtm_plan/{id}, /delete_gtm_plan/{id}, /generation_status, SWOT system routes, pitch /api/system-status, avatar endpoints, cold-mail endpoints, and the pitch route now queues Celery instead of using in-process background work.

I verified this with python -m compileall app, direct import app.main, and FastAPI TestClient smoke checks for /health, /health/ready, /diagnostics, /api/system/health, and /session. Those all returned 200 with expected payloads.

The important caveat: this is not yet a true line-for-line parity port of the very large Flask GTM, pitch, and business engines. I closed the biggest structural gaps and fixed several concrete FastAPI bugs, but the Flask service internals in gtm_bp.py, pitch_analysis_bp.py, and especially business_bp.py are still much larger than their FastAPI counterparts. Also, I did not run end-to-end authenticated GTM/SWOT/pitch jobs against live Firebase users plus a live Celery worker in this pass.


can you once again  verify all the codebase files and codes operations , functions and routing system and .env files and credits and flow and etc things are as per the server2 flask in the Server1_FastApi are not can you see it and confirm me. the operations and code flow and code details and etc things are same as flask or not in the Server1_FastApi check all the files and things correct and confirm me and test all the routes because i need to integrate it with my front-end called D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming .See in the GTM , SWOT , BUSINESSS plan , pitch deck -> remove the http SSE and keep the sockets and remove all the SSE you see in the Server1_FASTApi and keep the sockets and fast socket connection need to be happend and correct and accurate coding we needed .TASK-1 verify the all the routes are correctly integrated and functions and operation are working correct and test it with the front-end and Task-2 remove the SSE progress and replace it with the sockets and keep the correct progress update and connect the sokcets to the front-end correctly and show the progress correctly. See use the correct coding and techniques and thinking  to make it correctly and make sure this is a real time project be every careful and check them correctly.understand the project folder and then continue the work.



Worked for 20m 43s
Status

No, I can’t honestly confirm that Server1_FastApi is fully the same as server2 line-for-line yet.

What I can confirm is:

.env parity is exact right now: server2/.env matches .env and .env.local.
The SSE progress flow has been removed from the active FastAPI/frontend integration and replaced with WebSockets through progress_ws_routes.py, progress.py, and the frontend socket helper progressSocket.ts.
GTM, business-plan, and pitch frontend flows now use sockets instead of EventSource in GTMStrategy.tsx, gtmloading.tsx, businessLoading.tsx, resultpitchanalysis.tsx, and pitch_anaylsis.tsx.
The active backend route surface needed by those frontend flows is present, and realtime progress works through /ws/progress/{progress_type}.
Verified

I tested these successfully:

python -m compileall app
import app.main
WebSocket smoke test on /ws/progress/gtm?token=...&task_id=... with real publish/receive messages
npm run build for the frontend at D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming
I also verified these backend contracts exist: /verify-login, /api/service/check-access/{service_id}, /generate_gtm_plan, /gtm_plan_result/{task_id}, /download_gtm_pdf/{plan_id}, /user_gtm_plans, /gtm_plan/{plan_id}, /delete_gtm_plan/{plan_id}, /generation_status, /api/swot, /api/competitor-analysis, /api/value-proposition-canvas, /api/market-segmentation, /api/risk-analysis, /api/generate-business-plan, /api/analyze-pitch, /api/analyze-pitch-result/{task_id}, /api/analyze-pitch-history, and /api/analyze-pitch-status/{task_id}.

Not Confirmed Yet

The important gap is full business-logic parity with Flask. The Flask source is still much larger than the FastAPI port in the heaviest modules:

Flask GTM gtm_bp.py is about 2297 lines, while FastAPI GTM is mainly gtm_routes.py and gtm_service.py, about 293 + 371.
Flask pitch pitch_analysis_bp.py is about 4839 lines, while FastAPI pitch is mainly pitch_analysis_routes.py and pitch_service.py, about 472 + 343.
Flask business business_bp.py is about 4784 lines, while FastAPI business is mainly business_routes.py, about 509.
So the honest answer is: the route/env/socket integration is now in much better shape and the frontend compiles against it, but I cannot truthfully certify that Server1_FastApi is fully identical to server2 in deep GTM, pitch, and business logic yet.

Residual notes:

Frontend build passed, but it still shows pre-existing CSS/source-map warnings.
Backend import still shows the existing requests dependency warning and PhonePe SDK warning.
I did not run full live end-to-end GTM/SWOT/business/pitch generations against real external AI/services and a real browser session.

17 files changed
+777
-818
Undo

Review
app/api/routes/__init__.py
app/api/routes/business_progress_routes.py
app/api/routes/general_progress_routes.py
app/api/routes/gtm_progress_routes.py
app/api/routes/gtm_routes.py
app/api/routes/pitch_analysis_routes.py
app/api/routes/pitch_progress_routes.py
app/api/routes/progress_ws_routes.py
app/celery_tasks/celery_tasks.py
app/core/progress.py
app/main.py
src/components/BusinessPlanfrom/resultpitchanalysis.tsx
src/components/Loading/businessLoading.tsx
src/components/Loading/gtmloading.tsx
src/lib/progressSocket.ts
src/pages/GTMStrategy.tsx
src/pages/pitch_anaylsis.tsx
So whats you're next plan ?


The next plan is to stop changing infrastructure and do a strict parity pass module by module.

Build a Flask-to-FastAPI parity checklist.
I’ll map every important Flask route, request shape, response shape, DB write shape, service check, env usage, and side effect against the FastAPI version and mark exact mismatches.

Finish the heavy backend parity in this order: GTM -> Business Plan -> Pitch -> SWOT.
These are still the biggest gaps, especially because the Flask files are much larger than the FastAPI ones, so I need to port missing internal logic, not just routes.

Validate data flow end to end with the frontend.
I’ll run the real frontend against FastAPI, test GTM, business plan, pitch, and SWOT flows, confirm socket progress behavior, result payloads, error cases, and downloads.

Produce a final confirmation report.
I’ll give you a clear list of:

what is now fully matched
what was fixed
what is still different, if anything
which routes and flows were tested successfully
My recommendation is to start immediately with GTM, because that is where the frontend/backend contract and generation flow have the biggest remaining parity risk. After that I’ll do Business Plan, then Pitch, then SWOT.


yes do it please. 



Worked for 18m 17s
I finished another strict Flask-to-FastAPI parity pass and patched the concrete mismatches I found. The biggest backend updates are in business_routes.py, pitch_analysis_routes.py, swot_routes.py, swot.py, and business.py.

What changed in this pass:

Business plan flow now follows the Flask-style prompt structure much more closely, including the richer section-generation flow, better progress stages, real cache stats, improved health response, correct PDF filename behavior, pagination flags, and cached plan lookup.
Pitch result/status/history/metrics now use the stored Flask-style analysis_results shape instead of rebuilding a thinner response, so processing time, ratings, and result payloads line up better.
SWOT now has Flask-style request tracking/rate limiting in /api/swot, and /api/system/status reports real active-request counters instead of placeholders.
SWOT request schemas were fixed so FastAPI no longer incorrectly requires userId in the body, and competitor analysis now accepts the Flask-style business fields.
.env parity is still exact, and SSE/EventSource references are gone from the active FastAPI/frontend codepaths. The websocket progress stack remains in progress_ws_routes.py, progress.py, and progressSocket.ts.
What I verified:

python -m compileall app
direct app import via app.main
FastAPI health/system smoke checks for /health, /health/ready, /diagnostics, /api/system/health
route-level smoke tests for business, pitch, and SWOT flows with patched dependencies
frontend build at D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming via npm run build
.env hash match between server2/.env and .env
Important status:

I can confirm the tested route contracts, schemas, progress transport, and env setup are in much better alignment with server2 now.
I cannot honestly claim perfect line-by-line parity across every deep AI/business branch yet without full live end-to-end runs against real auth, Mongo/Cosmos data, Redis, Celery workers, and external AI/services for GTM, business plan, pitch, and SWOT.
Remaining intentional differences I found:

GTM is still async in FastAPI, with gtm_routes.py using /gtm_plan_result/{task_id} instead of Flask’s synchronous return.
Pitch SSE progress endpoint is intentionally not restored; websocket progress replaces it.
Flask path syntax like <task_id> becomes {task_id} in FastAPI, which is expected.
Flask’s exact business /health endpoint is not duplicated because FastAPI already has the shared global /health; business-specific health is exposed at /api/business/health.
Residual warnings only:

backend still logs the existing RequestsDependencyWarning
backend still logs the existing PhonePe SDK warning
frontend build still has the pre-existing sourcemap/CSS chunk-size warnings
If you want, the next safest step is a live end-to-end browser-backed integration pass against your frontend with real authenticated flows for GTM -> Business Plan -> Pitch -> SWOT.


5 files changed
+824
-362
Undo

Review
app/api/routes/business_routes.py
app/api/routes/pitch_analysis_routes.py
app/api/routes/swot_routes.py
app/schemas/business.py
app/schemas/swot.py
 yes continue



I’m continuing with the next high-risk area now: GTM parity and the frontend contract around it, because that’s still the biggest remaining gap between the Flask source and the FastAPI port.

I’m tracing the GTM flow end to end now: frontend request shape, FastAPI route/service behavior, and the original Flask generation path, so the next edits target real integration breaks.

Ran Get-Content -Path 'Server1_FastApi/app/api/routes/gtm_routes.py' | Select-Object -First 420 for 1s


Ran Get-Content -Path 'server2/blueprints/gtm_bp.py' | Select-Object -Skip 1420 -First 520 for 1s


Ran rg -n "generate_gtm_plan|gtm_plan_result|download_gtm_pdf|user_gtm_plans|delete_gtm_plan|generation_status|Target Launch Location/Country|Business Name:" D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src Server1_FastApi/app/api/routes/gtm_routes.py Server1_FastApi/app/services/gtm_service.py server2/blueprints/gtm_bp.py


Ran Get-Content -Path 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\pages\GTMStrategy.tsx' | Select-Object -First 420 for 1s


I’ve confirmed one GTM integration edge already: the frontend still sends Target Launch Location/Country: but the FastAPI route was discarding it. I’m checking the GTM prompt/save/result path now so we keep that field and bring the returned payload closer to the Flask behavior.

Ran Get-Content -Path 'Server1_FastApi/app/celery_tasks/celery_tasks.py' | Select-Object -Skip 120 -First 220 for 1s


Ran rg -n "def _construct_prompt|Target Launch Location/Country|comprehensive_market_data|emit\(|active_generations|pdf_filename|plan_inputs|market_intelligence|strategic_nodes|node_connections" Server1_FastApi/app/services/gtm_service.py Server1_FastApi/app/celery_tasks/celery_tasks.py


Ran Get-Content -Path 'Server1_FastApi/app/services/gtm_service.py' | Select-Object -Skip 240 -First 420 for 1s


Ran rg -n "downloadGtmPdf|planId|pdfFilename|marketIntelligence|strategicNodes|nodeConnections|generationId|flowchart" D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\pages\GTMStrategy.tsx D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\components\business\ShowGTM* D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\components\Loading\gtmloading.tsx for 1s


Ran Get-Content -Path 'server2/blueprints/gtm_bp.py' | Select-Object -Skip 1910 -First 420 for 1s


Ran Get-Content -Path 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\pages\GTMStrategy.tsx' | Select-Object -Skip 520 -First 180 for 1s


Ran Get-Content -Path 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\components\business\ShowGTM.tsx' | Select-Object -First 320 for 1s


Ran rg -n "def generate_strategic_nodes|def generate_node_connections|def get_competitive_landscape|def analyze_market_dynamics|def get_emerging_trends|def analyze_regulatory_environment|def get_investment_activity" server2/blueprints/gtm_bp.py for 1s


Ran rg -n "flowchart|visualization|industry_growth_data|flowchart_prompt|flowchart_image_url|flowchart_available|flowchart_base64|flowchart_filename|flowchart_steps|Target Launch Location/Country" server2/blueprints/gtm_bp.py Server1_FastApi/app/services/gtm_service.py Server1_FastApi/app/api/routes/gtm_routes.py D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\pages\GTMStrategy.tsx


Ran Get-Content -Path 'server2/blueprints/gtm_bp.py' | Select-Object -Skip 220 -First 700 for 1s


Ran Get-Content -Path 'Server1_FastApi/app/services/gtm_service.py' | Select-Object -First 260 for 1s


Ran rg -n "def generate_gtm_plan\(|@celery_app.task\(|gtm_service.generate_plan|progress_type=\"gtm\"|task_id" Server1_FastApi/app/celery_tasks/celery_tasks.py for 8s


Ran Get-Content -Path 'Server1_FastApi/app/celery_tasks/celery_tasks.py' | Select-Object -Skip 394 -First 90


I found a real GTM backend issue that isn’t just parity polish: /generation_status currently depends on in-process memory, but GTM runs in Celery now, so that status view won’t reflect real worker activity. I’m fixing that along with the GTM prompt/result improvements.

Ran rg -n "progress:" Server1_FastApi/app -g '!**/__pycache__/**' for 1s


Ran Get-Content -Path 'Server1_FastApi/app/core/progress.py' | Select-Object -First 260 for 1s


Ran Get-Content -Path 'Server1_FastApi/app/db/redis.py' | Select-Object -First 140 for 1s


Ran Get-Content -Path 'Server1_FastApi/app/celery_tasks/celery_tasks.py' | Select-Object -First 120


Ran (Get-Content -Path 'Server1_FastApi/app/services/gtm_service.py').Length


I’m making the GTM pass a little deeper than just route matching: I’m syncing the worker progress persistence, the richer Flask-style prompt/market-intelligence structure, and the PDF/status behavior so the frontend gets a more faithful payload and the backend can actually report live generation state.

The GTM patch hit an encoding mismatch in the route file, so I’m switching to smaller targeted edits now. I’ve already isolated the exact spots; this is just about applying them safely without clobbering the existing route signatures.

Ran Get-Content -Path 'Server1_FastApi/app/api/routes/gtm_routes.py' | Select-Object -Skip 1 -First 150 for 1s


Ran Get-Content -Path 'Server1_FastApi/app/services/gtm_service.py' | Select-Object -First 80 for 1s


Ran Get-Content -Path 'Server1_FastApi/app/schemas/gtm.py' | Select-Object -First 120 for 1s


I’m replacing the GTM service file in one clean pass now. It’s the safest way to bring over the richer Flask-style market-intelligence, prompt, node, and PDF logic without leaving half-synced helper methods behind.

Rejected
gtm_service.py
+1,088
-0
gtm_service.py
+1,088
-0

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from threading import Lock
from typing import Any, Dict

import requests
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.ai import ai_factory
from app.core.config import settings
from app.db.mongo import get_collection

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

logger = logging.getLogger(__name__)


class GTMService:
    def __init__(self):
        self.generation_lock = Lock()
        self.active_generations = {}
        self.ai_client = ai_factory.get_client("gtm")
        self.deployment = ai_factory.get_deployment("gtm")
        self.serpapi_key = settings.SERPAPI_API_KEY
        self.news_api_key = os.getenv(
            "NEWS_API_KEY", "bb0b82f1d8a74c529fca68561f990d08"
        )
        self.fred_api_key = os.getenv(
            "FRED_API_KEY", "3e7e485e7705143f49393fbeba964862"
        )

    def generate_plan(
        self,
        user_id: str,
        user_inputs: Dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        progress_callback=None,
    ):
        generation_id = f"{user_id}_{int(time.time())}"

        def update_generation(status: str, progress: int):
            with self.generation_lock:
                if generation_id in self.active_generations:
                    self.active_generations[generation_id]["status"] = status
                    self.active_generations[generation_id]["progress"] = progress
                    self.active_generations[generation_id]["updated_at"] = (
                        datetime.utcnow()
                    )

        def emit(progress: int, message: str, data=None, status: str = "processing"):
            update_generation(status, progress)
            if progress_callback:
                payload = dict(data or {})
                payload.setdefault("status", status)
                progress_callback(progress, message, payload)

        try:
            with self.generation_lock:
                self.active_generations[generation_id] = {
                    "user_id": user_id,
                    "start_time": datetime.utcnow(),
                    "status": "starting",
                    "progress": 0,
                }

            business_name = user_inputs["Section 0: Business Identity"]["Business Name:"]
            industry_term = user_inputs[
                "Section 1: Battlefield Entry â€” Strategic Positioning"
            ]["Industry:"]

            emit(10, "Starting GTM plan generation...", status="starting")
            emit(15, "Gathering market intelligence...", status="industry_analysis")

            market_intelligence = self._get_enhanced_industry_analysis(industry_term)
            validated_industry = market_intelligence["validated_industry"]
            comprehensive_market_data = self._format_market_data(
                market_intelligence, validated_industry
            )

            emit(20, "Market intelligence completed", status="prompt_construction")

            prompt = self._construct_prompt(
                business_name,
                validated_industry,
                user_inputs,
                comprehensive_market_data,
            )

            emit(30, "Generating strategic GTM plan with AI...", status="ai_generation")
            gtm_plan = self._generate_ai_plan(prompt)

            emit(50, "GTM plan generated successfully", status="post_processing")

            strategic_nodes = self._generate_strategic_nodes(
                gtm_plan, business_name, validated_industry, user_inputs
            )
            node_connections = self._generate_node_connections(strategic_nodes)

            emit(60, "Processing visualizations and nodes...", status="visualization")
            emit(70, "Generating PDF report...", status="pdf_generation")
            pdf_result = self._generate_pdf_report(gtm_plan, business_name, user_id)

            industry_growth_data = market_intelligence.get("growth_data")
            visualization_type = "strategic_flow" if strategic_nodes else ""
            visualization_available = bool(strategic_nodes)

            emit(80, "Finalizing GTM strategy...", status="finalizing")

            gtm_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "gtm_plan": gtm_plan,
                "business_name": business_name,
                "industry": validated_industry,
                "original_industry": industry_term,
                "market_intelligence": market_intelligence,
                "industry_growth_data": industry_growth_data,
                "generation_id": generation_id,
                "strategic_nodes": strategic_nodes,
                "node_connections": node_connections,
                "visualization_type": visualization_type,
                "visualization_available": visualization_available,
                "pdf_path": pdf_result.get("pdf_path", ""),
                "pdf_filename": pdf_result.get("pdf_filename", ""),
                "plan_inputs": user_inputs,
            }

            async def save_to_db():
                collection = get_collection("gtm_plans")
                return await collection.insert_one(gtm_data)

            plan_id = None
            try:
                result = loop.run_until_complete(save_to_db())
                plan_id = str(result.inserted_id)
            except Exception as db_err:
                logger.error("Database insertion failed: %s", db_err)

            emit(
                100,
                "GTM strategy ready!",
                {"plan_id": plan_id},
                status="completed",
            )

            return {
                "success": True,
                "plan_id": plan_id,
                "gtm_plan": gtm_plan,
                "business_name": business_name,
                "industry": validated_industry,
                "original_industry": industry_term,
                "market_intelligence": market_intelligence,
                "industry_growth_data": industry_growth_data,
                "strategic_nodes": strategic_nodes,
                "node_connections": node_connections,
                "visualization_type": visualization_type,
                "visualization_available": visualization_available,
                "pdf_path": pdf_result.get("pdf_path", ""),
                "pdf_filename": pdf_result.get("pdf_filename", ""),
                "generation_id": generation_id,
            }
        except Exception as exc:
            logger.error("Error in GTM generation: %s", exc)
            emit(100, f"Error: {str(exc)}", status="error")
            raise
        finally:
            with self.generation_lock:
                self.active_generations.pop(generation_id, None)

    def _get_enhanced_industry_analysis(self, industry_term: str) -> Dict[str, Any]:
        try:
            validated_industry = self._validate_and_correct_industry(industry_term)
            industry_growth = self._get_industry_growth_rate(industry_term)
            return {
                "validated_industry": validated_industry,
                "growth_data": industry_growth["growth_data"],
                "market_dynamics": self._analyze_market_dynamics(validated_industry),
                "competitive_landscape": self._get_competitive_landscape(
                    validated_industry
                ),
                "emerging_trends": self._get_emerging_trends(validated_industry),
                "regulatory_environment": self._analyze_regulatory_environment(
                    validated_industry
                ),
                "investment_activity": self._get_investment_activity(
                    validated_industry
                ),
            }
        except Exception as exc:
            logger.error("Error in enhanced GTM analysis: %s", exc)
            return {
                "validated_industry": industry_term,
                "growth_data": "Analysis unavailable",
                "market_dynamics": {},
                "competitive_landscape": {},
                "emerging_trends": [],
                "regulatory_environment": {},
                "investment_activity": {},
            }

    def _validate_and_correct_industry(self, industry_input: str) -> str:
        try:
            prompt = f"""
            You are an industry classification expert. The user provided this industry: "{industry_input}"

            Return ONLY:
            INDUSTRY: [Standardized Industry Name]
            """
            if not self.ai_client or not self.deployment:
                return industry_input

            response = self.ai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You standardize industry names for market research purposes."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.deployment,
                temperature=0.1,
            )
            result = response.choices[0].message.content.strip()
            if "INDUSTRY:" in result:
                return result.split("INDUSTRY:", 1)[1].strip()
            return industry_input
        except Exception as exc:
            logger.error("Industry validation error: %s", exc)
            return industry_input

    def _get_industry_growth_rate(self, industry_term: str) -> Dict[str, str]:
        if not self.serpapi_key:
            return {"growth_data": "SERP API Key missing"}

        try:
            validated_industry = self._validate_and_correct_industry(industry_term)
            search_queries = [
                f"{validated_industry} market size growth rate 2024 2025 forecast CAGR",
                f"{validated_industry} industry growth statistics revenue 2024 2025",
                f"{validated_industry} market trends TAM SAM SOM analysis 2024",
            ]
            all_growth_info = ""
            for query in search_queries:
                try:
                    params = {
                        "engine": "google",
                        "q": query,
                        "api_key": self.serpapi_key,
                        "num": 5,
                        "hl": "en",
                    }
                    response = requests.get(  # nosec B113
                        "https://serpapi.com/search", params=params
                    )
                    results = response.json()
                    for result in results.get("organic_results", [])[:3]:
                        snippet = result.get("snippet")
                        if snippet:
                            all_growth_info += f"- {snippet}\n"
                    time.sleep(0.5)
                except Exception as query_error:
                    logger.warning("GTM growth query failed for '%s': %s", query, query_error)

            if not all_growth_info.strip():
                all_growth_info = (
                    f"Specific growth data for {validated_industry} not found. "
                    "Industry estimated at 10-15% CAGR based on broader sector trends."
                )
            return {"growth_data": all_growth_info.strip()}
        except Exception as exc:
            logger.warning("Growth rate fetch error: %s", exc)
            return {"growth_data": "Error fetching growth data"}

    def _get_google_trends(self, industry: str):
        if not TrendReq:
            return None
        try:
            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([industry], timeframe="today 12-m")
            data = pytrends.interest_over_time()
            if not data.empty:
                direction = (
                    "Increasing"
                    if data[industry].iloc[-1] > data[industry].iloc[0]
                    else "Stable"
                )
                return {"trend_direction": direction}
        except Exception as exc:
            logger.warning("Trends error: %s", exc)
        return None

    def _analyze_market_dynamics(self, industry: str) -> Dict[str, str]:
        try:
            dynamics = {
                "supply_demand_balance": "Analyzing...",
                "pricing_trends": "Analyzing...",
                "market_maturity": "Analyzing...",
                "disruption_potential": "Analyzing...",
                "barrier_to_entry": "Analyzing...",
                "customer_acquisition_cost_trend": "Analyzing...",
            }

            trends = self._get_google_trends(industry)
            if trends:
                if trends["trend_direction"] == "Increasing":
                    dynamics["supply_demand_balance"] = (
                        "High demand with growing interest"
                    )
                    dynamics["market_maturity"] = (
                        "Growth stage - increasing search interest"
                    )
                else:
                    dynamics["supply_demand_balance"] = (
                        "Stable demand with mature market"
                    )
                    dynamics["market_maturity"] = "Mature stage - stable interest"

            industry_lower = industry.lower()
            if any(
                term in industry_lower
                for term in ["tech", "software", "saas", "ai", "digital"]
            ):
                dynamics["barrier_to_entry"] = (
                    "Medium-High - requires technical expertise and capital"
                )
                dynamics["disruption_potential"] = (
                    "Very High - rapid technological change"
                )
            elif any(
                term in industry_lower for term in ["retail", "ecommerce", "consumer"]
            ):
                dynamics["barrier_to_entry"] = (
                    "Low-Medium - accessible but competitive"
                )
                dynamics["disruption_potential"] = (
                    "High - digital transformation ongoing"
                )
            elif any(
                term in industry_lower
                for term in ["finance", "banking", "insurance"]
            ):
                dynamics["barrier_to_entry"] = "High - regulatory requirements"
                dynamics["disruption_potential"] = "High - fintech disruption"
            else:
                dynamics["barrier_to_entry"] = "Medium - varies by specific sector"
                dynamics["disruption_potential"] = (
                    "Moderate - depends on technology adoption"
                )

            dynamics["pricing_trends"] = (
                "Competitive pricing pressure with value-based differentiation"
            )
            dynamics["customer_acquisition_cost_trend"] = (
                "Rising in digital markets; acquisition efficiency is becoming a moat"
            )
            return dynamics
        except Exception as exc:
            logger.error("Error analyzing market dynamics: %s", exc)
            return {
                "supply_demand_balance": "Unable to analyze - data unavailable",
                "pricing_trends": "Unable to analyze - data unavailable",
                "market_maturity": "Unable to analyze - data unavailable",
                "disruption_potential": "Unable to analyze - data unavailable",
                "barrier_to_entry": "Unable to analyze - data unavailable",
                "customer_acquisition_cost_trend": (
                    "Unable to analyze - data unavailable"
                ),
            }

    def _get_competitive_landscape(self, industry: str) -> Dict[str, Any]:
        try:
            landscape = {
                "market_concentration": "Analyzing...",
                "competitive_intensity": "Analyzing...",
                "differentiation_opportunities": [],
                "white_space_opportunities": [],
            }

            if self.serpapi_key:
                params = {
                    "engine": "google",
                    "q": f"{industry} market share leaders competition analysis 2024",
                    "api_key": self.serpapi_key,
                    "num": 10,
                }
                response = requests.get("https://serpapi.com/search", params=params)  # nosec B113
                if response.status_code == 200:
                    results = response.json()
                    snippets = [
                        result.get("snippet", "")
                        for result in results.get("organic_results", [])
                    ]
                    full_text = " ".join(snippets).lower()
                    if "fragmented" in full_text or "many players" in full_text:
                        landscape["market_concentration"] = (
                            "Fragmented - many competitors, no dominant player"
                        )
                    elif "dominated" in full_text or "leader" in full_text:
                        landscape["market_concentration"] = (
                            "Concentrated - few major players dominate"
                        )
                    else:
                        landscape["market_concentration"] = (
                            "Moderate concentration - mix of large and small players"
                        )

                    competition_keywords = [
                        "competitive",
                        "competition",
                        "rivalry",
                        "competing",
                    ]
                    intensity_count = sum(
                        1 for keyword in competition_keywords if keyword in full_text
                    )
                    landscape["competitive_intensity"] = (
                        "High - intense competition"
                        if intensity_count > 2
                        else "Moderate - healthy competition"
                    )

            if any(term in industry.lower() for term in ["tech", "software", "saas"]):
                landscape["differentiation_opportunities"] = [
                    "AI/ML-powered features",
                    "Superior user experience",
                    "Vertical specialization",
                    "API-first approach",
                    "No-code/low-code solutions",
                ]
                landscape["white_space_opportunities"] = [
                    "SMB segment automation",
                    "Industry-specific solutions",
                    "Emerging markets expansion",
                    "Integration platforms",
                ]
            elif any(term in industry.lower() for term in ["retail", "ecommerce"]):
                landscape["differentiation_opportunities"] = [
                    "Personalization engine",
                    "Omnichannel experience",
                    "Sustainable practices",
                    "Social commerce integration",
                    "Same-day delivery",
                ]
                landscape["white_space_opportunities"] = [
                    "Niche market segments",
                    "B2B marketplaces",
                    "Subscription models",
                    "AR/VR shopping",
                ]
            else:
                landscape["differentiation_opportunities"] = [
                    "Digital transformation",
                    "Customer experience focus",
                    "Data-driven insights",
                    "Sustainability initiatives",
                    "Partnership ecosystems",
                ]
                landscape["white_space_opportunities"] = [
                    "Underserved segments",
                    "Geographic expansion",
                    "Service innovation",
                    "Platform business models",
                ]

            return landscape
        except Exception as exc:
            logger.error("Error getting competitive landscape: %s", exc)
            return {
                "market_concentration": "Unable to analyze",
                "competitive_intensity": "Unable to analyze",
                "differentiation_opportunities": ["Market analysis unavailable"],
                "white_space_opportunities": ["Market analysis unavailable"],
            }

    def _get_emerging_trends(self, industry: str):
        try:
            if any(term in industry.lower() for term in ["tech", "software"]):
                return [
                    "AI/ML becoming standard in all products",
                    "Shift to subscription and usage-based pricing",
                    "Privacy-first architecture requirements",
                    "Edge computing and distributed systems",
                    "Developer experience as competitive advantage",
                ]
            if any(term in industry.lower() for term in ["retail", "ecommerce"]):
                return [
                    "Social commerce integration",
                    "Sustainable and ethical sourcing",
                    "Hyper-personalization through AI",
                    "Live shopping and video commerce",
                    "Blockchain for supply chain transparency",
                ]
            return [
                "Digital transformation acceleration",
                "Remote/hybrid work normalization",
                "ESG focus increasing",
                "Data privacy and security prioritization",
                "Platform economy expansion",
            ]
        except Exception as exc:
            logger.error("Error getting emerging trends: %s", exc)
            return [
                "Digital transformation initiatives",
                "AI and automation adoption",
                "Sustainability focus",
                "Customer experience optimization",
                "Data-driven decision making",
            ]

    def _analyze_regulatory_environment(self, industry: str) -> Dict[str, Any]:
        try:
            reg_env = {
                "key_regulations": [],
                "compliance_complexity": "Medium",
                "regulatory_trends": "Increasing requirements",
                "geographic_considerations": "Varies by region",
            }

            industry_lower = industry.lower()
            if any(
                term in industry_lower
                for term in ["finance", "banking", "fintech", "payment"]
            ):
                reg_env["key_regulations"] = [
                    "PCI DSS",
                    "SOX",
                    "BASEL III",
                    "PSD2",
                    "AML/KYC",
                ]
                reg_env["compliance_complexity"] = "Very High"
                reg_env["regulatory_trends"] = (
                    "Increasing scrutiny on digital finance and crypto"
                )
                reg_env["geographic_considerations"] = (
                    "Highly regulated globally, especially in US/EU"
                )
            elif any(
                term in industry_lower
                for term in ["health", "medical", "pharma", "biotech"]
            ):
                reg_env["key_regulations"] = [
                    "HIPAA",
                    "FDA",
                    "GDPR (health data)",
                    "MDR",
                    "Clinical Trials",
                ]
                reg_env["compliance_complexity"] = "Very High"
                reg_env["regulatory_trends"] = (
                    "Digital health regulations evolving rapidly"
                )
                reg_env["geographic_considerations"] = (
                    "Strict regulations in all major markets"
                )
            elif any(
                term in industry_lower for term in ["data", "software", "tech", "saas"]
            ):
                reg_env["key_regulations"] = [
                    "GDPR",
                    "CCPA",
                    "SOC2",
                    "ISO 27001",
                    "COPPA",
                ]
                reg_env["compliance_complexity"] = "High"
                reg_env["regulatory_trends"] = "Privacy laws expanding globally"
                reg_env["geographic_considerations"] = (
                    "EU strictest, US state-by-state variation"
                )
            elif any(
                term in industry_lower for term in ["retail", "ecommerce", "consumer"]
            ):
                reg_env["key_regulations"] = [
                    "PCI DSS",
                    "GDPR",
                    "CCPA",
                    "Consumer Protection Laws",
                    "ADA",
                ]
                reg_env["compliance_complexity"] = "Medium"
                reg_env["regulatory_trends"] = (
                    "Focus on data privacy and accessibility"
                )
                reg_env["geographic_considerations"] = (
                    "Varies by product category and region"
                )
            else:
                reg_env["key_regulations"] = [
                    "GDPR",
                    "Industry Standards",
                    "Local Business Laws",
                    "Tax Compliance",
                ]
            return reg_env
        except Exception as exc:
            logger.error("Error analyzing regulatory environment: %s", exc)
            return {
                "key_regulations": ["GDPR", "Industry Standards"],
                "compliance_complexity": "Medium",
                "regulatory_trends": "Increasing requirements",
                "geographic_considerations": "Varies by region",
            }

    def _get_investment_activity(self, industry: str) -> Dict[str, Any]:
        try:
            investment_data = {
                "total_funding_last_year": "Analyzing...",
                "average_deal_size": "Analyzing...",
                "funding_stage_focus": "Analyzing...",
                "top_investors": [],
                "exit_activity": "Analyzing...",
            }

            industry_lower = industry.lower()
            if any(term in industry_lower for term in ["ai", "ml", "artificial intelligence"]):
                investment_data.update(
                    {
                        "total_funding_last_year": "$50B+ globally in AI/ML startups",
                        "average_deal_size": "$15-25M for Series A",
                        "funding_stage_focus": "Series A and B (growth stage)",
                        "top_investors": [
                            "Sequoia",
                            "a16z",
                            "Google Ventures",
                            "Microsoft Ventures",
                        ],
                        "exit_activity": "High M&A activity, several unicorns",
                    }
                )
            elif any(term in industry_lower for term in ["fintech", "finance", "payment"]):
                investment_data.update(
                    {
                        "total_funding_last_year": "$30B+ in fintech globally",
                        "average_deal_size": "$20-30M for Series A",
                        "funding_stage_focus": "All stages active",
                        "top_investors": [
                            "Ribbit Capital",
                            "Accel",
                            "Index Ventures",
                            "QED",
                        ],
                        "exit_activity": "Strong IPO and acquisition pipeline",
                    }
                )
            elif any(term in industry_lower for term in ["saas", "software"]):
                investment_data.update(
                    {
                        "total_funding_last_year": "$40B+ in B2B SaaS",
                        "average_deal_size": "$10-20M for Series A",
                        "funding_stage_focus": "Series A through C",
                        "top_investors": [
                            "Bessemer",
                            "Insight Partners",
                            "Tiger Global",
                            "Sequoia",
                        ],
                        "exit_activity": "Active M&A market, strategic acquisitions",
                    }
                )
            else:
                investment_data.update(
                    {
                        "total_funding_last_year": "Varies by specific sector",
                        "average_deal_size": "$5-15M for Series A",
                        "funding_stage_focus": "Seed and Series A",
                        "top_investors": [
                            "General Catalyst",
                            "NEA",
                            "Kleiner Perkins",
                            "Founders Fund",
                        ],
                        "exit_activity": "Moderate M&A activity",
                    }
                )
            return investment_data
        except Exception as exc:
            logger.error("Error getting investment activity: %s", exc)
            return {
                "total_funding_last_year": "Data unavailable",
                "average_deal_size": "Varies by stage",
                "funding_stage_focus": "All stages",
                "top_investors": ["Major VC firms"],
                "exit_activity": "Market dependent",
            }

    def _format_market_data(
        self, market_intelligence: Dict[str, Any], validated_industry: str
    ) -> str:
        return f"""
        VALIDATED INDUSTRY: {validated_industry}

        GROWTH DATA:
        {market_intelligence.get("growth_data", "N/A")}

        MARKET DYNAMICS:
        - Supply/Demand: {market_intelligence.get("market_dynamics", {}).get("supply_demand_balance", "N/A")}
        - Pricing Trends: {market_intelligence.get("market_dynamics", {}).get("pricing_trends", "N/A")}
        - Market Maturity: {market_intelligence.get("market_dynamics", {}).get("market_maturity", "N/A")}
        - Disruption Potential: {market_intelligence.get("market_dynamics", {}).get("disruption_potential", "N/A")}
        - Barriers to Entry: {market_intelligence.get("market_dynamics", {}).get("barrier_to_entry", "N/A")}
        - CAC Trend: {market_intelligence.get("market_dynamics", {}).get("customer_acquisition_cost_trend", "N/A")}

        COMPETITIVE LANDSCAPE:
        - Market Concentration: {market_intelligence.get("competitive_landscape", {}).get("market_concentration", "N/A")}
        - Competitive Intensity: {market_intelligence.get("competitive_landscape", {}).get("competitive_intensity", "N/A")}
        - Differentiation Opportunities: {", ".join(market_intelligence.get("competitive_landscape", {}).get("differentiation_opportunities", []))}
        - White Space Opportunities: {", ".join(market_intelligence.get("competitive_landscape", {}).get("white_space_opportunities", []))}

        EMERGING TRENDS:
        {"; ".join(market_intelligence.get("emerging_trends", []))}

        REGULATORY ENVIRONMENT:
        - Key Regulations: {", ".join(market_intelligence.get("regulatory_environment", {}).get("key_regulations", []))}
        - Compliance Complexity: {market_intelligence.get("regulatory_environment", {}).get("compliance_complexity", "N/A")}
        - Regulatory Trends: {market_intelligence.get("regulatory_environment", {}).get("regulatory_trends", "N/A")}

        INVESTMENT ACTIVITY:
        - Total Funding: {market_intelligence.get("investment_activity", {}).get("total_funding_last_year", "N/A")}
        - Average Deal Size: {market_intelligence.get("investment_activity", {}).get("average_deal_size", "N/A")}
        - Funding Focus: {market_intelligence.get("investment_activity", {}).get("funding_stage_focus", "N/A")}
        - Exit Activity: {market_intelligence.get("investment_activity", {}).get("exit_activity", "N/A")}
        """

    def _construct_prompt(
        self,
        business_name: str,
        validated_industry: str,
        user_inputs: Dict[str, Any],
        market_data: str,
    ) -> str:
        risk_scale = user_inputs["Section 4: Risk Appetite â€” Aggression Meter"].get(
            "Scale of 1-10 (1 = Safe, 10 = Extreme):",
            "5",
        )
        return f"""
        You are a legendary GTM strategist who has scaled 50+ unicorns and led multiple successful IPOs.
        Your GTM plans are known for aggressive tactics, data-driven thinking, and immediate actionability.
        Think like a military strategist planning a market conquest combined with a Silicon Valley growth hacker.

        Generate a WORLD-CLASS, PROFESSIONAL Go-To-Market strategy for:

        BUSINESS: {business_name}
        VALIDATED INDUSTRY: {validated_industry}

        CLIENT INPUTS:
        {json.dumps(user_inputs, indent=2)}

        REAL-TIME MARKET INTELLIGENCE:
        {market_data}

        Create these sections:
        1. Executive Summary & Strategic Thesis
        2. Market Domination Strategy
        3. Customer Acquisition Warfare
        4. Revenue Acceleration Engine
        5. Tactical Execution Roadmap
        6. Growth Hacking Playbook
        7. Competitive Warfare Tactics
        8. Metrics & KPI Dashboard
        9. Resource Allocation & Team Building
        10. Risk Mitigation & Scenario Planning
        11. Fundraising & Exit Strategy
        12. 100-Day Battle Plan
        13. Technology & Automation Stack
        14. Psychological Warfare & Brand Strategy
        15. Global Expansion Playbook

        REQUIREMENTS:
        - Use rich markdown formatting.
        - Include a detailed execution matrix in markdown table format with phases, timelines, activities, owners, budget allocation, metrics, risks, and mitigations.
        - Include specific numbers, percentages, timelines, and measurable KPIs.
        - Make every recommendation concrete and immediately actionable.
        - Calibrate aggressiveness to a risk tolerance of {risk_scale}/10.
        - If a launch location is provided, tailor market entry and regulatory recommendations to that geography.
        """

    def _generate_ai_plan(self, prompt: str) -> str:
        if not self.ai_client or not self.deployment:
            raise RuntimeError("AI Client not configured")

        try:
            response = self.ai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the world's best GTM strategist. "
                            "You create aggressive, data-driven, highly actionable market domination plans. "
                            "Every recommendation must be specific, measurable, and time-bound."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                model=self.deployment,
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(f"AI Error: {exc}") from exc

    def _generate_strategic_nodes(
        self, plan: str, name: str, industry: str, inputs: Dict[str, Any]
    ):
        _ = plan
        try:
            return [
                {
                    "id": "core-strategy",
                    "type": "strategy",
                    "title": f"{name} Core Strategy",
                    "description": (
                        f"Dominate {industry} through "
                        f"{inputs['Section 1: Battlefield Entry â€” Strategic Positioning']['GTM Mode Preference (Guerrilla Warfare, Blitzkrieg, Stealth Mode, Community-Led):']}"
                    ),
                    "metrics": [
                        {"label": "TAM", "value": "$2.5B"},
                        {"label": "Target Share", "value": "15%"},
                        {"label": "Timeline", "value": "18 months"},
                    ],
                },
                {
                    "id": "market-entry",
                    "type": "launch",
                    "title": "Market Entry Strategy",
                    "description": (
                        "Phased rollout targeting early adopters and strategic accounts"
                    ),
                    "metrics": [
                        {"label": "Phase 1", "value": "3 months"},
                        {"label": "Initial Targets", "value": "100 accounts"},
                        {"label": "Success Metric", "value": "25% activation"},
                    ],
                },
                {
                    "id": "customer-acquisition",
                    "type": "growth",
                    "title": "Customer Acquisition Engine",
                    "description": (
                        "Multi-channel approach targeting "
                        f"{inputs['Section 1: Battlefield Entry â€” Strategic Positioning']['Who are you hunting?']}"
                    ),
                    "metrics": [
                        {"label": "CAC Target", "value": "$150"},
                        {"label": "Channels", "value": "5 primary"},
                        {"label": "Conv Rate", "value": "15%"},
                    ],
                },
                {
                    "id": "revenue-growth",
                    "type": "revenue",
                    "title": "Revenue Acceleration",
                    "description": (
                        "Scale from $0 to $10M ARR through land-and-expand strategy"
                    ),
                    "metrics": [
                        {"label": "Month 6", "value": "$1M ARR"},
                        {"label": "Month 12", "value": "$5M ARR"},
                        {"label": "Month 18", "value": "$10M ARR"},
                    ],
                },
                {
                    "id": "competitive-advantage",
                    "type": "moat",
                    "title": "Competitive Moat",
                    "description": (
                        "Leverage "
                        f"{inputs['Section 2: Founder DNA â€” Weapons Inventory']['Unfair Advantage:']}"
                        " for sustainable advantage"
                    ),
                    "metrics": [
                        {"label": "NPS Target", "value": "70+"},
                        {"label": "Retention", "value": "95%"},
                        {"label": "LTV:CAC", "value": "5:1"},
                    ],
                },
                {
                    "id": "scale-operations",
                    "type": "scale",
                    "title": "Scale Infrastructure",
                    "description": "Build systems and team for 10x growth",
                    "metrics": [
                        {"label": "Team Size", "value": "50+"},
                        {"label": "Automation", "value": "80%"},
                        {"label": "Efficiency", "value": "2x"},
                    ],
                },
            ]
        except Exception as exc:
            logger.error("Error generating strategic nodes: %s", exc)
            return []

    def _generate_node_connections(self, nodes):
        _ = nodes
        try:
            flow_map = {
                "core-strategy": ["market-entry", "competitive-advantage"],
                "market-entry": ["customer-acquisition"],
                "customer-acquisition": ["revenue-growth"],
                "revenue-growth": ["scale-operations"],
                "competitive-advantage": ["revenue-growth", "scale-operations"],
            }
            connections = []
            for source, targets in flow_map.items():
                for target in targets:
                    connections.append(
                        {
                            "id": f"{source}-{target}",
                            "source": source,
                            "target": target,
                            "type": "strategic",
                            "animated": True,
                        }
                    )
            return connections
        except Exception as exc:
            logger.error("Error generating node connections: %s", exc)
            return []

    def _generate_pdf_report(self, plan: str, business_name: str, user_id: str):
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            upload_dir = os.path.join(base_dir, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            filename = (
                f"{user_id}_gtm_battle_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            filepath = os.path.join(upload_dir, filename)

            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )
            story = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2c3e50"),
            )
            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading1"],
                fontSize=16,
                spaceAfter=12,
                spaceBefore=20,
                textColor=colors.HexColor("#34495e"),
            )
            subheading_style = ParagraphStyle(
                "CustomSubHeading",
                parent=styles["Heading2"],
                fontSize=14,
                spaceAfter=10,
                spaceBefore=15,
                textColor=colors.HexColor("#5d6d7e"),
            )
            normal_style = ParagraphStyle(
                "CustomNormal",
                parent=styles["Normal"],
                fontSize=10,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
            )

            story.append(Paragraph("GTM STRATEGY PLAYBOOK", title_style))
            story.append(Paragraph(f"<b>{business_name}</b>", heading_style))
            story.append(
                Paragraph(
                    f"Generated on: {datetime.now().strftime('%B %d, %Y')}",
                    normal_style,
                )
            )
            story.append(Spacer(1, 20))

            for section in plan.split("\n\n"):
                stripped = section.strip()
                if not stripped:
                    continue

                if stripped.startswith("#"):
                    heading_level = len(stripped) - len(stripped.lstrip("#"))
                    heading_text = stripped.lstrip("#").strip()
                    if heading_level == 1:
                        story.append(Paragraph(heading_text, heading_style))
                    elif heading_level == 2:
                        story.append(Paragraph(heading_text, subheading_style))
                    else:
                        story.append(Paragraph(f"<b>{heading_text}</b>", normal_style))
                elif stripped.startswith("|"):
                    table_data = self._parse_markdown_table(stripped)
                    if table_data:
                        table = Table(table_data, hAlign="LEFT")
                        table.setStyle(
                            TableStyle(
                                [
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ]
                            )
                        )
                        story.append(table)
                        story.append(Spacer(1, 12))
                else:
                    for line in stripped.split("\n"):
                        clean_line = line.strip()
                        if not clean_line:
                            continue
                        if clean_line.startswith("-") or clean_line.startswith("*"):
                            bullet_text = clean_line.lstrip("-*").strip()
                            story.append(Paragraph(f"• {bullet_text}", normal_style))
                        else:
                            story.append(
                                Paragraph(self._clean_markdown(clean_line), normal_style)
                            )
                    story.append(Spacer(1, 6))

            doc.build(story)
            return {"success": True, "pdf_path": filepath, "pdf_filename": filename}
        except Exception as exc:
            logger.error("PDF Error: %s", exc)
            return {"success": False, "error": str(exc)}

    def _parse_markdown_table(self, table_text: str):
        try:
            lines = table_text.strip().split("\n")
            table_data = []
            for line in lines:
                if "|" not in line:
                    continue
                if re.match(r"^[\s\|\-:]+$", line):
                    continue
                cells = [cell.strip() for cell in line.split("|")]
                if cells and cells[0] == "":
                    cells = cells[1:]
                if cells and cells[-1] == "":
                    cells = cells[:-1]
                if cells:
                    table_data.append(cells)
            return table_data if table_data else None
        except Exception as exc:
            logger.error("Error parsing markdown table: %s", exc)
            return None

    def _clean_markdown(self, text: str) -> str:
        text = re.sub(r"<br\s*/?>", "<br/>", text, flags=re.IGNORECASE)
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"#{1,6}\s*", "", text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        text = text.replace("&lt;br/&gt;", "<br/>")
        return text


gtm_service = GTMService()
The full-file rewrite is too large for a single patch on this Windows workspace, so I’m applying the GTM changes in smaller chunks instead. That’s slower, but it’s the safest path and avoids partial corruption.

Ran $i=1; Get-Content 'Server1_FastApi/app/services/gtm_service.py' | ForEach-Object {('{0,4}: {1}' -f $i, $_); $i++} | Select-Object -First 220 for 3s


Ran $i=1; Get-Content 'Server1_FastApi/app/api/routes/gtm_routes.py' | ForEach-Object {('{0,4}: {1}' -f $i, $_); $i++} | Select-Object -First 360 for 2s


Ran $i=221; Get-Content 'Server1_FastApi/app/services/gtm_service.py' | Select-Object -Skip 220 | ForEach-Object {('{0,4}: {1}' -f $i, $_); $i++} | Select-Object -First 240 for 2s


Edited file
gtm_service.py
+74
-45

import os
import json
import time
import logging
import requests
import asyncio
from datetime import datetime
from typing import Dict, Any
from threading import Lock
import os
import json
import time
import logging
import re
import requests
import asyncio
from datetime import datetime
from typing import Dict, Any
from threading import Lock
from app.db.mongo import get_collection

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


        # Helper to emit progress
        def update_generation(status, progress):
            with self.generation_lock:
                if generation_id in self.active_generations:
                    self.active_generations[generation_id]["status"] = status
                    self.active_generations[generation_id]["progress"] = progress
                    self.active_generations[generation_id]["updated_at"] = (
                        datetime.utcnow()
                    )

        # Helper to emit progress
        def emit(p, m, d=None, status=None):
            update_generation(status or "processing", p)
            if progress_callback:
                # For now, we simulate the logic from the blueprint.
                self.active_generations[generation_id] = {
                    "user_id": user_id,
                    "start_time": datetime.utcnow(),
                    "status": "starting",
                }
                self.active_generations[generation_id] = {
                    "user_id": user_id,
                    "start_time": datetime.utcnow(),
                    "status": "starting",
                    "progress": 0,
                }

            logger.info(f"Starting GTM generation {generation_id} for user {user_id}")
            emit(10, "Starting GTM plan generation...")
            emit(10, "Starting GTM plan generation...", status="starting")

            # Market Intelligence
            emit(15, "Gathering market intelligence...")
            emit(15, "Gathering market intelligence...", status="industry_analysis")
            market_intelligence = self._get_enhanced_industry_analysis(industry_term)

            emit(20, "Market intelligence completed")
            emit(20, "Market intelligence completed", status="prompt_construction")


            emit(30, "Generating strategic GTM plan with AI...")
            emit(30, "Generating strategic GTM plan with AI...", status="ai_generation")


            emit(50, "GTM plan generated successfully")
            emit(50, "GTM plan generated successfully", status="post_processing")

            # Post Processing
            emit(60, "Processing visualizations and nodes...")
            emit(60, "Processing visualizations and nodes...", status="visualization")
            strategic_nodes = self._generate_strategic_nodes(
            # PDF Generation
            emit(70, "Generating PDF report...")
            pdf_result = self._generate_pdf_report(gtm_plan, business_name, user_id)

            emit(80, "Finalizing GTM strategy...")
            emit(70, "Generating PDF report...", status="pdf_generation")
            pdf_result = self._generate_pdf_report(gtm_plan, business_name, user_id)

            emit(80, "Finalizing GTM strategy...", status="finalizing")
            industry_growth_data = market_intelligence.get("growth_data")
            visualization_type = "strategic_flow" if strategic_nodes else ""
            visualization_available = bool(strategic_nodes)

                "original_industry": industry_term,
                "market_intelligence": market_intelligence,
                "generation_id": generation_id,
                "strategic_nodes": strategic_nodes,
                "node_connections": node_connections,
                "pdf_path": pdf_result.get("pdf_path", ""),
                "pdf_filename": pdf_result.get("pdf_filename", ""),
                "plan_inputs": user_inputs,
                "market_intelligence": market_intelligence,
                "industry_growth_data": industry_growth_data,
                "generation_id": generation_id,
                "strategic_nodes": strategic_nodes,
                "node_connections": node_connections,
                "visualization_type": visualization_type,
                "visualization_available": visualization_available,
                "pdf_path": pdf_result.get("pdf_path", ""),
                "pdf_filename": pdf_result.get("pdf_filename", ""),
                "plan_inputs": user_inputs,
            }

            emit(100, "GTM strategy ready!", {"plan_id": plan_id})
            emit(100, "GTM strategy ready!", {"plan_id": plan_id}, status="completed")

                "industry": validated_industry,
                "original_industry": industry_term,
                "market_intelligence": market_intelligence,
                "strategic_nodes": strategic_nodes,
                "node_connections": node_connections,
                "pdf_path": pdf_result.get("pdf_path", ""),
                "pdf_filename": pdf_result.get("pdf_filename", ""),
                "generation_id": generation_id,
                "original_industry": industry_term,
                "market_intelligence": market_intelligence,
                "industry_growth_data": industry_growth_data,
                "strategic_nodes": strategic_nodes,
                "node_connections": node_connections,
                "visualization_type": visualization_type,
                "visualization_available": visualization_available,
                "pdf_path": pdf_result.get("pdf_path", ""),
                "pdf_filename": pdf_result.get("pdf_filename", ""),
                "generation_id": generation_id,
            }
Edited file
gtm_service.py
+412
-105


    def _get_industry_growth_rate(self, industry_term):
        # Using SerpApi if available
        if not self.serpapi_key:
            return {"growth_data": "SERP API Key missing"}

        try:
            params = {
                "engine": "google",
                "q": f"{industry_term} market size growth rate 2024 2025 forecast CAGR",
                "api_key": self.serpapi_key,
                "num": 3,
            }
            response = requests.get("https://serpapi.com/search", params=params)  # nosec B113
            results = response.json()
            snippets = [
                r.get("snippet", "") for r in results.get("organic_results", [])
            ]
            return {"growth_data": "\n".join(snippets) if snippets else "No data found"}
        except Exception as e:
            logger.warning(f"Growth rate fetch error: {e}")
            return {"growth_data": "Error fetching growth data"}

    def _analyze_market_dynamics(self, industry):
        # Simplified logic from blueprint
        dynamics = {}
        # Google Trends
        trends = self._get_google_trends(industry)
        if trends:
            dynamics["supply_demand_balance"] = (
                "High demand" if trends["trend_direction"] == "Increasing" else "Stable"
            )

        # Add basic logic based on industry keywords (ported from blueprint)
        industry_lower = industry.lower()
        if any(x in industry_lower for x in ["tech", "software", "saas"]):
            dynamics["barrier_to_entry"] = "Medium-High"
        else:
            dynamics["barrier_to_entry"] = "Medium"

        return dynamics
    def _get_industry_growth_rate(self, industry_term):
        if not self.serpapi_key:
            return {"growth_data": "SERP API Key missing"}

        try:
            validated_industry = self._validate_and_correct_industry(industry_term)
            search_queries = [
                f"{validated_industry} market size growth rate 2024 2025 forecast CAGR",
                f"{validated_industry} industry growth statistics revenue 2024 2025",
                f"{validated_industry} market trends TAM SAM SOM analysis 2024",
            ]
            all_growth_info = ""

            for query in search_queries:
                try:
                    params = {
                        "engine": "google",
                        "q": query,
                        "api_key": self.serpapi_key,
                        "num": 5,
                        "hl": "en",
                    }
                    response = requests.get(  # nosec B113
                        "https://serpapi.com/search", params=params
                    )
                    results = response.json()
                    for result in results.get("organic_results", [])[:3]:
                        snippet = result.get("snippet")
                        if snippet:
                            all_growth_info += f"- {snippet}\n"
                    time.sleep(0.5)
                except Exception as query_error:
                    logger.warning(
                        "Growth query failed for '%s': %s", query, query_error
                    )

            if not all_growth_info.strip():
                all_growth_info = (
                    f"Specific growth data for {validated_industry} not found. "
                    "Industry estimated at 10-15% CAGR based on broader sector trends."
                )

            return {"growth_data": all_growth_info.strip()}
        except Exception as e:
            logger.warning(f"Growth rate fetch error: {e}")
            return {"growth_data": "Error fetching growth data"}

    def _analyze_market_dynamics(self, industry):
        try:
            dynamics = {
                "supply_demand_balance": "Analyzing...",
                "pricing_trends": "Analyzing...",
                "market_maturity": "Analyzing...",
                "disruption_potential": "Analyzing...",
                "barrier_to_entry": "Analyzing...",
                "customer_acquisition_cost_trend": "Analyzing...",
            }

            trends = self._get_google_trends(industry)
            if trends:
                if trends["trend_direction"] == "Increasing":
                    dynamics["supply_demand_balance"] = (
                        "High demand with growing interest"
                    )
                    dynamics["market_maturity"] = (
                        "Growth stage - increasing search interest"
                    )
                else:
                    dynamics["supply_demand_balance"] = (
                        "Stable demand with mature market"
                    )
                    dynamics["market_maturity"] = "Mature stage - stable interest"

            industry_lower = industry.lower()
            if any(
                x in industry_lower for x in ["tech", "software", "saas", "ai", "digital"]
            ):
                dynamics["barrier_to_entry"] = (
                    "Medium-High - requires technical expertise and capital"
                )
                dynamics["disruption_potential"] = (
                    "Very High - rapid technological change"
                )
            elif any(x in industry_lower for x in ["retail", "ecommerce", "consumer"]):
                dynamics["barrier_to_entry"] = (
                    "Low-Medium - accessible but competitive"
                )
                dynamics["disruption_potential"] = (
                    "High - digital transformation ongoing"
                )
            elif any(x in industry_lower for x in ["finance", "banking", "insurance"]):
                dynamics["barrier_to_entry"] = "High - regulatory requirements"
                dynamics["disruption_potential"] = "High - fintech disruption"
            else:
                dynamics["barrier_to_entry"] = "Medium - varies by specific sector"
                dynamics["disruption_potential"] = (
                    "Moderate - depends on technology adoption"
                )

            dynamics["pricing_trends"] = (
                "Competitive pricing pressure with value-based differentiation"
            )
            dynamics["customer_acquisition_cost_trend"] = (
                "Rising in digital markets; acquisition efficiency is becoming a moat"
            )
            return dynamics
        except Exception as e:
            logger.error(f"Error analyzing market dynamics: {e}")
            return {
                "supply_demand_balance": "Unable to analyze - data unavailable",
                "pricing_trends": "Unable to analyze - data unavailable",
                "market_maturity": "Unable to analyze - data unavailable",
                "disruption_potential": "Unable to analyze - data unavailable",
                "barrier_to_entry": "Unable to analyze - data unavailable",
                "customer_acquisition_cost_trend": (
                    "Unable to analyze - data unavailable"
                ),
            }


    def _get_competitive_landscape(self, industry):
        # Ported simplified version or full version if critical
        # For brevity, implementing the keyword based logic and simple SERP if key exists
        landscape = {
            "market_concentration": "Analyzing...",
            "differentiation_opportunities": [],
        }
        if self.serpapi_key:
            # Similar SERP logic...
            pass

        # Hardcoded fallback logic from blueprint
        if "tech" in industry.lower():
            landscape["differentiation_opportunities"] = ["AI/ML features", "UX"]
        else:
            landscape["differentiation_opportunities"] = [
                "Customer Experience",
                "Digital Transformation",
            ]

        return landscape

    def _get_emerging_trends(self, industry):
        # Simplified
        return ["AI Adoption", "Sustainability", "Digital Transformation"]

    def _analyze_regulatory_environment(self, industry):
        # Simplified logic
        ind = industry.lower()
        if "finance" in ind:
            return {"compliance": "Very High", "regulations": ["PCI DSS", "SOX"]}
        if "health" in ind:
            return {"compliance": "Very High", "regulations": ["HIPAA"]}
        return {"compliance": "Medium", "regulations": ["Standard Business Laws"]}

    def _get_investment_activity(self, industry):
        return {"total_funding": "Varies", "stage_focus": "Seed to Series A"}

    def _format_market_data(self, market_intelligence, validated_industry):
        # Helper to format string
        return f"""
        INDUSTRY: {validated_industry}
        GROWTH: {market_intelligence.get("growth_data", "N/A")}
        DYNAMICS: {market_intelligence.get("market_dynamics", {})}
        """

    def _construct_prompt(
        self, business_name, validated_industry, user_inputs, market_data
    ):
        return f"""
        Generate a World-Class GTM Strategy for:
        BUSINESS: {business_name}
        INDUSTRY: {validated_industry}
        INPUTS: {json.dumps(user_inputs, indent=2)}
        MARKET DATA: {market_data}

        Include sections: Executive Summary, Market Domination, Customer Acquisition, Revenue, Tactical Roadmap (Table), Growth Hacks, Metrics.
        Mark strictly as Markdown.
        """
    def _get_competitive_landscape(self, industry):
        try:
            landscape = {
                "market_concentration": "Analyzing...",
                "competitive_intensity": "Analyzing...",
                "differentiation_opportunities": [],
                "white_space_opportunities": [],
            }

            if self.serpapi_key:
                params = {
                    "engine": "google",
                    "q": f"{industry} market share leaders competition analysis 2024",
                    "api_key": self.serpapi_key,
                    "num": 10,
                }
                response = requests.get(  # nosec B113
                    "https://serpapi.com/search", params=params
                )
                if response.status_code == 200:
                    results = response.json()
                    snippets = [
                        r.get("snippet", "")
                        for r in results.get("organic_results", [])
                    ]
                    full_text = " ".join(snippets).lower()

                    if "fragmented" in full_text or "many players" in full_text:
                        landscape["market_concentration"] = (
                            "Fragmented - many competitors, no dominant player"
                        )
                    elif "dominated" in full_text or "leader" in full_text:
                        landscape["market_concentration"] = (
                            "Concentrated - few major players dominate"
                        )
                    else:
                        landscape["market_concentration"] = (
                            "Moderate concentration - mix of large and small players"
                        )

                    competition_keywords = [
                        "competitive",
                        "competition",
                        "rivalry",
                        "competing",
                    ]
                    intensity_count = sum(
                        1 for keyword in competition_keywords if keyword in full_text
                    )
                    landscape["competitive_intensity"] = (
                        "High - intense competition"
                        if intensity_count > 2
                        else "Moderate - healthy competition"
                    )

            if any(term in industry.lower() for term in ["tech", "software", "saas"]):
                landscape["differentiation_opportunities"] = [
                    "AI/ML-powered features",
                    "Superior user experience",
                    "Vertical specialization",
                    "API-first approach",
                    "No-code/low-code solutions",
                ]
                landscape["white_space_opportunities"] = [
                    "SMB segment automation",
                    "Industry-specific solutions",
                    "Emerging markets expansion",
                    "Integration platforms",
                ]
            elif any(term in industry.lower() for term in ["retail", "ecommerce"]):
                landscape["differentiation_opportunities"] = [
                    "Personalization engine",
                    "Omnichannel experience",
                    "Sustainable practices",
                    "Social commerce integration",
                    "Same-day delivery",
                ]
                landscape["white_space_opportunities"] = [
                    "Niche market segments",
                    "B2B marketplaces",
                    "Subscription models",
                    "AR/VR shopping",
                ]
            else:
                landscape["differentiation_opportunities"] = [
                    "Digital transformation",
                    "Customer experience focus",
                    "Data-driven insights",
                    "Sustainability initiatives",
                    "Partnership ecosystems",
                ]
                landscape["white_space_opportunities"] = [
                    "Underserved segments",
                    "Geographic expansion",
                    "Service innovation",
                    "Platform business models",
                ]

            return landscape
        except Exception as e:
            logger.error(f"Error getting competitive landscape: {e}")
            return {
                "market_concentration": "Unable to analyze",
                "competitive_intensity": "Unable to analyze",
                "differentiation_opportunities": ["Market analysis unavailable"],
                "white_space_opportunities": ["Market analysis unavailable"],
            }

    def _get_emerging_trends(self, industry):
        if any(term in industry.lower() for term in ["tech", "software"]):
            return [
                "AI/ML becoming standard in all products",
                "Shift to subscription and usage-based pricing",
                "Privacy-first architecture requirements",
                "Edge computing and distributed systems",
                "Developer experience as competitive advantage",
            ]
        if any(term in industry.lower() for term in ["retail", "ecommerce"]):
            return [
                "Social commerce integration",
                "Sustainable and ethical sourcing",
                "Hyper-personalization through AI",
                "Live shopping and video commerce",
                "Blockchain for supply chain transparency",
            ]
        return [
            "Digital transformation acceleration",
            "Remote/hybrid work normalization",
            "ESG focus increasing",
            "Data privacy and security prioritization",
            "Platform economy expansion",
        ]

    def _analyze_regulatory_environment(self, industry):
        industry_lower = industry.lower()
        if any(term in industry_lower for term in ["finance", "banking", "fintech", "payment"]):
            return {
                "key_regulations": ["PCI DSS", "SOX", "BASEL III", "PSD2", "AML/KYC"],
                "compliance_complexity": "Very High",
                "regulatory_trends": "Increasing scrutiny on digital finance and crypto",
                "geographic_considerations": "Highly regulated globally, especially in US/EU",
            }
        if any(term in industry_lower for term in ["health", "medical", "pharma", "biotech"]):
            return {
                "key_regulations": ["HIPAA", "FDA", "GDPR (health data)", "MDR", "Clinical Trials"],
                "compliance_complexity": "Very High",
                "regulatory_trends": "Digital health regulations evolving rapidly",
                "geographic_considerations": "Strict regulations in all major markets",
            }
        if any(term in industry_lower for term in ["data", "software", "tech", "saas"]):
            return {
                "key_regulations": ["GDPR", "CCPA", "SOC2", "ISO 27001", "COPPA"],
                "compliance_complexity": "High",
                "regulatory_trends": "Privacy laws expanding globally",
                "geographic_considerations": "EU strictest, US state-by-state variation",
            }
        return {
            "key_regulations": ["GDPR", "Industry Standards", "Local Business Laws", "Tax Compliance"],
            "compliance_complexity": "Medium",
            "regulatory_trends": "Increasing requirements",
            "geographic_considerations": "Varies by region",
        }

    def _get_investment_activity(self, industry):
        industry_lower = industry.lower()
        if any(term in industry_lower for term in ["ai", "ml", "artificial intelligence"]):
            return {
                "total_funding_last_year": "$50B+ globally in AI/ML startups",
                "average_deal_size": "$15-25M for Series A",
                "funding_stage_focus": "Series A and B (growth stage)",
                "top_investors": ["Sequoia", "a16z", "Google Ventures", "Microsoft Ventures"],
                "exit_activity": "High M&A activity, several unicorns",
            }
        if any(term in industry_lower for term in ["fintech", "finance", "payment"]):
            return {
                "total_funding_last_year": "$30B+ in fintech globally",
                "average_deal_size": "$20-30M for Series A",
                "funding_stage_focus": "All stages active",
                "top_investors": ["Ribbit Capital", "Accel", "Index Ventures", "QED"],
                "exit_activity": "Strong IPO and acquisition pipeline",
            }
        if any(term in industry_lower for term in ["saas", "software"]):
            return {
                "total_funding_last_year": "$40B+ in B2B SaaS",
                "average_deal_size": "$10-20M for Series A",
                "funding_stage_focus": "Series A through C",
                "top_investors": ["Bessemer", "Insight Partners", "Tiger Global", "Sequoia"],
                "exit_activity": "Active M&A market, strategic acquisitions",
            }
        return {
            "total_funding_last_year": "Varies by specific sector",
            "average_deal_size": "$5-15M for Series A",
            "funding_stage_focus": "Seed and Series A",
            "top_investors": ["General Catalyst", "NEA", "Kleiner Perkins", "Founders Fund"],
            "exit_activity": "Moderate M&A activity",
        }

    def _format_market_data(self, market_intelligence, validated_industry):
        return f"""
        VALIDATED INDUSTRY: {validated_industry}

        GROWTH DATA:
        {market_intelligence.get("growth_data", "N/A")}

        MARKET DYNAMICS:
        - Supply/Demand: {market_intelligence.get("market_dynamics", {}).get("supply_demand_balance", "N/A")}
        - Pricing Trends: {market_intelligence.get("market_dynamics", {}).get("pricing_trends", "N/A")}
        - Market Maturity: {market_intelligence.get("market_dynamics", {}).get("market_maturity", "N/A")}
        - Disruption Potential: {market_intelligence.get("market_dynamics", {}).get("disruption_potential", "N/A")}
        - Barriers to Entry: {market_intelligence.get("market_dynamics", {}).get("barrier_to_entry", "N/A")}
        - CAC Trend: {market_intelligence.get("market_dynamics", {}).get("customer_acquisition_cost_trend", "N/A")}

        COMPETITIVE LANDSCAPE:
        - Market Concentration: {market_intelligence.get("competitive_landscape", {}).get("market_concentration", "N/A")}
        - Competitive Intensity: {market_intelligence.get("competitive_landscape", {}).get("competitive_intensity", "N/A")}
        - Differentiation Opportunities: {", ".join(market_intelligence.get("competitive_landscape", {}).get("differentiation_opportunities", []))}
        - White Space Opportunities: {", ".join(market_intelligence.get("competitive_landscape", {}).get("white_space_opportunities", []))}

        EMERGING TRENDS:
        {"; ".join(market_intelligence.get("emerging_trends", []))}

        REGULATORY ENVIRONMENT:
        - Key Regulations: {", ".join(market_intelligence.get("regulatory_environment", {}).get("key_regulations", []))}
        - Compliance Complexity: {market_intelligence.get("regulatory_environment", {}).get("compliance_complexity", "N/A")}
        - Regulatory Trends: {market_intelligence.get("regulatory_environment", {}).get("regulatory_trends", "N/A")}

        INVESTMENT ACTIVITY:
        - Total Funding: {market_intelligence.get("investment_activity", {}).get("total_funding_last_year", "N/A")}
        - Average Deal Size: {market_intelligence.get("investment_activity", {}).get("average_deal_size", "N/A")}
        - Funding Focus: {market_intelligence.get("investment_activity", {}).get("funding_stage_focus", "N/A")}
        - Exit Activity: {market_intelligence.get("investment_activity", {}).get("exit_activity", "N/A")}
        """

    def _generate_ai_plan(self, prompt):
    def _construct_prompt(
        self, business_name, validated_industry, user_inputs, market_data
    ):
        risk_scale = user_inputs["Section 4: Risk Appetite â€” Aggression Meter"].get(
            "Scale of 1-10 (1 = Safe, 10 = Extreme):",
            "5",
        )
        return f"""
        You are a legendary GTM strategist who has scaled 50+ unicorns and led multiple successful IPOs.
        Your GTM plans are known for aggressive tactics, data-driven thinking, and immediate actionability.
        Think like a military strategist planning a market conquest combined with a Silicon Valley growth hacker.

        Generate a WORLD-CLASS, PROFESSIONAL Go-To-Market strategy for:

        BUSINESS: {business_name}
        VALIDATED INDUSTRY: {validated_industry}

        CLIENT INPUTS:
        {json.dumps(user_inputs, indent=2)}

        REAL-TIME MARKET INTELLIGENCE:
        {market_data}

        Create these sections:
        1. Executive Summary & Strategic Thesis
        2. Market Domination Strategy
        3. Customer Acquisition Warfare
        4. Revenue Acceleration Engine
        5. Tactical Execution Roadmap
        6. Growth Hacking Playbook
        7. Competitive Warfare Tactics
        8. Metrics & KPI Dashboard
        9. Resource Allocation & Team Building
        10. Risk Mitigation & Scenario Planning
        11. Fundraising & Exit Strategy
        12. 100-Day Battle Plan
        13. Technology & Automation Stack
        14. Psychological Warfare & Brand Strategy
        15. Global Expansion Playbook

        REQUIREMENTS:
        - Use rich markdown formatting.
        - Include a detailed execution matrix in markdown table format with phases, timelines, activities, owners, budget allocation, metrics, risks, and mitigations.
        - Include specific numbers, percentages, timelines, and measurable KPIs.
        - Make every recommendation concrete and immediately actionable.
        - Calibrate aggressiveness to a risk tolerance of {risk_scale}/10.
        - If a launch location is provided, tailor market entry and regulatory recommendations to that geography.
        """

    def _generate_ai_plan(self, prompt):
        if not self.ai_client or not self.deployment:
        try:
            response = self.ai_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert GTM strategist."},
                    {"role": "user", "content": prompt},
                ],
            response = self.ai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the world's best GTM strategist. "
                            "You create aggressive, data-driven, highly actionable market domination plans. "
                            "Every recommendation must be specific, measurable, and time-bound."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
Edited file
gtm_service.py
+257
-50


    def _generate_strategic_nodes(self, plan, name, industry, inputs):
        # Logic to extract nodes from plan (simplified for now as exact extraction is complex text parsing)
        # Blueprint had hardcoded structure logic.
        return [
            {
                "id": "strategy",
                "type": "strategy",
                "title": "Core Strategy",
                "description": f"Dominate {industry}",
            },
            {
                "id": "market",
                "type": "launch",
                "title": "Market Entry",
                "description": "Initial rollout",
            },
        ]

    def _generate_node_connections(self, nodes):
        return [{"source": "strategy", "target": "market", "id": "conn1"}]

    def _generate_pdf_report(self, plan, business_name, user_id):
        try:
            upload_dir = os.path.join(os.getcwd(), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"{user_id}_gtm_plan_{int(time.time())}.pdf"
            filepath = os.path.join(upload_dir, filename)

            doc = SimpleDocTemplate(
                filepath, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch
            )
            story = []
            styles = getSampleStyleSheet()

            story.append(Paragraph(f"GTM PLAN: {business_name}", styles["Title"]))
            story.append(Spacer(1, 12))

            # Simple markdown parser
            for line in plan.split("\n"):
                if line.strip():
                    # clean markdown
                    text = line.replace("*", "").replace("#", "")
                    story.append(Paragraph(text, styles["Normal"]))
                    story.append(Spacer(1, 6))

            doc.build(story)
            return {"success": True, "pdf_path": filepath, "pdf_filename": filename}
        except Exception as e:
            logger.error(f"PDF Error: {e}")
            return {"success": False, "error": str(e)}
    def _generate_strategic_nodes(self, plan, name, industry, inputs):
        _ = plan
        try:
            return [
                {
                    "id": "core-strategy",
                    "type": "strategy",
                    "title": f"{name} Core Strategy",
                    "description": (
                        f"Dominate {industry} through "
                        f"{inputs['Section 1: Battlefield Entry â€” Strategic Positioning']['GTM Mode Preference (Guerrilla Warfare, Blitzkrieg, Stealth Mode, Community-Led):']}"
                    ),
                    "metrics": [
                        {"label": "TAM", "value": "$2.5B"},
                        {"label": "Target Share", "value": "15%"},
                        {"label": "Timeline", "value": "18 months"},
                    ],
                },
                {
                    "id": "market-entry",
                    "type": "launch",
                    "title": "Market Entry Strategy",
                    "description": "Phased rollout targeting early adopters and strategic accounts",
                    "metrics": [
                        {"label": "Phase 1", "value": "3 months"},
                        {"label": "Initial Targets", "value": "100 accounts"},
                        {"label": "Success Metric", "value": "25% activation"},
                    ],
                },
                {
                    "id": "customer-acquisition",
                    "type": "growth",
                    "title": "Customer Acquisition Engine",
                    "description": (
                        "Multi-channel approach targeting "
                        f"{inputs['Section 1: Battlefield Entry â€” Strategic Positioning']['Who are you hunting?']}"
                    ),
                    "metrics": [
                        {"label": "CAC Target", "value": "$150"},
                        {"label": "Channels", "value": "5 primary"},
                        {"label": "Conv Rate", "value": "15%"},
                    ],
                },
                {
                    "id": "revenue-growth",
                    "type": "revenue",
                    "title": "Revenue Acceleration",
                    "description": "Scale from $0 to $10M ARR through land-and-expand strategy",
                    "metrics": [
                        {"label": "Month 6", "value": "$1M ARR"},
                        {"label": "Month 12", "value": "$5M ARR"},
                        {"label": "Month 18", "value": "$10M ARR"},
                    ],
                },
                {
                    "id": "competitive-advantage",
                    "type": "moat",
                    "title": "Competitive Moat",
                    "description": (
                        "Leverage "
                        f"{inputs['Section 2: Founder DNA â€” Weapons Inventory']['Unfair Advantage:']}"
                        " for sustainable advantage"
                    ),
                    "metrics": [
                        {"label": "NPS Target", "value": "70+"},
                        {"label": "Retention", "value": "95%"},
                        {"label": "LTV:CAC", "value": "5:1"},
                    ],
                },
                {
                    "id": "scale-operations",
                    "type": "scale",
                    "title": "Scale Infrastructure",
                    "description": "Build systems and team for 10x growth",
                    "metrics": [
                        {"label": "Team Size", "value": "50+"},
                        {"label": "Automation", "value": "80%"},
                        {"label": "Efficiency", "value": "2x"},
                    ],
                },
            ]
        except Exception as e:
            logger.error(f"Error generating strategic nodes: {e}")
            return []

    def _generate_node_connections(self, nodes):
        _ = nodes
        try:
            flow_map = {
                "core-strategy": ["market-entry", "competitive-advantage"],
                "market-entry": ["customer-acquisition"],
                "customer-acquisition": ["revenue-growth"],
                "revenue-growth": ["scale-operations"],
                "competitive-advantage": ["revenue-growth", "scale-operations"],
            }
            connections = []
            for source, targets in flow_map.items():
                for target in targets:
                    connections.append(
                        {
                            "id": f"{source}-{target}",
                            "source": source,
                            "target": target,
                            "type": "strategic",
                            "animated": True,
                        }
                    )
            return connections
        except Exception as e:
            logger.error(f"Error generating node connections: {e}")
            return []

    def _generate_pdf_report(self, plan, business_name, user_id):
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            upload_dir = os.path.join(base_dir, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            filename = (
                f"{user_id}_gtm_battle_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            filepath = os.path.join(upload_dir, filename)

            doc = SimpleDocTemplate(
                filepath, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch
            )
            story = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2c3e50"),
            )
            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading1"],
                fontSize=16,
                spaceAfter=12,
                spaceBefore=20,
                textColor=colors.HexColor("#34495e"),
            )
            subheading_style = ParagraphStyle(
                "CustomSubHeading",
                parent=styles["Heading2"],
                fontSize=14,
                spaceAfter=10,
                spaceBefore=15,
                textColor=colors.HexColor("#5d6d7e"),
            )
            normal_style = ParagraphStyle(
                "CustomNormal",
                parent=styles["Normal"],
                fontSize=10,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
            )

            story.append(Paragraph("GTM STRATEGY PLAYBOOK", title_style))
            story.append(Paragraph(f"<b>{business_name}</b>", heading_style))
            story.append(
                Paragraph(
                    f"Generated on: {datetime.now().strftime('%B %d, %Y')}",
                    normal_style,
                )
            )
            story.append(Spacer(1, 20))

            for section in plan.split("\n\n"):
                stripped = section.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    heading_level = len(stripped) - len(stripped.lstrip("#"))
                    heading_text = stripped.lstrip("#").strip()
                    if heading_level == 1:
                        story.append(Paragraph(heading_text, heading_style))
                    elif heading_level == 2:
                        story.append(Paragraph(heading_text, subheading_style))
                    else:
                        story.append(Paragraph(f"<b>{heading_text}</b>", normal_style))
                elif stripped.startswith("|"):
                    table_data = self._parse_markdown_table(stripped)
                    if table_data:
                        table = Table(table_data, hAlign="LEFT")
                        table.setStyle(
                            TableStyle(
                                [
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ]
                            )
                        )
                        story.append(table)
                        story.append(Spacer(1, 12))
                else:
                    for line in stripped.split("\n"):
                        clean_line = line.strip()
                        if not clean_line:
                            continue
                        if clean_line.startswith("-") or clean_line.startswith("*"):
                            bullet_text = clean_line.lstrip("-*").strip()
                            story.append(Paragraph(f"• {bullet_text}", normal_style))
                        else:
                            story.append(
                                Paragraph(self._clean_markdown(clean_line), normal_style)
                            )
                    story.append(Spacer(1, 6))

            doc.build(story)
            return {"success": True, "pdf_path": filepath, "pdf_filename": filename}
        except Exception as e:
            logger.error(f"PDF Error: {e}")
            return {"success": False, "error": str(e)}

    def _parse_markdown_table(self, table_text):
        try:
            lines = table_text.strip().split("\n")
            table_data = []
            for line in lines:
                if "|" not in line:
                    continue
                if re.match(r"^[\s\|\-:]+$", line):
                    continue
                cells = [cell.strip() for cell in line.split("|")]
                if cells and cells[0] == "":
                    cells = cells[1:]
                if cells and cells[-1] == "":
                    cells = cells[:-1]
                if cells:
                    table_data.append(cells)
            return table_data if table_data else None
        except Exception as e:
            logger.error(f"Error parsing markdown table: {e}")
            return None

    def _clean_markdown(self, text):
        text = re.sub(r"<br\s*/?>", "<br/>", text, flags=re.IGNORECASE)
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"#{1,6}\s*", "", text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        text = text.replace("&lt;br/&gt;", "<br/>")
        return text

Context automatically compacted
I’m continuing with the GTM parity pass now, starting from the remaining route/schema/Celery gaps so the FastAPI flow matches the Flask behavior and the frontend contract more reliably.

Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\celery_tasks\celery_tasks.py' for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py' for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\schemas\gtm.py' for 1s


I’ve confirmed the GTM route/schema/Celery pieces still had the exact gaps we identified, so I’m patching those next rather than guessing around them.

Ran rg -n "def _generate_pdf_report|async def _store_plan|def generate_plan|active_generations|pdf_filename|pdf_path" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\services\gtm_service.py' for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\services\gtm_service.py' -TotalCount 260 for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' -TotalCount 400 for 2s


I’ve got the GTM service context in hand now. Next I’m wiring the route layer to expose the richer GTM payload, regenerate missing PDFs like Flask, and persist task progress in Redis so status checks still work once Celery is involved.

Ran rg -n "download_gtm_pdf|generation_status|generate_gtm_plan|Target Launch Location/Country|gtm_plan_result" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' for 1s


Ran rg -n "Target Launch Location/Country|applyGtmResult|generation_status|gtm_plan_result|download_gtm_pdf|visualization_available|industry_growth_data" 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\pages\GTMStrategy.tsx' 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\components\business\ShowGTM.tsx'


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' | Select-Object -Skip 2260 -First 60 for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' | Select-Object -Skip 1800 -First 120 for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' | Select-Object -Skip 2288 -First 40


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' | Select-Object -Skip 2328 -First 30 for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' | Select-Object -Skip 2358 -First 20 for 1s


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\db\redis.py' for 1s


Ran rg -n "scan_iter\(|keys\(" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app'


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\pitch_analysis_routes.py' -TotalCount 120


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\deps.py' -TotalCount 200


Ran rg -n "InvalidId|ObjectId\(plan_id\)|find_one\(\{" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes'


Ran Get-Content -Path 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\business_routes.py' | Select-Object -Skip 836 -First 40


Ran rg -n "generation_status|active_generations|active_tasks" 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src'


I’ve narrowed the remaining GTM work to three concrete fixes: route parity, schema parity, and Redis-backed progress persistence for Celery. After that I’ll run compile and targeted smoke checks instead of assuming the changes are safe.

Patch gtm_routes.py for Flask-style download fallback, richer result payloads, and Redis-backed generation status.
Patch gtm.py so the GTM response model matches the newer payload fields the frontend already reads.
Patch celery_tasks.py so GTM progress is stored in Redis as well as emitted over websockets, then verify with backend smoke tests.
I’m editing the GTM backend files now. The changes are focused and compatibility-safe: they keep the existing FastAPI routes, but make the response shape, PDF behavior, and status tracking act much closer to the Flask version.

The GTM route patch hit one of the encoding-heavy sections in this repo, so I’m switching to smaller, line-targeted edits to avoid trampling the form aliases.

Ran $i=1; Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py' | ForEach-Object { '{0,4}: {1}' -f $i, $_; $i++ } | Select-Object -First 140 for 1s


Ran $i=141; Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py' | Select-Object -Skip 140 | ForEach-Object { '{0,4}: {1}' -f $i, $_; $i++ } | Select-Object -First 220 for 1s


Edited file
gtm_routes.py
+43
-2

from fastapi.responses import FileResponse
from bson.errors import InvalidId
import logging
import os
import json
from datetime import datetime

from app.db.mongo import get_collection
from app.db.redis import redis_client
from bson import ObjectId

router = APIRouter()
logger = logging.getLogger(__name__)
router = APIRouter()
logger = logging.getLogger(__name__)


def _build_plan_query(plan_id: str, user_id: str) -> dict:
    query = {"user_id": user_id}
    try:
        query["_id"] = ObjectId(plan_id)
    except (InvalidId, TypeError):
        query["_id"] = plan_id
    return query


def _serialize_generation_payload(task_id: str, payload: dict) -> tuple[str, dict]:
    details = payload.get("details") or {}
    timestamp_iso = None
    timestamp = payload.get("timestamp")
    if timestamp:
        try:
            timestamp_iso = datetime.fromtimestamp(float(timestamp)).isoformat()
        except Exception:
            timestamp_iso = None

    generation_id = (
        payload.get("generation_id")
        or details.get("generation_id")
        or payload.get("task_id")
        or task_id
    )

    return generation_id, {
        "user_id": payload.get("user_id"),
        "status": payload.get("status", "processing"),
        "progress": payload.get("progress", 0),
        "details": details,
        "task_id": payload.get("task_id", task_id),
        "created_at": timestamp_iso,
        "updated_at": timestamp_iso,
    }

Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 49..61 | ForEach-Object { '>' + $lines[$_] + '<' }


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 85..105 | ForEach-Object { '{0,4}: >{1}<' -f ($_+1), $lines[$_] }


Edited file
gtm_routes.py
+4
-0

    per_page: int = Query(default=10, ge=1, le=100),
    target_launch_location: str = Form(
        default="",
        alias="Target Launch Location/Country:",
    ),
    current_user: str = Depends(get_current_user),
Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 111..130 | ForEach-Object { '{0,4}: >{1}<' -f ($_+1), $lines[$_] } for 1s


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 130..148 | ForEach-Object { '{0,4}: >{1}<' -f ($_+1), $lines[$_] }


Edited file
gtm_routes.py
+2
-1

        "Section 5: Long-Term Vision — Empire Blueprint": {
            "Category Design Intent (Yes/No):": category_design_intent,
            "Target Launch Location/Country:": target_launch_location,
            "Category Design Intent (Yes/No):": category_design_intent,
            "Exit Intent (Acquisition/IPO/Lifestyle Business/Industry Consolidation):": exit_intent,
Edited file
gtm_routes.py
+22
-15

            plan_result = task_result.get("result", {})
            return {
                "success": True,
                "message": "GTM plan generated successfully",
                "plan_id": plan_result.get("plan_id"),
                "gtm_plan": plan_result.get("gtm_plan"),
                "business_name": plan_result.get("business_name"),
                "industry": plan_result.get("industry"),
                "original_industry": plan_result.get("original_industry"),
                "market_intelligence": plan_result.get("market_intelligence"),
                "strategic_nodes": plan_result.get("strategic_nodes"),
                "node_connections": plan_result.get("node_connections"),
                "pdf_filename": plan_result.get("pdf_filename"),
                "pdf_available": True if plan_result.get("pdf_filename") else False,
                "generation_id": plan_result.get("generation_id"),
            }
            return {
                "success": True,
                "message": "GTM plan generated successfully",
                "plan_id": plan_result.get("plan_id"),
                "gtm_plan": plan_result.get("gtm_plan"),
                "business_name": plan_result.get("business_name"),
                "industry": plan_result.get("industry"),
                "original_industry": plan_result.get("original_industry"),
                "market_intelligence": plan_result.get("market_intelligence"),
                "industry_growth_data": plan_result.get("industry_growth_data"),
                "strategic_nodes": plan_result.get("strategic_nodes"),
                "node_connections": plan_result.get("node_connections"),
                "visualization_type": plan_result.get("visualization_type"),
                "visualization_available": plan_result.get(
                    "visualization_available"
                ),
                "pdf_filename": plan_result.get("pdf_filename"),
                "pdf_available": bool(
                    plan_result.get("pdf_filename") or plan_result.get("pdf_path")
                ),
                "generation_id": plan_result.get("generation_id"),
            }
        else:
Edited file
gtm_routes.py
+40
-18

    current_user: str = Depends(get_current_user),
    _: bool = Depends(service_required("610")),
):
    try:
        coll = get_collection("gtm_plans")
        plan = await coll.find_one({"_id": ObjectId(plan_id), "user_id": current_user})

        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        pdf_path = plan.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found on server")

        return FileResponse(
            path=pdf_path,
            filename=plan.get("pdf_filename", "gtm_plan.pdf"),
            media_type="application/pdf",
        )
    _: bool = Depends(service_required("610")),
):
    try:
        coll = get_collection("gtm_plans")
        plan = await coll.find_one(_build_plan_query(plan_id, current_user))

        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        pdf_path = plan.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            pdf_result = gtm_service._generate_pdf_report(
                plan.get("gtm_plan", ""),
                plan.get("business_name", "gtm_plan"),
                current_user,
            )
            if not pdf_result.get("success"):
                raise HTTPException(status_code=500, detail="Failed to generate PDF")

            pdf_path = pdf_result.get("pdf_path")
            if not pdf_path or not os.path.exists(pdf_path):
                raise HTTPException(status_code=500, detail="Failed to generate PDF")

            await coll.update_one(
                {"_id": plan["_id"]},
                {
                    "$set": {
                        "pdf_path": pdf_path,
                        "pdf_filename": pdf_result.get("pdf_filename", ""),
                    }
                },
            )
            plan["pdf_path"] = pdf_path
            plan["pdf_filename"] = pdf_result.get("pdf_filename", "")

        return FileResponse(
            path=pdf_path,
            filename=f"{plan.get('business_name', 'gtm_plan')}_GTM_Strategy.pdf",
            media_type="application/pdf",
        )

Edited file
gtm_routes.py
+3
-1

                    "created_at": plan.get("created_at"),
                    "pdf_available": bool(plan.get("pdf_path")),
                    "pdf_available": bool(
                        plan.get("pdf_path") or plan.get("pdf_filename")
                    ),
                }
Edited file
gtm_routes.py
+3
-3

        coll = get_collection("gtm_plans")
        plan = await coll.find_one({"_id": ObjectId(plan_id), "user_id": current_user})
        plan = await coll.find_one(_build_plan_query(plan_id, current_user))
        if not plan:
        coll = get_collection("gtm_plans")
        plan = await coll.find_one({"_id": ObjectId(plan_id), "user_id": current_user})
        plan = await coll.find_one(_build_plan_query(plan_id, current_user))
        if not plan:

        await coll.delete_one({"_id": ObjectId(plan_id)})
        await coll.delete_one({"_id": plan["_id"]})
        return {
Edited file
gtm_routes.py
+36
-6

    try:
        user_generations = {
            generation_id: generation_data
            for generation_id, generation_data in gtm_service.active_generations.items()
            if generation_data.get("user_id") == user_id
        }
        active_tasks = []
        user_generations = {}

        try:
            for key in redis_client.scan_iter(match=f"gtm:{user_id}:*:progress"):
                raw = redis_client.get(key)
                if not raw:
                    continue

                payload = json.loads(raw)
                task_id = payload.get("task_id") or str(key).split(":")[-2]
                generation_id, generation_data = _serialize_generation_payload(
                    task_id, payload
                )
                user_generations[generation_id] = generation_data

                if generation_data["progress"] < 100 and generation_data["status"] not in {
                    "completed",
                    "error",
                    "failed",
                    "cancelled",
                }:
                    active_tasks.append(generation_data["task_id"])
        except Exception as redis_error:
            logger.warning(
                f"Falling back to in-memory GTM generation status for {user_id}: {redis_error}"
            )

        if not user_generations:
            user_generations = {
                generation_id: generation_data
                for generation_id, generation_data in gtm_service.active_generations.items()
                if generation_data.get("user_id") == user_id
            }

        return {
            "active_tasks": [],
            "active_tasks": active_tasks,
            "active_generations": user_generations,
Edited file
gtm.py
+11
-8

    business_name: Optional[str] = None
    industry: Optional[str] = None
    original_industry: Optional[str] = None
    market_intelligence: Optional[Dict[str, Any]] = None
    strategic_nodes: Optional[List[Dict[str, Any]]] = None
    node_connections: Optional[List[Dict[str, Any]]] = None
    pdf_available: Optional[bool] = None
    pdf_filename: Optional[str] = None
    generation_id: Optional[str] = None
    industry: Optional[str] = None
    original_industry: Optional[str] = None
    market_intelligence: Optional[Dict[str, Any]] = None
    industry_growth_data: Optional[str] = None
    strategic_nodes: Optional[List[Dict[str, Any]]] = None
    node_connections: Optional[List[Dict[str, Any]]] = None
    visualization_type: Optional[str] = None
    visualization_available: Optional[bool] = None
    pdf_available: Optional[bool] = None
    pdf_filename: Optional[str] = None
    generation_id: Optional[str] = None
Edited file
celery_tasks.py
+6
-5

        payload = {"task_id": self.request.id, **(data or {})}
        store_progress("gtm", user_id, self.request.id, progress, message, payload)
        manager.emit(user_id, progress, message, payload, progress_type="gtm")

        try:
            result = gtm_service.generate_plan(
                user_id, user_inputs, loop, progress_callback
            )
            return {"success": True, "result": result}
        try:
            result = gtm_service.generate_plan(
                user_id, user_inputs, loop, progress_callback
            )
            return {"success": True, "user_id": user_id, "result": result}

Edited file
celery_tasks.py
+25
-9


    except SoftTimeLimitExceeded:
        logger.error(f"GTM generation timed out for user {user_id}")
        raise

    except Exception as e:
        logger.error(f"GTM generation failed for user {user_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        raise
    except SoftTimeLimitExceeded:
        logger.error(f"GTM generation timed out for user {user_id}")
        store_progress(
            "gtm",
            user_id,
            self.request.id,
            100,
            "GTM generation timed out",
            {"task_id": self.request.id, "status": "error"},
        )
        raise

    except Exception as e:
        logger.error(f"GTM generation failed for user {user_id}: {e}")
        store_progress(
            "gtm",
            user_id,
            self.request.id,
            100,
            f"GTM generation failed: {str(e)}",
            {"task_id": self.request.id, "status": "error"},
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        raise

Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\services\gtm_service.py'; 60..95 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] }


I’m making one more small GTM change in the service layer so the generation IDs flow cleanly through websocket and Redis progress updates. That keeps the status view stable even when work is running in Celery workers.

Edited file
gtm_service.py
+1
-0

                payload = dict(d or {})
                payload.setdefault("generation_id", generation_id)
                if status:
Edited file
gtm_routes.py
+14
-9

            raise HTTPException(status_code=500, detail=f"Task failed: {result.info}")
        elif result.state == "SUCCESS":
            task_result = result.result
            if not task_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=task_result.get("error", "GTM generation failed"),
                )

            plan_result = task_result.get("result", {})
        elif result.state == "SUCCESS":
            task_result = result.result
            if not task_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=task_result.get("error", "GTM generation failed"),
                )
            if task_result.get("user_id") and task_result.get("user_id") != current_user:
                raise HTTPException(
                    status_code=403,
                    detail="Task does not belong to the current user",
                )

            plan_result = task_result.get("result", {})
            return {
Edited file
gtm_routes.py
+1
-0

            }
            active_tasks = list(user_generations.keys())

Ran $i=1; Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py' | ForEach-Object { '{0,4}: {1}' -f $i, $_; $i++ } | Select-Object -First 220 for 3s


Ran .\venv\Scripts\python.exe -m compileall 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app' for 2s


Ran rg -n "target_launch_location" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 288..306 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] }


I caught a misplaced form parameter while checking the patched file. I’m cleaning that up before running route-level tests so we don’t carry a subtle GTM bug forward.

Edited file
gtm_routes.py
+0
-4

    per_page: int = Query(default=10, ge=1, le=100),
    target_launch_location: str = Form(
        default="",
        alias="Target Launch Location/Country:",
    ),
    current_user: str = Depends(get_current_user),
Edited file
gtm_routes.py
+6
-2

        ...,
        alias="Global Domination or Local Niche King? (Global Scale Brand/Hyperlocal Authority/Regional Powerhouse):",
    ),
        alias="Global Domination or Local Niche King? (Global Scale Brand/Hyperlocal Authority/Regional Powerhouse):",
    ),
    target_launch_location: str = Form(
        default="",
        alias="Target Launch Location/Country:",
    ),
    # ── Auth / Service deps ───────────────────────────────────────────────────
Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 90..105 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] }


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 186..340 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] }


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 340..400 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] } for 1s


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py'; 400..450 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] }


I’ve finished the code changes. I’m on the verification step now, and I’m checking them with direct GTM route smoke tests instead of relying on compile-only checks.

Ran rg -n "Competitor 1|Target Launch Location/Country|Global Domination or Local Niche King|GTM Mode Preference" 'D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming\src\pages\GTMStrategy.tsx'


Ran rg -n "Target Launch Location/Country|Global Domination or Local Niche King|Competitor 1" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\server2\blueprints\gtm_bp.py' for 1s


Ran @' import json import os import tempfile from copy import deepcopy from types import SimpleNamespace from unittest.mock import patch from bson import ObjectId from fastapi import FastAPI from fastapi.testclient import TestClient import app.api.deps as deps_module from app.api.deps import get_current_user from app.api.routes import gtm_routes import app.celery_tasks.celery_tasks as celery_tasks_module class FakeCursor: def __init__(self, items): self.items = items def sort(self, *args, **kwargs): return self def skip(self, count): self.items = self.items[count:] return self def limit(self, count): self.items = self.items[:count] return self def __aiter__(self): self._iter = iter(self.items) return self async def __anext__(self): try: return next(self._iter) except StopIteration: raise StopAsyncIteration class FakeCollection: def __init__(self, docs): self.docs = docs self.updated = [] self.deleted = [] @staticmethod def _matches(doc, query): for key, value in query.items(): if doc.get(key) != value: return False return True async def find_one(self, query): for doc in self.docs: if self._matches(doc, query): return deepcopy(doc) return None async def count_documents(self, query): return sum(1 for doc in self.docs if self._matches(doc, query)) def find(self, query): return FakeCursor([deepcopy(doc) for doc in self.docs if self._matches(doc, query)]) async def update_one(self, query, update): self.updated.append((deepcopy(query), deepcopy(update))) for doc in self.docs: if self._matches(doc, query): doc.update(update.get('$set', {})) return SimpleNamespace(modified_count=1) return SimpleNamespace(modified_count=0) async def delete_one(self, query): self.deleted.append(deepcopy(query)) before = len(self.docs) self.docs = [doc for doc in self.docs if not self._matches(doc, query)] return SimpleNamespace(deleted_count=before - len(self.docs)) class FakeRedis: def __init__(self, payloads): self.payloads = payloads def scan_iter(self, match=None): return list(self.payloads.keys()) def get(self, key): return self.payloads.get(key) async def fake_user(): return 'user-1' async def fake_check_service_access(service_id, user_id): return True app = FastAPI() app.include_router(gtm_routes.router) app.dependency_overrides[get_current_user] = fake_user with tempfile.TemporaryDirectory() as tmpdir: existing_pdf_path = os.path.join(tmpdir, 'existing.pdf') with open(existing_pdf_path, 'wb') as fh: fh.write(b'%PDF-1.4 existing') regenerated_pdf_path = os.path.join(tmpdir, 'regenerated.pdf') with open(regenerated_pdf_path, 'wb') as fh: fh.write(b'%PDF-1.4 regenerated') plan_id = ObjectId() delete_plan_id = ObjectId() collection = FakeCollection([ { '_id': plan_id, 'user_id': 'user-1', 'business_name': 'Acme', 'industry': 'AI', 'gtm_plan': '# GTM Plan', 'pdf_path': '', 'pdf_filename': '', 'created_at': '2026-03-23T10:00:00', }, { '_id': ObjectId(), 'user_id': 'user-1', 'business_name': 'Beta', 'industry': 'SaaS', 'gtm_plan': '# Beta Plan', 'pdf_path': '', 'pdf_filename': 'beta_saved.pdf', 'created_at': '2026-03-23T09:00:00', }, { '_id': delete_plan_id, 'user_id': 'user-1', 'business_name': 'DeleteCo', 'industry': 'Fintech', 'gtm_plan': '# Delete Plan', 'pdf_path': existing_pdf_path, 'pdf_filename': 'deleteco.pdf', 'created_at': '2026-03-23T08:00:00', }, ]) def fake_get_collection(name): assert name == 'gtm_plans' return collection captured_delay = {} def fake_delay(*, user_id, user_inputs): captured_delay['user_id'] = user_id captured_delay['user_inputs'] = user_inputs return SimpleNamespace(id='task-123') class FakeAsyncResult: def __init__(self, task_id, app=None): self.state = 'SUCCESS' self.info = None self.result = { 'success': True, 'user_id': 'user-1', 'result': { 'plan_id': str(plan_id), 'gtm_plan': '# Final GTM Plan', 'business_name': 'Acme', 'industry': 'AI', 'original_industry': 'AI tools', 'market_intelligence': {'validated_industry': 'AI'}, 'industry_growth_data': '25% CAGR', 'strategic_nodes': [{'id': 'core-strategy'}], 'node_connections': [{'source': 'core-strategy', 'target': 'market-entry'}], 'visualization_type': 'strategic_flow', 'visualization_available': True, 'pdf_filename': 'acme_saved.pdf', 'generation_id': 'gen-123', }, } fake_redis = FakeRedis({ 'gtm:user-1:task-123:progress': json.dumps({ 'progress': 65, 'status': 'ai_generation', 'details': {'phase': 'generation'}, 'user_id': 'user-1', 'task_id': 'task-123', 'generation_id': 'gen-123', 'timestamp': 1711180000, }), 'gtm:user-1:task-done:progress': json.dumps({ 'progress': 100, 'status': 'completed', 'details': {}, 'user_id': 'user-1', 'task_id': 'task-done', 'generation_id': 'gen-done', 'timestamp': 1711180100, }), }) form_data = { 'Business Name:': 'Acme', 'Industry:': 'AI tools', 'Who are you hunting?': 'Founders', 'Demographics (Age, Role, Geography):': '30-45, founders, global', 'Psychographics (Pain points, Dreams, Behavior):': 'Want faster execution', 'Where do they hang out?': 'LinkedIn', 'Competitor 1 â€” Weakness:': 'Slow onboarding', 'Competitor 2 â€” Weakness:': 'Weak analytics', 'Competitor 3 â€” Weakness:': 'High price', 'GTM Mode Preference (Guerrilla Warfare, Blitzkrieg, Stealth Mode, Community-Led):': 'Blitzkrieg', 'Unfair Advantage:': 'Deep domain expertise', 'Content Power Strategy (Thought Leadership, Meme Warfare, Long-form Content, Product-led Content, No Content):': 'Thought Leadership', 'Monthly Budget:': '$10000', 'Team Size & Strength:': '5 people', 'Time Horizon for First Attack (Launch Date):': '30 days', 'Scale of 1-10 (1 = Safe, 10 = Extreme):': '7', 'Category Design Intent (Yes/No):': 'Yes', 'Exit Intent (Acquisition/IPO/Lifestyle Business/Industry Consolidation):': 'IPO', 'Global Domination or Local Niche King? (Global Scale Brand/Hyperlocal Authority/Regional Powerhouse):': 'Global Scale Brand', 'Target Launch Location/Country:': 'India', } with patch.object(deps_module, 'check_service_access', fake_check_service_access), \ patch.object(gtm_routes, 'get_collection', fake_get_collection), \ patch.object(gtm_routes, 'redis_client', fake_redis), \ patch.object(gtm_routes.gtm_service, '_generate_pdf_report', return_value={ 'success': True, 'pdf_path': regenerated_pdf_path, 'pdf_filename': 'acme_saved.pdf', }), \ patch.object(celery_tasks_module.generate_gtm_plan, 'delay', side_effect=fake_delay), \ patch('celery.result.AsyncResult', FakeAsyncResult): client = TestClient(app) response = client.post('/generate_gtm_plan', data=form_data) assert response.status_code == 200, response.text assert response.json()['task_id'] == 'task-123' assert captured_delay['user_inputs']['Section 5: Long-Term Vision â€” Empire Blueprint']['Target Launch Location/Country:'] == 'India' response = client.get('/gtm_plan_result/task-123') assert response.status_code == 200, response.text result_payload = response.json() assert result_payload['industry_growth_data'] == '25% CAGR' assert result_payload['visualization_type'] == 'strategic_flow' assert result_payload['visualization_available'] is True assert result_payload['pdf_available'] is True response = client.get(f'/download_gtm_pdf/{plan_id}') assert response.status_code == 200, response.text assert 'Acme_GTM_Strategy.pdf' in response.headers.get('content-disposition', '') assert collection.updated, 'expected regenerated PDF metadata to be stored' response = client.get('/user_gtm_plans') assert response.status_code == 200, response.text plans_payload = response.json() beta_plan = next(plan for plan in plans_payload['plans'] if plan['business_name'] == 'Beta') assert beta_plan['pdf_available'] is True response = client.get(f'/gtm_plan/{plan_id}') assert response.status_code == 200, response.text assert response.json()['plan']['business_name'] == 'Acme' response = client.get('/generation_status') assert response.status_code == 200, response.text status_payload = response.json() assert 'task-123' in status_payload['active_tasks'] assert status_payload['active_generations']['gen-123']['status'] == 'ai_generation' response = client.delete(f'/delete_gtm_plan/{delete_plan_id}') assert response.status_code == 200, response.text assert response.json()['success'] is True assert not os.path.exists(existing_pdf_path) print('gtm-route-smoke: ok') '@ | .\venv\Scripts\python.exe - for 20s


The first GTM smoke test found a form-alias detail: FastAPI is correctly expecting the real em-dash competitor field names there. I’m rerunning the route checks with the actual runtime field names so we verify the contract the server is really enforcing.

Ran @' import json import os import tempfile from copy import deepcopy from types import SimpleNamespace from unittest.mock import patch from bson import ObjectId from fastapi import FastAPI from fastapi.testclient import TestClient import app.api.deps as deps_module from app.api.deps import get_current_user from app.api.routes import gtm_routes import app.celery_tasks.celery_tasks as celery_tasks_module DASH = '\u2014' SECTION5 = f'Section 5: Long-Term Vision {DASH} Empire Blueprint' class FakeCursor: def __init__(self, items): self.items = items def sort(self, *args, **kwargs): return self def skip(self, count): self.items = self.items[count:] return self def limit(self, count): self.items = self.items[:count] return self def __aiter__(self): self._iter = iter(self.items) return self async def __anext__(self): try: return next(self._iter) except StopIteration: raise StopAsyncIteration class FakeCollection: def __init__(self, docs): self.docs = docs self.updated = [] self.deleted = [] @staticmethod def _matches(doc, query): for key, value in query.items(): if doc.get(key) != value: return False return True async def find_one(self, query): for doc in self.docs: if self._matches(doc, query): return deepcopy(doc) return None async def count_documents(self, query): return sum(1 for doc in self.docs if self._matches(doc, query)) def find(self, query): return FakeCursor([deepcopy(doc) for doc in self.docs if self._matches(doc, query)]) async def update_one(self, query, update): self.updated.append((deepcopy(query), deepcopy(update))) for doc in self.docs: if self._matches(doc, query): doc.update(update.get('$set', {})) return SimpleNamespace(modified_count=1) return SimpleNamespace(modified_count=0) async def delete_one(self, query): self.deleted.append(deepcopy(query)) before = len(self.docs) self.docs = [doc for doc in self.docs if not self._matches(doc, query)] return SimpleNamespace(deleted_count=before - len(self.docs)) class FakeRedis: def __init__(self, payloads): self.payloads = payloads def scan_iter(self, match=None): return list(self.payloads.keys()) def get(self, key): return self.payloads.get(key) async def fake_user(): return 'user-1' async def fake_check_service_access(service_id, user_id): return True app = FastAPI() app.include_router(gtm_routes.router) app.dependency_overrides[get_current_user] = fake_user with tempfile.TemporaryDirectory() as tmpdir: existing_pdf_path = os.path.join(tmpdir, 'existing.pdf') with open(existing_pdf_path, 'wb') as fh: fh.write(b'%PDF-1.4 existing') regenerated_pdf_path = os.path.join(tmpdir, 'regenerated.pdf') with open(regenerated_pdf_path, 'wb') as fh: fh.write(b'%PDF-1.4 regenerated') plan_id = ObjectId() delete_plan_id = ObjectId() collection = FakeCollection([ { '_id': plan_id, 'user_id': 'user-1', 'business_name': 'Acme', 'industry': 'AI', 'gtm_plan': '# GTM Plan', 'pdf_path': '', 'pdf_filename': '', 'created_at': '2026-03-23T10:00:00', }, { '_id': ObjectId(), 'user_id': 'user-1', 'business_name': 'Beta', 'industry': 'SaaS', 'gtm_plan': '# Beta Plan', 'pdf_path': '', 'pdf_filename': 'beta_saved.pdf', 'created_at': '2026-03-23T09:00:00', }, { '_id': delete_plan_id, 'user_id': 'user-1', 'business_name': 'DeleteCo', 'industry': 'Fintech', 'gtm_plan': '# Delete Plan', 'pdf_path': existing_pdf_path, 'pdf_filename': 'deleteco.pdf', 'created_at': '2026-03-23T08:00:00', }, ]) def fake_get_collection(name): assert name == 'gtm_plans' return collection captured_delay = {} def fake_delay(*, user_id, user_inputs): captured_delay['user_id'] = user_id captured_delay['user_inputs'] = user_inputs return SimpleNamespace(id='task-123') class FakeAsyncResult: def __init__(self, task_id, app=None): self.state = 'SUCCESS' self.info = None self.result = { 'success': True, 'user_id': 'user-1', 'result': { 'plan_id': str(plan_id), 'gtm_plan': '# Final GTM Plan', 'business_name': 'Acme', 'industry': 'AI', 'original_industry': 'AI tools', 'market_intelligence': {'validated_industry': 'AI'}, 'industry_growth_data': '25% CAGR', 'strategic_nodes': [{'id': 'core-strategy'}], 'node_connections': [{'source': 'core-strategy', 'target': 'market-entry'}], 'visualization_type': 'strategic_flow', 'visualization_available': True, 'pdf_filename': 'acme_saved.pdf', 'generation_id': 'gen-123', }, } fake_redis = FakeRedis({ 'gtm:user-1:task-123:progress': json.dumps({ 'progress': 65, 'status': 'ai_generation', 'details': {'phase': 'generation'}, 'user_id': 'user-1', 'task_id': 'task-123', 'generation_id': 'gen-123', 'timestamp': 1711180000, }), 'gtm:user-1:task-done:progress': json.dumps({ 'progress': 100, 'status': 'completed', 'details': {}, 'user_id': 'user-1', 'task_id': 'task-done', 'generation_id': 'gen-done', 'timestamp': 1711180100, }), }) form_data = { 'Business Name:': 'Acme', 'Industry:': 'AI tools', 'Who are you hunting?': 'Founders', 'Demographics (Age, Role, Geography):': '30-45, founders, global', 'Psychographics (Pain points, Dreams, Behavior):': 'Want faster execution', 'Where do they hang out?': 'LinkedIn', f'Competitor 1 {DASH} Weakness:': 'Slow onboarding', f'Competitor 2 {DASH} Weakness:': 'Weak analytics', f'Competitor 3 {DASH} Weakness:': 'High price', 'GTM Mode Preference (Guerrilla Warfare, Blitzkrieg, Stealth Mode, Community-Led):': 'Blitzkrieg', 'Unfair Advantage:': 'Deep domain expertise', 'Content Power Strategy (Thought Leadership, Meme Warfare, Long-form Content, Product-led Content, No Content):': 'Thought Leadership', 'Monthly Budget:': '$10000', 'Team Size & Strength:': '5 people', 'Time Horizon for First Attack (Launch Date):': '30 days', 'Scale of 1-10 (1 = Safe, 10 = Extreme):': '7', 'Category Design Intent (Yes/No):': 'Yes', 'Exit Intent (Acquisition/IPO/Lifestyle Business/Industry Consolidation):': 'IPO', 'Global Domination or Local Niche King? (Global Scale Brand/Hyperlocal Authority/Regional Powerhouse):': 'Global Scale Brand', 'Target Launch Location/Country:': 'India', } with patch.object(deps_module, 'check_service_access', fake_check_service_access), \ patch.object(gtm_routes, 'get_collection', fake_get_collection), \ patch.object(gtm_routes, 'redis_client', fake_redis), \ patch.object(gtm_routes.gtm_service, '_generate_pdf_report', return_value={ 'success': True, 'pdf_path': regenerated_pdf_path, 'pdf_filename': 'acme_saved.pdf', }), \ patch.object(celery_tasks_module.generate_gtm_plan, 'delay', side_effect=fake_delay), \ patch('celery.result.AsyncResult', FakeAsyncResult): client = TestClient(app) response = client.post('/generate_gtm_plan', data=form_data) assert response.status_code == 200, response.text assert response.json()['task_id'] == 'task-123' assert captured_delay['user_inputs'][SECTION5]['Target Launch Location/Country:'] == 'India' response = client.get('/gtm_plan_result/task-123') assert response.status_code == 200, response.text result_payload = response.json() assert result_payload['industry_growth_data'] == '25% CAGR' assert result_payload['visualization_type'] == 'strategic_flow' assert result_payload['visualization_available'] is True assert result_payload['pdf_available'] is True response = client.get(f'/download_gtm_pdf/{plan_id}') assert response.status_code == 200, response.text assert 'Acme_GTM_Strategy.pdf' in response.headers.get('content-disposition', '') assert collection.updated, 'expected regenerated PDF metadata to be stored' response = client.get('/user_gtm_plans') assert response.status_code == 200, response.text plans_payload = response.json() beta_plan = next(plan for plan in plans_payload['plans'] if plan['business_name'] == 'Beta') assert beta_plan['pdf_available'] is True response = client.get(f'/gtm_plan/{plan_id}') assert response.status_code == 200, response.text assert response.json()['plan']['business_name'] == 'Acme' response = client.get('/generation_status') assert response.status_code == 200, response.text status_payload = response.json() assert 'task-123' in status_payload['active_tasks'] assert status_payload['active_generations']['gen-123']['status'] == 'ai_generation' response = client.delete(f'/delete_gtm_plan/{delete_plan_id}') assert response.status_code == 200, response.text assert response.json()['success'] is True assert not os.path.exists(existing_pdf_path) print('gtm-route-smoke: ok') '@ | .\venv\Scripts\python.exe - for 11s


Ran @' import inspect import app.celery_tasks.celery_tasks as m print(type(m.generate_gtm_plan)) print(m.generate_gtm_plan) print(inspect.signature(m.generate_gtm_plan.run)) '@ | .\venv\Scripts\python.exe - for 3s


I’ve verified the GTM HTTP routes. I’m doing one more narrow check on the Celery side so we know GTM progress is both emitted over websockets and persisted in Redis for status recovery.

Ran @' from unittest.mock import patch import app.celery_tasks.celery_tasks as tasks_module from app.services.gtm_service import gtm_service store_calls = [] emit_calls = [] async def fake_connect(): return None async def fake_close(): return None def fake_store_progress(prefix, user_id, task_id, progress, status, details=None, ttl=300): store_calls.append({ 'prefix': prefix, 'user_id': user_id, 'task_id': task_id, 'progress': progress, 'status': status, 'details': details, 'ttl': ttl, }) def fake_emit(user_id, progress, message, payload, progress_type='general'): emit_calls.append({ 'user_id': user_id, 'progress': progress, 'message': message, 'payload': payload, 'progress_type': progress_type, }) def fake_generate_plan(user_id, user_inputs, loop, progress_callback): progress_callback(42, 'Building GTM plan', {'phase': 'generation'}) return {'success': True, 'generation_id': 'gen-42'} tasks_module.generate_gtm_plan.request.id = 'celery-task-42' with patch.object(tasks_module, 'store_progress', side_effect=fake_store_progress), \ patch('app.core.progress.manager.emit', side_effect=fake_emit), \ patch('app.db.mongo.connect', side_effect=fake_connect), \ patch('app.db.mongo.close', side_effect=fake_close), \ patch.object(gtm_service, 'generate_plan', side_effect=fake_generate_plan): result = tasks_module.generate_gtm_plan.run('user-1', {'sample': 'data'}) assert result['success'] is True assert result['user_id'] == 'user-1' assert store_calls, 'store_progress was not called' assert emit_calls, 'manager.emit was not called' assert store_calls[0]['prefix'] == 'gtm' assert store_calls[0]['task_id'] == 'celery-task-42' assert store_calls[0]['progress'] == 42 assert store_calls[0]['details']['task_id'] == 'celery-task-42' assert emit_calls[0]['progress_type'] == 'gtm' print('gtm-celery-progress-smoke: ok') '@ | .\venv\Scripts\python.exe - for 4s


Ran git status --short 'Server1_FastApi/app/api/routes/gtm_routes.py' 'Server1_FastApi/app/schemas/gtm.py' 'Server1_FastApi/app/celery_tasks/celery_tasks.py' 'Server1_FastApi/app/services/gtm_service.py' for 1s


Ran git diff -- 'Server1_FastApi/app/api/routes/gtm_routes.py' 'Server1_FastApi/app/schemas/gtm.py' 'Server1_FastApi/app/celery_tasks/celery_tasks.py' 'Server1_FastApi/app/services/gtm_service.py'


Ran git rev-parse --show-toplevel


The GTM parity patch is in place and the targeted verification passed. I’m updating the task state now so the remaining work is clearly tracked against what’s actually been tested.

Ran rg -n "store_progress\(|user_id\": user_id|GTM generation timed out|GTM generation failed" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\celery_tasks\celery_tasks.py' for 1s


Ran rg -n "def _build_plan_query|Target Launch Location/Country|industry_growth_data|download_gtm_pdf|generation_status" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\api\routes\gtm_routes.py' for 1s


Ran rg -n "industry_growth_data|visualization_type|visualization_available" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\schemas\gtm.py' for 1s


Ran rg -n "generation_id" 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\services\gtm_service.py' for 1s


Ran rg -n 'store_progress\(|"user_id": user_id|GTM generation timed out|GTM generation failed' 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\celery_tasks\celery_tasks.py'


Ran rg -n 'return \{"success": True, "user_id": user_id, "result": result\}' 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\celery_tasks\celery_tasks.py'


Ran rg -n '"user_id": user_id|"result": result' 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\celery_tasks\celery_tasks.py'


Ran $lines = Get-Content 'd:\Desktop\Server1_fastapi_community\Server1_serverauth\Server1_FastApi\app\celery_tasks\celery_tasks.py'; 410..470 | ForEach-Object { '{0,4}: {1}' -f ($_+1), $lines[$_] }


Worked for 29m 20s
GTM parity moved forward in this pass. I patched the remaining route/schema/Celery gaps in gtm_routes.py, gtm.py, celery_tasks.py, and gtm_service.py.

The important changes are:

GTM now accepts the frontend’s Target Launch Location/Country: field and carries it into the stored input payload in gtm_routes.py.
GTM result responses now include industry_growth_data, visualization_type, and visualization_available in gtm_routes.py and gtm.py.
/download_gtm_pdf/{plan_id} now regenerates the PDF when the file is missing, then persists the new metadata, matching Flask much more closely in gtm_routes.py.
/generation_status no longer depends only on in-memory state; it now reads GTM progress from Redis and falls back to memory only if needed in gtm_routes.py.
Celery GTM progress now gets stored in Redis as well as emitted over websocket in celery_tasks.py, and GTM progress payloads now consistently carry generation_id in gtm_service.py.
I verified this with:

python -m compileall app
a GTM route smoke test covering /generate_gtm_plan, /gtm_plan_result/{task_id}, /download_gtm_pdf/{plan_id}, /user_gtm_plans, /gtm_plan/{plan_id}, /delete_gtm_plan/{plan_id}, and /generation_status
a Celery smoke test confirming GTM progress is both persisted via store_progress(...) and emitted over websocket
One honest caveat remains: this was a strong backend smoke pass with patched dependencies, not a full browser-backed live run against your real frontend plus live Mongo/Redis/Celery/OpenAI services yet. The next safest step is the same strict parity pass for Business Plan and Pitch, then a real end-to-end frontend integration run.


4 files changed
+956
-279
Undo

Review
app/api/routes/gtm_routes.py
app/celery_tasks/celery_tasks.py
app/schemas/gtm.py
app/services/gtm_service.py


 See understand the complete readme.txt in that i have give you where i have got stopped , So you need to understand
  the complete readme.txt and understand the project files and give me Plan and next steps to complete the task which
  are their in the readme.txt

◐ The user wants me to understand the readme.txt file in the current directory and create a plan based on where they 
  stopped. Let me first read the readme.txt file to understand the project and what tasks remain.

● Read readme.txt
  └ 1 line read

● List directory .
  └ 23 files found

● The readme.txt is large. Let me read it in sections to understand the full scope:

✗ Read first 300 lines of readme.txt (shell)
  │ Get-Content "D:\Desktop\New_Flask\FLASK\readme.txt" -Head 300
  └ <exited with error: PowerShell 6+ (pwsh) is not available. Please install it from https://aka.ms/powershell. Error:
    Error: Command failed: pwsh.exe --version
    'pwsh.exe' is not recognized as an internal or external command,
    operable program or batch file.
    >

✗ Read last 500 lines of readme.txt (shell)
  │ Get-Content "D:\Desktop\New_Flask\FLASK\readme.txt" -Tail 500
  └ <exited with error: PowerShell 6+ (pwsh) is not available. Please install it from https://aka.ms/powershell. Error:
    Error: Command failed: pwsh.exe --version
    'pwsh.exe' is not recognized as an internal or external command,
    operable program or batch file.
    >

● Read readme.txt
  └ L1:300 (300 lines read)

● Let me continue reading the readme.txt to understand the full context:

● Read readme.txt
  └ L300:600 (301 lines read)

● Read readme.txt
  └ L600:900 (301 lines read)

● Read readme.txt
  └ L900:1200 (301 lines read)

● Read readme.txt
  └ L1200:1500 (301 lines read)

● Let me continue reading to understand the full scope of where work was stopped:

● Read readme.txt
  └ L1500:1800 (301 lines read)

● Read readme.txt
  └ L1800:2100 (301 lines read)

● Let me continue reading to the end of the readme.txt to fully understand where work stopped:

● Read readme.txt
  └ L2100:2500 (401 lines read)

● Read readme.txt
  └ L2500:2900 (400 lines read)

● Let me continue reading the end of the readme.txt to see the final status:

● Read readme.txt
  └ L2900:3300 (36 lines read)

● Read readme.txt

● Read readme.txt
  └ L2938:2990 (46 lines read)

● Now I have a complete understanding of the readme.txt. Let me also check the current state of the Server1_FastApi
  folder to understand what's there now:

● List directory Server1_FastApi
  └ 15 files found

● List directory server2
  └ 27 files found

● List directory Server1_FastApi\app
  └ 11 files found

● List directory server2\blueprints
  └ 27 files found

● Now I have a complete picture. Let me create a comprehensive plan based on the readme.txt analysis:

● Create plan.md +102
  └ ~\.copilot\session-state\b2a80834-2405-4987-8bad-b9aa9760d027\plan.md

● Todo added 6 items
  │ Complete GTM Parity
  │ Complete Business Plan Parity
  │ Complete Pitch Analysis Parity
  │ Complete SWOT Parity
  │ Audit Missing Blueprints
  └ End-to-End Integration Testing

● Todo dependency 8 links added
  │ business-parity → gtm-parity
  │ pitch-parity → business-parity
  │ swot-parity → gtm-parity
  │ e2e-testing → gtm-parity
  │ e2e-testing → business-parity
  │ e2e-testing → pitch-parity
  │ e2e-testing → swot-parity
  └ e2e-testing → blueprints-audit

● Summary: Flask to FastAPI Migration Plan

  Based on my analysis of the readme.txt, here's where work stopped and what remains:

  ✅ Completed Work

   - Basic route surface parity established
   - SSE replaced with WebSockets for progress
   - .env file sync between Flask and FastAPI
   - GTM routes partially ported with Redis-backed progress
   - Frontend builds successfully against FastAPI
   - Auth, CSRF, health endpoints working

  ⚠️ Critical Gaps (Not Yet Complete)

  ┌──────────────┬───────────┬─────────────┬─────────────┐
  │ Module       │ Flask LOC │ FastAPI LOC │ Missing     │
  ├──────────────┼───────────┼─────────────┼─────────────┤
  │ GTM          │ ~2297     │ ~664        │ ~1633 lines │
  ├──────────────┼───────────┼─────────────┼─────────────┤
  │ Pitch        │ ~4839     │ ~815        │ ~4024 lines │
  ├──────────────┼───────────┼─────────────┼─────────────┤
  │ Business     │ ~4784     │ ~509        │ ~4275 lines │
  ├──────────────┼───────────┼─────────────┼─────────────┤
  │ SWOT         │ ~varies   │ partial     │ Needs audit │
  └──────────────┴───────────┴─────────────┴─────────────┘

  📋 Next Steps (In Order)

   1. Complete GTM - Already partially done, finish market intelligence, strategic nodes, PDF generation
   2. Complete Business Plan - Heavy AI generation, complex section flow
   3. Complete Pitch Analysis - Largest module, slide-by-slide processing
   4. Complete SWOT - Competitor analysis, risk analysis, etc.
   5. Audit Missing Blueprints - payment, profile, contact, document, etc.
   6. Full E2E Testing - Live testing with real services

  Plan saved to plan.md. Would you like me to start implementing any of these tasks?

❯ wait Understand the server 2(flask), Server1_FastApi(updated version fastapi) , lliveupdatedstreaming also . and give
  me the plan and give me the step plan please

◐ The user wants me to understand all three components properly:
  1. server2 (Flask) - The original Flask server
  2. Server1_FastApi - The FastAPI version being updated
  3. lliveupdatedstreaming - The frontend

  Let me explore each of these thoroughly before creating a comprehensive plan.

● Explore explore-flask
  └ Agent started in background with agent_id: explore-flask. You can use read_ag...

● Explore explore-fastapi
  └ Agent started in background with agent_id: explore-fastapi. You can use read_...

● Explore explore-frontend
  └ Agent started in background with agent_id: explore-frontend. You can use read...

● I've started 3 parallel agents to analyze all three components. Let me wait for them to complete:

● Read (Explore agent — explore-flask)
  └ Running

● Read (Explore agent — explore-fastapi)
  └ Running

● Read (Explore agent — explore-frontend)
  └ Completed

● Background agent "explore-frontend" (explore) completed 
  └ Explore the frontend at D:\Desktop\New_Flask\FLASK\lliveupdatedstreaming comp...

◐ The frontend agent completed. Let me read its full results and also check on the other agents.

● Read 1774266552342-copilot-tool-output-n4zs7x.txt
  │ ~\AppData\Local\Temp\1774266552342-copilot-tool-output-n4zs7x.txt
  └ 1 line read

● Read (Explore agent — explore-flask)
  └ Running

● Read 1774266552342-copilot-tool-output-n4zs7x.txt
  │ ~\AppData\Local\Temp\1774266552342-copilot-tool-output-n4zs7x.txt
  └ L1:200 (200 lines read)

● Read 1774266552342-copilot-tool-output-n4zs7x.txt
  │ ~\AppData\Local\Temp\1774266552342-copilot-tool-output-n4zs7x.txt
  └ L200:400 (201 lines read)

● Read 1774266552342-copilot-tool-output-n4zs7x.txt
  │ ~\AppData\Local\Temp\1774266552342-copilot-tool-output-n4zs7x.txt
  └ L400:550 (151 lines read)

● Read (Explore agent — explore-fastapi)
  └ Running

● Let me continue viewing frontend results and wait for the other agents:

● Read 1774266552342-copilot-tool-output-n4zs7x.txt
  │ ~\AppData\Local\Temp\1774266552342-copilot-tool-output-n4zs7x.txt
  └ L550:700 (151 lines read)

● Background agent "explore-fastapi" (explore) completed 
  └ Explore the FastAPI server at D:\Desktop\New_Flask\FLASK\Server1_FastApi comp...

◐ The FastAPI agent completed. Let me read its results.

● Read (Explore agent — explore-fastapi)
  └ Completed

● Read 1774267079340-copilot-tool-output-p3g608.txt
  │ ~\AppData\Local\Temp\1774267079340-copilot-tool-output-p3g608.txt
  └ L1:250 (250 lines read)

● Read 1774267079340-copilot-tool-output-p3g608.txt
  │ ~\AppData\Local\Temp\1774267079340-copilot-tool-output-p3g608.txt
  └ L250:500 (250 lines read)

● Read 1774267079340-copilot-tool-output-p3g608.txt
  │ ~\AppData\Local\Temp\1774267079340-copilot-tool-output-p3g608.txt
  └ L500:650 (61 lines read)

● Read (Explore agent — explore-flask)
  └ Completed

● Background agent "explore-flask" (explore) completed 
  └ Explore the Flask server at D:\Desktop\New_Flask\FLASK\server2 comprehensivel...

◐ The Flask agent completed. Let me read its full results to understand the Flask server structure completely.

● Read 1774267105180-copilot-tool-output-2fl0v1.txt
  │ ~\AppData\Local\Temp\1774267105180-copilot-tool-output-2fl0v1.txt
  └ L1:300 (300 lines read)

● Read 1774267105180-copilot-tool-output-2fl0v1.txt
  │ ~\AppData\Local\Temp\1774267105180-copilot-tool-output-2fl0v1.txt
  └ L300:550 (250 lines read)

● Read 1774267105180-copilot-tool-output-2fl0v1.txt
  │ ~\AppData\Local\Temp\1774267105180-copilot-tool-output-2fl0v1.txt
  └ L550:800 (250 lines read)

● Read 1774267105180-copilot-tool-output-2fl0v1.txt
  │ ~\AppData\Local\Temp\1774267105180-copilot-tool-output-2fl0v1.txt
  └ L800:950 (151 lines read)

● Read 1774267105180-copilot-tool-output-2fl0v1.txt
  │ ~\AppData\Local\Temp\1774267105180-copilot-tool-output-2fl0v1.txt
  └ L950:1100 (151 lines read)

● Now I have a complete understanding of all three components. Let me update the plan with this comprehensive
  information:

● Edit plan.md +276 -76
  └ ~\.copilot\session-state\b2a80834-2405-4987-8bad-b9aa9760d027\plan.md

● Now let me update the SQL todos with the detailed breakdown:

● Clear and rebuild todos (sql)
  │ DELETE FROM todo_deps; DELETE FROM todos;
  └ Executed 2 statement(s)

● Todo added 6 items
  │ PHASE 1: GTM Complete Parity
  │ PHASE 2: Business Plan Parity
  │ PHASE 3: SWOT Analysis Parity
  │ PHASE 4: Pitch Analysis
  │ PHASE 5: Supporting Services Audit
  └ PHASE 6: E2E Integration Testing

● Todo dependency 8 links added
  │ phase2-business → phase1-gtm
  │ phase3-swot → phase1-gtm
  │ phase4-pitch → phase2-business
  │ phase5-services → phase3-swot
  │ phase6-testing → phase1-gtm
  │ phase6-testing → phase2-business
  │ phase6-testing → phase3-swot
  └ phase6-testing → phase5-services

● ✅ Complete Analysis Done - Here's Your Step-by-Step Plan

  I've analyzed all three components in depth:

  Project Structure

  ┌────────────────────┬──────────────────────────┬────────────────────────────────────────────┐
  │ Component          │ Location                 │ Tech Stack                                 │
  ├────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
  │ Flask Server       │ server2/                 │ Flask, ~15,000+ lines across 20 blueprints │
  ├────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
  │ FastAPI Server     │ Server1_FastApi/         │ FastAPI, ~5,000 lines across 27 routes     │
  ├────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
  │ Frontend           │ lliveupdatedstreaming/   │ React 18 + TypeScript + Vite + Redux       │
  └────────────────────┴──────────────────────────┴────────────────────────────────────────────┘

  ---------------------------------------------------------------------------------------------------------------------

  Critical Code Gaps Found

  ┌───────────────────┬─────────────┬───────────────┬──────────────────┐
  │ Module            │ Flask Lines │ FastAPI Lines │ Gap              │
  ├───────────────────┼─────────────┼───────────────┼──────────────────┤
  │ GTM               │ ~3,000      │ ~664          │ ~2,336 lines     │
  ├───────────────────┼─────────────┼───────────────┼──────────────────┤
  │ Business Plan     │ ~5,200      │ ~509          │ ~4,691 lines     │
  ├───────────────────┼─────────────┼───────────────┼──────────────────┤
  │ SWOT              │ ~800        │ partial       │ ~400+ lines      │
  ├───────────────────┼─────────────┼───────────────┼──────────────────┤
  │ Pitch             │ disabled    │ ~472          │ Needs decision   │
  └───────────────────┴─────────────┴───────────────┴──────────────────┘

  ---------------------------------------------------------------------------------------------------------------------

  6-Phase Implementation Plan

   PHASE 1: GTM Parity          [2-3 hours] ← START HERE
       ↓
   PHASE 2: Business Plan       [4-5 hours]
       ↓
   PHASE 3: SWOT Analysis       [1-2 hours]
       ↓
   PHASE 4: Pitch Analysis      [2-3 hours] (may skip if disabled)
       ↓
   PHASE 5: Services Audit      [2-3 hours] (payment, profile, etc.)
       ↓
   PHASE 6: E2E Testing         [2-3 hours]

  Total Estimated Time: 14-19 hours

  ---------------------------------------------------------------------------------------------------------------------

  Key Technical Notes

   1. Progress Streaming: Flask uses SSE with in-memory queues → FastAPI uses WebSockets with Redis Pub/Sub
   2. Frontend Contract: Expects /ws/progress/{type}?token=...&task_id=...
   3. AI Services: 4 separate Azure OpenAI deployments (GTM, Business, Pitch, SWOT)
   4. Database: MongoDB (Azure Cosmos DB) + Redis (Azure Cache)

  ---------------------------------------------------------------------------------------------------------------------

  The detailed plan is saved to plan.md. Would you like me to start implementing Phase 1 (GTM Parity)?

❯ See complete all the phases correctly ,make sure i need a complete production ready code i don't want any parital
  implementation i need the complete implementation and also flask(server2) is a old version of FASTAPI
  (Server1_FastApi) , so we updating the backend so any changes that you have done in the server1_fastapi need to
  integrate correctly to the Front-end without making any mistakes. See and also in the flask we use SSE repose for the
  progress now we are updating it with the sockets in the FASTAPI(Server1_FastApi). So implement the things correctly i
  need a complete and correct things .

◐ The user wants me to implement ALL phases completely with production-ready code. This is a significant undertaking. Let 
  me break this down:

  1. They want complete implementation, not partial
  2. Flask (server2) is the OLD version, FastAPI (Server1_FastApi) is the NEW version being updated
  3. SSE in Flask → WebSockets in FastAPI
  4. Frontend integration must work correctly
  5. Production-ready code

  This is a large task. I should:
  1. Start with Phase 1 (GTM) as it's the dependency for other phases
  2. Work systematically through each phase
  3. Ensure WebSocket progress works correctly
  4. Test the integration

  Let me start by marking the first todo as in_progress and then begin the implementation. I'll use background agents to 
  work on different phases in parallel where possible, but some have dependencies.

  Let me start with GTM parity first since it's the foundation.

● I'll implement all phases completely with production-ready code. Let me start systematically.

● Todo started phase1-gtm

● Read gtm_bp.py
  │ server2\blueprints\gtm_bp.py
  └ L1:150 (150 lines read)

● Read gtm_service.py
  │ Server1_FastApi\app\services\gtm_service.py
  └ L1:100 (100 lines read)

● Compacting conversation history...

● Read gtm_bp.py
  │ server2\blueprints\gtm_bp.py
  └ L140:350 (211 lines read)

● Read gtm_bp.py
  │ server2\blueprints\gtm_bp.py
  └ L350:550 (201 lines read)

● Read gtm_bp.py
  │ server2\blueprints\gtm_bp.py
  └ L550:850 (301 lines read)

● Read gtm_bp.py
  │ server2\blueprints\gtm_bp.py
  └ L850:1150 (301 lines read)

● This is a large codebase. Let me use parallel agents to implement all phases efficiently:

● Developer gtm-complete-service
  └ Agent started in background with agent_id: gtm-complete-service. You can use ...

● Developer gtm-routes-websocket
  └ Agent started in background with agent_id: gtm-routes-websocket. You can use ...

● Compaction completed 
  │ A new checkpoint has been added to your session.
  └ Use /session checkpoints 1 to view the compaction summary.

● Developer business-plan-service
  └ Agent started in background with agent_id: business-plan-service. You can use...

● Developer swot-service-routes
  └ Agent started in background with agent_id: swot-service-routes. You can use r...

● Developer celery-tasks-update
  └ Agent started in background with agent_id: celery-tasks-update. You can use r...

● Developer websocket-progress-handler
  └ Agent started in background with agent_id: websocket-progress-handler. You ca...

● Developer pitch-analysis-service
  └ Agent started in background with agent_id: pitch-analysis-service. You can us...

● Explore supporting-services-audit
  └ Agent started in background with agent_id: supporting-services-audit. You can...

● I've launched 7 parallel developer agents to implement all phases. Let me check the status:

● Listing background agents 

● All 8 agents are running in parallel. Let me wait for them to complete:

● Read (Developer agent — gtm-complete-service)
  └ Running

● Read (Developer agent — swot-service-routes)
  └ Running

● Request failed due to a transient API error. Retrying...

● Background agent "supporting-services-audit" (explore) completed 
  └ Audit all supporting services in FastAPI vs Flask to identify gaps.
    
    **Compar...

● Request failed due to a transient API error. Retrying...

◐ The supporting-services-audit agent has completed. Let me read its results while the other agents continue working.

● Read (Explore agent — supporting-services-audit)
  └ Completed

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Excellent! The supporting services audit is complete. Let me check on the other agents:

● Listing background agents 

● Request failed due to a transient API error. Retrying...

● Background agent "business-plan-service" (Developer) completed 
  └ You are implementing the complete Business Plan service for FastAPI.
    
    **Refer...

● Request failed due to a transient API error. Retrying...

● Background agent "websocket-progress-handler" (Developer) completed 
  └ You are implementing the WebSocket progress system for FastAPI that replaces ...

● Request failed due to a transient API error. Retrying...

● Background agent "gtm-routes-websocket" (Developer) completed 
  └ You are implementing the complete GTM routes and WebSocket progress for FastA...

● Background agent "swot-service-routes" (Developer) completed 
  └ You are implementing the complete SWOT Analysis service for FastAPI.
    
    **Refer...

● Background agent "gtm-complete-service" (Developer) completed 
  └ You are implementing the complete GTM service for FastAPI. The Flask version ...

● Background agent "pitch-analysis-service" (Developer) completed 
  └ You are implementing the Pitch Analysis service for FastAPI.
    
    **Reference Fla...

● Request failed due to a transient API error. Retrying...

◐ Multiple agents have completed. Let me read their results to see what was implemented.

● Excellent! Multiple agents completed. Let me retrieve their results:

● Read (Developer agent — gtm-complete-service)
  └ Completed

● Read (Developer agent — gtm-routes-websocket)
  └ Completed

● Read (Developer agent — business-plan-service)
  └ Completed

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Background agent "celery-tasks-update" (Developer) completed 
  └ You are updating the Celery tasks to ensure complete integration with FastAPI...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

◐ All the Developer agents hit rate limits. Let me check the remaining agents and then I'll need to implement the code 
  directly myself instead of using sub-agents.

● The Developer agents hit rate limits. Let me check the remaining ones and then implement directly:

● Read (Developer agent — websocket-progress-handler)
  └ Completed

● Read (Developer agent — celery-tasks-update)
  └ Completed

● Read (Developer agent — swot-service-routes)
  └ Completed

● Read (Developer agent — pitch-analysis-service)
  └ Completed

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● All sub-agents hit rate limits. I'll implement the code directly. Let me start with the most critical files:

● Read gtm_service.py
  │ Server1_FastApi\app\services\gtm_service.py
  └ 432 lines read

● Read progress.py
  │ Server1_FastApi\app\core\progress.py
  └ 453 lines read

● Read config.py
  │ Server1_FastApi\app\core\config.py
  └ 285 lines read

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Good, the core infrastructure is already in place. Let me now check what routes exist and enhance the GTM service with
  full Flask parity:

● Read gtm_routes.py
  │ Server1_FastApi\app\api\routes\gtm_routes.py
  └ 1 line read

● List directory Server1_FastApi\app\celery_tasks
  └ 3 files found

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Read gtm_routes.py
  │ Server1_FastApi\app\api\routes\gtm_routes.py
  └ L1:150 (150 lines read)

● Read celery_tasks.py
  │ Server1_FastApi\app\celery_tasks\celery_tasks.py
  └ 1 line read

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Read gtm_routes.py
  │ Server1_FastApi\app\api\routes\gtm_routes.py
  └ L150:350 (201 lines read)

● Read celery_tasks.py
  │ Server1_FastApi\app\celery_tasks\celery_tasks.py
  └ L1:150 (150 lines read)

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Read celery_tasks.py
  │ Server1_FastApi\app\celery_tasks\celery_tasks.py
  └ L150:350 (201 lines read)

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Read celery_tasks.py
  │ Server1_FastApi\app\celery_tasks\celery_tasks.py
  └ L350:600 (251 lines read)

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● The Celery tasks infrastructure looks good. Let me check if there's a GTM task defined:

● Search (grep)
  │ "generate_gtm_plan" (Server1_FastApi\app\celery_tasks\celery_tasks.py)
  └ 3 lines found

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Operation cancelled by user

❯ Sorry for stopping can you say whats you're next plan and can you say where you have stopped and whats the next step
  and details please i will implement by my self

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

◐ The user wants me to summarize where I stopped and what the next steps are so they can implement themselves. Let me 
  provide a clear summary of:
  1. What was completed
  2. Where I stopped
  3. Detailed next steps for implementation

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...

✗ Edit plan.md
  │ ~\.copilot\session-state\b2a80834-2405-4987-8bad-b9aa9760d027\plan.md
  └ No match found

● Request failed due to a transient API error. Retrying...

● Request failed due to a transient API error. Retrying...
