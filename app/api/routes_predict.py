import joblib
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.config import settings
import logging
from supabase import create_client, Client
from app.core.dependencies import verify_api_access

logger = logging.getLogger("app")

router = APIRouter(tags=["Predictions"])

# Load the trained machine learning pipeline once when the API starts up
MODEL = joblib.load(settings.MODEL_PATH)

# Initialize Supabase client if keys are provided in .env
supabase_client: Client = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")

class LoanApplication(BaseModel):
    grossapproval: float = Field(..., description="Gross approved loan amount", examples=[250000.0])
    sbaguaranteedapproval: float = Field(..., description="SBA guaranteed portion", examples=[187500.0])
    terminmonths: int = Field(..., description="Loan term in months", examples=[120])
    initialinterestrate: float = Field(..., description="Interest rate", examples=[7.5])
    jobssupported: int = Field(..., description="Number of jobs supported", examples=[10])
    bank_prior_def_rate: float = Field(..., description="Lender historical default rate", examples=[0.08])
    bank_prior_loans: float = Field(..., description="Lender historical loan volume", examples=[500.0])
    sector_historical_default_rate: float = Field(..., description="Industry sector historical default rate", examples=[0.087])
    naics_sector: str = Field(..., description="2-digit NAICS industry code", examples=["72"])
    businesstype: str = Field(..., description="Business structure type", examples=["CORPORATION"])
    business_age_group: str = Field(..., description="Business age category", examples=["Existing"])
    bank_experience_tier: str = Field(..., description="Lender experience category", examples=["High"])
    revolverstatus: int = Field(..., description="Is revolving line of credit (1/0)", examples=[0])
    is_same_state_bank: int = Field(..., description="Is lender in same state as borrower (1/0)", examples=[1])
    is_variable_rate: int = Field(..., description="Is variable interest rate (1/0)", examples=[1])
    is_franchise: int = Field(..., description="Is a franchise business (1/0)", examples=[0])
    collateralind: int = Field(..., description="Is collateral provided (1/0)", examples=[1])


class RiskAssessmentResponse(BaseModel):
    probability_of_default: float
    loss_given_default: float
    exposure_at_default: float
    expected_loss: float
    risk_tier: str
    underwriting_action: str

def assign_risk_tier(pd_score: float):
    if pd_score < 0.10:
        return "Tier 1", "🟢 Auto Approve"
    elif pd_score < 0.25:
        return "Tier 2", "🟡 Manual Review"
    elif pd_score < 0.40:
        return "Tier 3", "🟠 Senior Review"
    else:
        return "Tier 4", "🔴 Recommend Denial"
    
@router.post("/predict", response_model=RiskAssessmentResponse)
async def predict_risk(application: LoanApplication, auth_info: dict = Depends(verify_api_access)):
    data_dict = application.model_dump()

    data_dict['unguaranteed_exposure'] = data_dict['grossapproval'] - data_dict['sbaguaranteedapproval']
    data_dict['log_gross_approval'] = float(np.log1p(data_dict['grossapproval']))

    input_df = pd.DataFrame([data_dict])

    pd_score = float(MODEL.predict_proba(input_df)[:,1][0])

    lgd = data_dict['unguaranteed_exposure'] / data_dict['grossapproval']
    ead = data_dict['grossapproval']
    expected_loss = pd_score * lgd * ead
    tier_label, action = assign_risk_tier(pd_score)

    # Log to Supabase audit database if configured
    if supabase_client:
        try:
            username = auth_info.get("user", "API_KEY_USER")
            supabase_client.table("predictions").insert({
                "username": username,
                "loan_amount": float(ead),
                "term_months": int(data_dict['terminmonths']),
                "interest_rate": float(data_dict['initialinterestrate']),
                "probability_of_default": float(pd_score),
                "expected_loss": float(expected_loss),
                "risk_tier": tier_label
            }).execute()
            logger.info(f"Successfully logged prediction to Supabase for user: {username}")
        except Exception as e:
            logger.error(f"Failed to log prediction to Supabase: {e}")

    return {
        "probability_of_default": pd_score,
        "loss_given_default": lgd,
        "exposure_at_default": ead,
        "expected_loss": expected_loss,
        "risk_tier": tier_label,
        "underwriting_action": action
    }
