import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock AccuLynx API", version="1.0.0")

ESTIMATES = {
    "CLM-2024-0891": {
        "claim_id": "CLM-2024-0891",
        "acculynx_estimate_id": "ACX-88421",
        "line_items": [
            {
                "category": "Roofing",
                "description": "Remove and replace asphalt shingle roof — 28 sq",
                "quantity": 28.0,
                "unit": "sq",
                "unit_price": 650.0,
                "total": 18200.0,
            },
            {
                "category": "Roofing",
                "description": "Roof decking repair — OSB 7/16\"",
                "quantity": 12.0,
                "unit": "sheet",
                "unit_price": 95.0,
                "total": 1140.0,
            },
            {
                "category": "Interior",
                "description": "Ceiling drywall replacement — water-damaged sections",
                "quantity": 320.0,
                "unit": "sq ft",
                "unit_price": 8.50,
                "total": 2720.0,
            },
            {
                "category": "Interior",
                "description": "Interior paint — ceilings and affected walls",
                "quantity": 480.0,
                "unit": "sq ft",
                "unit_price": 3.00,
                "total": 1440.0,
            },
            {
                "category": "Interior",
                "description": "Insulation replacement — blown fiberglass attic",
                "quantity": 1100.0,
                "unit": "sq ft",
                "unit_price": 2.00,
                "total": 2200.0,
            },
            {
                "category": "Roofing",
                "description": "Gutters and downspouts — aluminum 5\"",
                "quantity": 140.0,
                "unit": "ln ft",
                "unit_price": 19.00,
                "total": 2660.0,
            },
            {
                "category": "General",
                "description": "Debris removal and haul-off",
                "quantity": 1.0,
                "unit": "lot",
                "unit_price": 140.0,
                "total": 140.0,
            },
        ],
        "total_estimate": 28500.0,
        "status": "submitted",
        "last_updated": "2024-10-14",
        "estimator": "Marcus Tran",
    },
    "CLM-2024-1187": {
        "claim_id": "CLM-2024-1187",
        "acculynx_estimate_id": "ACX-91047",
        "line_items": [
            {
                "category": "Structural",
                "description": "Exterior load-bearing wall repair — tornado damage",
                "quantity": 64.0,
                "unit": "ln ft",
                "unit_price": 380.0,
                "total": 24320.0,
            },
            {
                "category": "Structural",
                "description": "Structural beam and header replacement",
                "quantity": 3.0,
                "unit": "each",
                "unit_price": 2800.0,
                "total": 8400.0,
            },
            {
                "category": "Roofing",
                "description": "Full roof replacement — hip style, 36 sq",
                "quantity": 36.0,
                "unit": "sq",
                "unit_price": 680.0,
                "total": 24480.0,
            },
            {
                "category": "Garage",
                "description": "Garage door replacement — 16x7 insulated steel",
                "quantity": 1.0,
                "unit": "each",
                "unit_price": 1850.0,
                "total": 1850.0,
            },
            {
                "category": "Garage",
                "description": "Garage framing repair",
                "quantity": 1.0,
                "unit": "lot",
                "unit_price": 3200.0,
                "total": 3200.0,
            },
            {
                "category": "Fence",
                "description": "Wood privacy fence — 6ft, replace 120 ln ft",
                "quantity": 120.0,
                "unit": "ln ft",
                "unit_price": 38.0,
                "total": 4560.0,
            },
            {
                "category": "General",
                "description": "Temporary board-up and tarping — emergency",
                "quantity": 1.0,
                "unit": "lot",
                "unit_price": 390.0,
                "total": 390.0,
            },
        ],
        "total_estimate": 67200.0,
        "status": "approved",
        "last_updated": "2024-10-22",
        "estimator": "Sandra Kowalski",
    },
}


@app.get("/estimates/{claim_id}")
def get_estimate(claim_id: str):
    if claim_id not in ESTIMATES:
        raise HTTPException(
            status_code=404,
            detail="Estimate not found in AccuLynx for this claim ID",
        )
    return ESTIMATES[claim_id]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
