/**
 * PropertyWeatherAgent
 *
 * Calls the Verisk Claims Concierge AI external agent via Named Credential.
 * Exposes an @InvocableMethod so it can be used in:
 *   - Agentforce actions
 *   - Flow (screen or autolaunched)
 *   - Apex code
 *
 * Named Credential required: VeriskAgentAPI
 * Endpoint: POST /api/ask
 */
public class PropertyWeatherAgent {

    // ── Input / Output types for @InvocableMethod ──────────────────────────

    public class AgentRequest {
        @InvocableVariable(label='Question' description='Natural language question about the property or weather' required=true)
        public String question;

        @InvocableVariable(label='Property Address' description='Full property address for context (optional)')
        public String propertyAddress;

        @InvocableVariable(label='Latitude' description='Property latitude (optional)')
        public Decimal lat;

        @InvocableVariable(label='Longitude' description='Property longitude (optional)')
        public Decimal lon;
    }

    public class AgentResponse {
        @InvocableVariable(label='Answer')
        public String answer;

        @InvocableVariable(label='Sources')
        public String sources;

        @InvocableVariable(label='Weather Available')
        public Boolean weatherAvailable;

        @InvocableVariable(label='Success')
        public Boolean success;

        @InvocableVariable(label='Error Message')
        public String errorMessage;
    }

    // ── Invocable entry point ──────────────────────────────────────────────

    @InvocableMethod(
        label='Ask Property Weather Agent'
        description='Ask the Verisk Claims Concierge AI a question about property or weather data. Returns a grounded natural language answer with source attribution.'
        category='Financial Services'
    )
    public static List<AgentResponse> ask(List<AgentRequest> requests) {
        List<AgentResponse> responses = new List<AgentResponse>();
        for (AgentRequest req : requests) {
            responses.add(callAgent(req));
        }
        return responses;
    }

    // ── HTTP callout ───────────────────────────────────────────────────────

    private static AgentResponse callAgent(AgentRequest req) {
        AgentResponse resp = new AgentResponse();

        try {
            // Build request body
            Map<String, Object> body = new Map<String, Object>{
                'question' => req.question,
                'persona'  => 'adjuster'
            };
            if (String.isNotBlank(req.propertyAddress)) {
                body.put('property_address', req.propertyAddress);
            }
            if (req.lat != null) {
                body.put('lat', req.lat);
            }
            if (req.lon != null) {
                body.put('lon', req.lon);
            }

            HttpRequest httpReq = new HttpRequest();
            httpReq.setEndpoint('callout:VeriskAgentAPI/api/ask');
            httpReq.setMethod('POST');
            httpReq.setHeader('Content-Type', 'application/json');
            httpReq.setBody(JSON.serialize(body));
            httpReq.setTimeout(30000); // 30s — LLM calls can be slow

            Http http = new Http();
            HttpResponse httpResp = http.send(httpReq);

            if (httpResp.getStatusCode() == 200) {
                Map<String, Object> result = (Map<String, Object>) JSON.deserializeUntyped(httpResp.getBody());
                resp.answer         = (String)  result.get('answer');
                resp.weatherAvailable = (Boolean) result.get('weather_available');
                resp.success        = true;

                // Join sources list into a comma-separated string
                List<Object> srcList = (List<Object>) result.get('sources');
                List<String> srcStrings = new List<String>();
                if (srcList != null) {
                    for (Object s : srcList) {
                        srcStrings.add(String.valueOf(s));
                    }
                }
                resp.sources = String.join(srcStrings, ', ');

            } else {
                resp.success = false;
                resp.errorMessage = 'Agent returned HTTP ' + httpResp.getStatusCode() + ': ' + httpResp.getBody();
            }

        } catch (Exception e) {
            resp.success = false;
            resp.errorMessage = e.getMessage();
        }

        return resp;
    }
}
