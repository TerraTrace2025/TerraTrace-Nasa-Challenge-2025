import os
import re
import glob
import json
import pandas as pd
import enum
from datetime import date, timedelta

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI


# ----------------------------
# Models
# ----------------------------
class AlertType(str, enum.Enum):
    critical = "critical"
    risk = "risk"
    stable = "stable"
    surplus = "surplus"


from dotenv import load_dotenv

# load .env variables
load_dotenv()

class CropType(str, enum.Enum):
    rapeseed = "rapeseed"
    soybean = "soybean"
    wheat = "wheat"
    corn = "corn"
    barley = "barley"
    sunflowerseed = "sunflowerseed"


def classify_alert(relative_diff: float) -> AlertType:
    """Map relative difference to an AlertType"""
    if relative_diff < -0.1:
        return AlertType.critical
    elif -0.1 <= relative_diff < 0:
        return AlertType.risk
    elif 0 <= relative_diff < 0.1:
        return AlertType.stable
    else:
        return AlertType.surplus


# ----------------------------
# LLM Setup
# ----------------------------
prompt_template = """
You are a supply-chain optimization assistant.
Your goal is to ensure food demand is covered while **minimizing food waste**. However costs are the most important factor
and that the alternative is close (not completly on the other side of switzerland). And also that the alternative farmer
has a positive diff (good chance of surplus).

You are given:
- Product: {product}
- Current Farmer Situation: {current}
- Available Suppliers: {suppliers}

Rules:
1. Always recommend exactly 3 alternative suppliers.
2. Prioritize suppliers whose expiry dates are soonest (to reduce waste).
3. Prefer reasonable price, but reducing food waste is also important.
4. Alternative should be predicted to have a surplus.
5. Region should be close by.
6. Respond ONLY in JSON with the following structure:

{{
  "recommendations": [
    {{
      "supplier": "<Supplier Name>",
      "reasoning": "<1–3 short sentences explaining why this supplier is chosen, focusing on food waste reduction>"
    }},
    ...
  ]
}}

No extra commentary, just valid JSON.
"""

prompt = PromptTemplate(
    input_variables=["product", "current", "suppliers"],
    template=prompt_template
)

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
)

chain = LLMChain(llm=llm, prompt=prompt)


# ----------------------------
# Core Evaluation
# ----------------------------
def evaluate_and_update(df: pd.DataFrame, crop_type: str) -> pd.DataFrame:
    # prepare new columns
    df["recommendations"] = None

    for idx, row in df.iterrows():
        diff = row["diff"]
        alert = classify_alert(diff)

        if alert in [AlertType.critical, AlertType.risk]:
            current_farmer = {
                "standort": row["Standort"],
                "diff": float(diff),
                "price": float(row["price"]),
                "expiry_date": str(row["expiry_date"]),
            }

            # alternative suppliers
            suppliers_list = []
            for _, s in df.iterrows():
                if s["Standort"] != row["Standort"]:
                    suppliers_list.append({
                        "standort": s["Standort"],
                        "price": float(s["price"]),
                        "expiry_date": str(s["expiry_date"]),
                        "diff": float(s["diff"])
                    })

            # sort by expiry date
            suppliers_list = sorted(
                suppliers_list,
                key=lambda x: (x["expiry_date"])
            )

            # retry logic: try up to 2 times
            recs = None
            for attempt in range(2):
                response = chain.run(
                    product=crop_type,
                    current=current_farmer,
                    suppliers=suppliers_list[:10]
                )
                print(f"Attempt {attempt+1} response:", response)

                try:
                    recs = json.loads(response)
                    break  # success
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parse failed (attempt {attempt+1}):", e)

            if recs:
                df.at[idx, "recommendations"] = json.dumps(recs)
            else:
                df.at[idx, "recommendations"] = None

    return df



# ----------------------------
# Main Runner
# ----------------------------
def run_pipeline(data_folder="src/scripts/data"):
    for file in glob.glob(os.path.join(data_folder, "*_estimated_requested.csv")):
        crop_name = os.path.basename(file).replace("_estimated_requested.csv", "")
        crop_type = CropType(crop_name)

        df = pd.read_csv(file)

        if {"Standort", "estimated_yield", "requested_yield"}.issubset(df.columns):
            df = evaluate_and_update(df, crop_type.value)

            # save back with recommendations
            #out_file = file.replace("_estimated_requested.csv", "_with_alerts.csv")
            df.to_csv(file, index=False)
            print(f"✅ Saved enriched CSV: {file}")


if __name__ == "__main__":
    run_pipeline()
