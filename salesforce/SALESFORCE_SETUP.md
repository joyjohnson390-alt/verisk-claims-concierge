# Salesforce Setup — Verisk Property Weather Agent

Connects your Salesforce org to the Verisk Claims Concierge AI via Named Credentials + Apex + Agentforce.

---

## Step 1 — Start the Agent API

In your terminal, from the `verisk-demo` directory:

```bash
.venv/bin/python -m app.web_main
```

This starts the FastAPI server at `http://localhost:8000`.
The `/api/ask` endpoint is what Salesforce will call.

---

## Step 2 — Expose It Publicly with ngrok

Install ngrok if you don't have it:
```bash
brew install ngrok
```

In a second terminal tab:
```bash
ngrok http 8000
```

Copy the `https://` URL it gives you — looks like:
```
https://abc123.ngrok-free.app
```

Test it works:
```bash
curl -X POST https://abc123.ngrok-free.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What weather events have hit Pensacola recently?", "lat": 30.4213, "lon": -87.2169}'
```

You should get a JSON response with `answer`, `sources`, and `weather_available`.

---

## Step 3 — Create a Named Credential in Salesforce

1. Go to **Setup → Security → Named Credentials**
2. Click **New Legacy** (or **New** depending on your API version)
3. Fill in:
   - **Label:** `VeriskAgentAPI`
   - **Name:** `VeriskAgentAPI` ← must match exactly (used in Apex)
   - **URL:** `https://abc123.ngrok-free.app` ← your ngrok URL
   - **Identity Type:** `Anonymous`
   - **Authentication Protocol:** `No Authentication`
   - **Allow Merge Fields in HTTP Header:** checked
   - **Allow Merge Fields in HTTP Body:** checked
4. Save

> **Note:** For a real deployment, replace ngrok with a cloud-hosted URL (Heroku, Railway, Render, etc.) and add proper authentication (API key in header).

---

## Step 4 — Add the Remote Site Setting

1. Go to **Setup → Security → Remote Site Settings**
2. Click **New Remote Site**
3. Fill in:
   - **Remote Site Name:** `VeriskAgentAPI`
   - **Remote Site URL:** `https://abc123.ngrok-free.app`
   - **Active:** checked
4. Save

---

## Step 5 — Deploy the Apex Class

From the `verisk-demo` directory, deploy the Apex class to your org:

```bash
sf org login web --alias my-demo-org
sf project deploy start --source-dir salesforce/ --target-org my-demo-org
```

Or deploy manually via Developer Console:
1. Go to **Setup → Developer Console**
2. **File → New → Apex Class**
3. Name it `PropertyWeatherAgent`
4. Paste the contents of `salesforce/classes/PropertyWeatherAgent.cls`
5. Save (Ctrl+S)

---

## Step 6 — Test the Apex Class

In Developer Console → **Debug → Open Execute Anonymous Window**, paste:

```apex
PropertyWeatherAgent.AgentRequest req = new PropertyWeatherAgent.AgentRequest();
req.question = 'What weather events have affected properties in Pensacola, FL?';
req.propertyAddress = '1142 Palmetto Drive, Pensacola, FL 32501';
req.lat = 30.4213;
req.lon = -87.2169;

List<PropertyWeatherAgent.AgentRequest> reqs = new List<PropertyWeatherAgent.AgentRequest>{ req };
List<PropertyWeatherAgent.AgentResponse> resps = PropertyWeatherAgent.ask(reqs);

System.debug('Answer: ' + resps[0].answer);
System.debug('Sources: ' + resps[0].sources);
System.debug('Weather available: ' + resps[0].weatherAvailable);
```

Click **Execute**. Check the **Logs** panel — you should see the agent's answer.

---

## Step 7 — Wire into Agentforce

### Create the Agent Action

1. Go to **Setup → Agentforce → Agent Actions**
2. Click **New Agent Action**
3. Select **Type:** `Apex`
4. Select class: `PropertyWeatherAgent`, method: `ask`
5. Configure inputs:
   - `question` → map to agent conversation context
   - `propertyAddress` → optional, map from record field
6. Configure output: `answer` → surface to agent response
7. Save as: `Ask Property Weather Agent`

### Create the Agent Topic

1. Go to **Setup → Agentforce → Agents** → open your agent (or create new)
2. Add a **Topic:**
   - **Name:** `Property and Weather Risk`
   - **Description:** `Answers questions about property damage risk, weather events, and loss data for a given address or location. Use when the user asks about weather, property risk, storm damage, or claim-related location data.`
3. Add the action `Ask Property Weather Agent` to this topic
4. Set the action instructions: `When the user asks about weather or property risk, call this action with their question and any property address or coordinates mentioned. Surface the answer directly.`
5. Save and activate

---

## Step 8 — Test in Agentforce

1. Go to **Setup → Agentforce → Agents** → open your agent
2. Click **Preview**
3. Type: *"What weather events have hit properties in Pensacola, FL recently?"*
4. The agent should call your action and return a grounded answer from the Verisk AI

---

## Architecture Summary

```
Salesforce Agentforce Agent
  └─ Topic: Property and Weather Risk
       └─ Action: Ask Property Weather Agent (Apex @InvocableMethod)
            └─ Named Credential: VeriskAgentAPI
                 └─ POST /api/ask  ──►  LangGraph Agent (FastAPI :8000)
                                             └─ retrieve_weather (mock NOAA)
                                             └─ search_knowledge_base (ChromaDB)
                                             └─ generate_response (Claude)
```

---

## For Production (beyond demo)

- Replace ngrok with a proper cloud deployment (Heroku, Railway, AWS Lambda)
- Add API key authentication: set a secret header in Named Credential, verify it in FastAPI middleware
- Replace mock APIs with real NOAA / weather data provider
- Replace SQLite with a production database
- Add Salesforce Connected App OAuth for identity propagation
