import joblib
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.dependencies import verify_api_access


router = APIRouter(tags=["Predictions"])

MODEL = joblib.load(settings.MODEL_PATH)

class LoanApplication(BaseModel):
    grossapproval: float = Field(..., description= "Gross approved loan amount", examples=250000.0)
    sbaguaranteedapproval: float = Field(..., description="SBA guaranteed portion", example=187500.0)
    terminmonths: int = Field(..., description="Loan term in months", example=120)
    initialinterestrate: float = Field(..., description="Interest rate", example=7.5)
    jobssupported: int = Field(..., description="Number of jobs supported", example=10)
    bank_prior_def_rate: float = Field(..., description="Lender historical default rate", example=0.08)
    bank_prior_loans: float = Field(..., description="Lender historical loan volume", example=500.0)
    sector_historical_default_rate: float = Field(..., description="Industry sector historical default rate", example=0.087)
    naics_sector: str = Field(..., description="2-digit NAICS industry code", example="72")
    businesstype: str = Field(..., description="Business structure type", example="CORPORATION")
    business_age_group: str = Field(..., description="Business age category", example="Existing")
    bank_experience_tier: str = Field(..., description="Lender experience category", example="High")
    revolverstatus: int = Field(..., description="Is revolving line of credit (1/0)", example=0)
    is_same_state_bank: int = Field(..., description="Is lender in same state as borrower (1/0)", example=1)
    is_variable_rate: int = Field(..., description="Is variable interest rate (1/0)", example=1)
    is_franchise: int = Field(..., description="Is a franchise business (1/0)", example=0)
    collateralind: int = Field(..., description="Is collateral provided (1/0)", example=1)


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
    
@router.post("/predict", response_model=RiskAssessmentResponse, dependencies=[Depends(verify_api_access)])
async def predict_risk(application: LoanApplication):
    data_dict = application.model_dump()

    data_dict['unguaranteed_exposure'] = data_dict['grossapproval'] - data_dict['sbaguaranteedapproval']
    data_dict['log_gross_approval'] = float(np.log1p(data_dict['grossapproval']))

    input_df = pd.DataFrame([data_dict])

    pd_score = float(Model.predict_proba(input_df)[:,1][0])

    lgd = data_dict['unguaranteed_exposure'] / data_dict['grossapproval']

    ead = data_dict['grossapproval']

    expected_loss = pd_score * lgd * ead
    tier_label, action = assign_risk_tier(pd_score)

    return {
        "probability_of_default": pd_score,
        "loss_given_default": lgd,
        "exposure_at_default": ead,
        "expected_loss": expected_loss,
        "risk_tier": tier_label,
        "underwriting_action": action
    }
