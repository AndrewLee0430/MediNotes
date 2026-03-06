"""
build_explain_cache.py
Pre-loads common LOINC, RxNorm, and MedlinePlus entries into cache.
Run once before deployment or periodically to warm up the cache.

Usage:
    python scripts/build_explain_cache.py

Estimated time: 3-5 minutes (rate-limited to respect NLM servers)
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.data_sources.loinc_client import loinc_client
from api.data_sources.rxnorm_client import rxnorm_client
from api.data_sources.medlineplus_client import medlineplus_client

# ============================================================
# Common Lab Tests (LOINC)
# Source: Most frequently ordered lab tests in primary care
# ============================================================
COMMON_LAB_TESTS = [
    # Kidney function
    "eGFR", "creatinine", "BUN", "uric acid", "cystatin C",
    # Blood sugar
    "HbA1c", "glucose", "fasting glucose", "insulin", "C-peptide",
    # Lipids
    "cholesterol", "LDL", "HDL", "triglycerides", "VLDL",
    # Liver function
    "ALT", "AST", "ALP", "bilirubin", "albumin", "GGT", "total protein",
    # Complete blood count
    "hemoglobin", "hematocrit", "WBC", "platelet", "RBC", "MCV", "MCH",
    # Thyroid
    "TSH", "T3", "T4", "free T4", "free T3",
    # Electrolytes
    "sodium", "potassium", "chloride", "bicarbonate", "calcium", "magnesium", "phosphorus",
    # Cardiac
    "troponin", "BNP", "NT-proBNP", "CK", "CK-MB", "LDH",
    # Inflammation
    "CRP", "ESR", "ferritin", "fibrinogen", "procalcitonin",
    # Vitamins & minerals
    "vitamin D", "vitamin B12", "folate", "iron", "TIBC", "transferrin",
    # Urine
    "urinalysis", "urine protein", "urine albumin", "urine creatinine", "urine glucose",
    # Hormones
    "cortisol", "ACTH", "PTH", "testosterone", "estradiol", "FSH", "LH", "prolactin",
    # Other
    "PSA", "CEA", "CA-125", "AFP", "beta-HCG", "HIV", "HbsAg",
]

# ============================================================
# Common Medications (RxNorm + MedlinePlus)
# Source: Top 200 prescribed drugs
# ============================================================
COMMON_MEDICATIONS = [
    # Diabetes
    "Metformin", "Insulin", "Glipizide", "Sitagliptin", "Empagliflozin",
    "Liraglutide", "Dapagliflozin", "Pioglitazone", "Glimepiride", "Saxagliptin",
    # Cardiovascular
    "Lisinopril", "Amlodipine", "Metoprolol", "Atorvastatin", "Simvastatin",
    "Losartan", "Carvedilol", "Bisoprolol", "Valsartan", "Ramipril",
    "Furosemide", "Spironolactone", "Hydrochlorothiazide", "Digoxin", "Warfarin",
    "Aspirin", "Clopidogrel", "Rivaroxaban", "Apixaban", "Rosuvastatin",
    # Pain & Inflammation
    "Ibuprofen", "Acetaminophen", "Naproxen", "Celecoxib", "Tramadol",
    "Gabapentin", "Pregabalin", "Morphine", "Oxycodone", "Meloxicam",
    # Antibiotics
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Doxycycline", "Metronidazole",
    "Clarithromycin", "Cephalexin", "Trimethoprim", "Nitrofurantoin", "Levofloxacin",
    # Mental health
    "Sertraline", "Fluoxetine", "Escitalopram", "Venlafaxine", "Bupropion",
    "Mirtazapine", "Quetiapine", "Olanzapine", "Risperidone", "Aripiprazole",
    "Alprazolam", "Lorazepam", "Diazepam", "Clonazepam", "Zolpidem",
    # Respiratory
    "Albuterol", "Salbutamol", "Fluticasone", "Budesonide", "Montelukast",
    "Tiotropium", "Salmeterol", "Ipratropium", "Prednisone", "Prednisolone",
    # GI
    "Omeprazole", "Pantoprazole", "Lansoprazole", "Ranitidine", "Metoclopramide",
    "Ondansetron", "Loperamide", "Mesalazine", "Domperidone",
    # Thyroid
    "Levothyroxine", "Methimazole", "Propylthiouracil",
    # Other
    "Allopurinol", "Colchicine", "Hydroxychloroquine", "Tamoxifen",
    "Finasteride", "Sildenafil", "Tadalafil",
]

# ============================================================
# Common Diagnoses (MedlinePlus)
# ============================================================
COMMON_DIAGNOSES = [
    "diabetes mellitus", "hypertension", "chronic kidney disease",
    "heart failure", "atrial fibrillation", "coronary artery disease",
    "hypothyroidism", "hyperthyroidism", "asthma", "COPD",
    "depression", "anxiety", "osteoporosis", "osteoarthritis",
    "rheumatoid arthritis", "gout", "anemia", "hyperlipidemia",
    "obesity", "metabolic syndrome", "stroke", "epilepsy",
    "Alzheimer's disease", "Parkinson's disease", "multiple sclerosis",
]


async def warm_loinc(delay: float = 0.3):
    """Pre-load LOINC cache for common lab tests."""
    print(f"\n{'='*50}")
    print(f"LOINC Cache Warm-up ({len(COMMON_LAB_TESTS)} terms)")
    print(f"{'='*50}")

    success, fail = 0, 0
    for i, term in enumerate(COMMON_LAB_TESTS, 1):
        try:
            result = await loinc_client.search(term)
            if result:
                print(f"  ✅ [{i:3d}/{len(COMMON_LAB_TESTS)}] {term:<25} → {result.get('loinc_num', 'N/A')}")
                success += 1
            else:
                print(f"  ⚠️  [{i:3d}/{len(COMMON_LAB_TESTS)}] {term:<25} → not found")
                fail += 1
        except Exception as e:
            print(f"  ❌ [{i:3d}/{len(COMMON_LAB_TESTS)}] {term:<25} → error: {e}")
            fail += 1

        await asyncio.sleep(delay)

    print(f"\nLOINC: {success} cached, {fail} failed")
    return success, fail


async def warm_rxnorm(delay: float = 0.3):
    """Pre-load RxNorm cache for common medications."""
    print(f"\n{'='*50}")
    print(f"RxNorm Cache Warm-up ({len(COMMON_MEDICATIONS)} medications)")
    print(f"{'='*50}")

    success, fail = 0, 0
    for i, med in enumerate(COMMON_MEDICATIONS, 1):
        try:
            rxcui = await rxnorm_client.get_rxcui(med)
            if rxcui:
                print(f"  ✅ [{i:3d}/{len(COMMON_MEDICATIONS)}] {med:<30} → RXCUI {rxcui}")
                success += 1
            else:
                print(f"  ⚠️  [{i:3d}/{len(COMMON_MEDICATIONS)}] {med:<30} → not found")
                fail += 1
        except Exception as e:
            print(f"  ❌ [{i:3d}/{len(COMMON_MEDICATIONS)}] {med:<30} → error: {e}")
            fail += 1

        await asyncio.sleep(delay)

    print(f"\nRxNorm: {success} cached, {fail} failed")
    return success, fail


async def warm_medlineplus(delay: float = 0.5):
    """Pre-load MedlinePlus cache for common medications and diagnoses."""
    terms = COMMON_MEDICATIONS[:50] + COMMON_DIAGNOSES  # Limit to top 50 meds + all diagnoses
    print(f"\n{'='*50}")
    print(f"MedlinePlus Cache Warm-up ({len(terms)} terms)")
    print(f"{'='*50}")

    success, fail = 0, 0
    for i, term in enumerate(terms, 1):
        try:
            result = await medlineplus_client.get_drug_info(term)
            if result:
                print(f"  ✅ [{i:3d}/{len(terms)}] {term:<35} → found")
                success += 1
            else:
                print(f"  ⚠️  [{i:3d}/{len(terms)}] {term:<35} → not found")
                fail += 1
        except Exception as e:
            print(f"  ❌ [{i:3d}/{len(terms)}] {term:<35} → error: {e}")
            fail += 1

        await asyncio.sleep(delay)

    print(f"\nMedlinePlus: {success} cached, {fail} failed")
    return success, fail


async def main():
    start = time.time()
    print("🚀 Vela Explain Cache Builder")
    print("Pre-loading common medical terms to speed up first-query response times.")
    print(f"Estimated time: 3-5 minutes\n")

    # Run all three in sequence (not parallel, to respect rate limits)
    loinc_ok, loinc_fail   = await warm_loinc(delay=0.3)
    rxnorm_ok, rxnorm_fail = await warm_rxnorm(delay=0.3)
    ml_ok, ml_fail         = await warm_medlineplus(delay=0.5)

    elapsed = int(time.time() - start)
    total_ok   = loinc_ok + rxnorm_ok + ml_ok
    total_fail = loinc_fail + rxnorm_fail + ml_fail

    print(f"\n{'='*50}")
    print(f"Cache Build Complete — {elapsed}s")
    print(f"{'='*50}")
    print(f"  LOINC:       {loinc_ok:3d} cached, {loinc_fail:3d} failed")
    print(f"  RxNorm:      {rxnorm_ok:3d} cached, {rxnorm_fail:3d} failed")
    print(f"  MedlinePlus: {ml_ok:3d} cached, {ml_fail:3d} failed")
    print(f"  Total:       {total_ok:3d} cached, {total_fail:3d} failed")
    print(f"\n✅ Cache is ready. First-query response times will be significantly faster.")


if __name__ == "__main__":
    asyncio.run(main())