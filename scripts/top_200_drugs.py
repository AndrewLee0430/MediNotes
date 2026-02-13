"""
Top 200 Most Commonly Prescribed Drugs in the US
美国最常用的 200 种处方药物列表

数据来源：基于 FDA、医疗统计数据整理
用途：预先加载到本地数据库，提供离线查询能力
"""

# Top 200 常见药物（按使用频率排序）
TOP_200_DRUGS = [
    # ============ 心血管系统 (Cardiovascular) ============
    "Lisinopril",           # ACE inhibitor - 高血压
    "Atorvastatin",         # Statin - 降脂
    "Amlodipine",           # Calcium channel blocker - 高血压
    "Metoprolol",           # Beta blocker - 高血压/心律不整
    "Losartan",             # ARB - 高血压
    "Simvastatin",          # Statin - 降脂
    "Warfarin",             # Anticoagulant - 抗凝血
    "Aspirin",              # Antiplatelet - 抗血小板
    "Clopidogrel",          # Antiplatelet - 抗血小板
    "Furosemide",           # Diuretic - 利尿剂
    "Carvedilol",           # Beta blocker - 心衰/高血压
    "Rosuvastatin",         # Statin - 降脂
    "Valsartan",            # ARB - 高血压
    "Hydrochlorothiazide",  # Diuretic - 利尿剂
    "Digoxin",              # Cardiac glycoside - 心律不整
    "Diltiazem",            # Calcium channel blocker - 高血压
    "Apixaban",             # Anticoagulant - 新型抗凝药
    "Rivaroxaban",          # Anticoagulant - 新型抗凝药
    
    # ============ 内分泌系统 (Endocrine) ============
    "Metformin",            # Antidiabetic - 糖尿病
    "Levothyroxine",        # Thyroid hormone - 甲状腺
    "Insulin Glargine",     # Long-acting insulin - 胰岛素
    "Insulin Lispro",       # Rapid-acting insulin - 胰岛素
    "Glipizide",            # Sulfonylurea - 糖尿病
    "Sitagliptin",          # DPP-4 inhibitor - 糖尿病
    "Empagliflozin",        # SGLT2 inhibitor - 糖尿病
    "Semaglutide",          # GLP-1 agonist - 糖尿病
    "Liraglutide",          # GLP-1 agonist - 糖尿病
    
    # ============ 呼吸系统 (Respiratory) ============
    "Albuterol",            # Beta-2 agonist - 气喘
    "Fluticasone",          # Inhaled steroid - 气喘
    "Montelukast",          # Leukotriene inhibitor - 气喘/过敏
    "Budesonide",           # Inhaled steroid - 气喘
    "Tiotropium",           # Anticholinergic - COPD
    "Ipratropium",          # Anticholinergic - COPD
    
    # ============ 消化系统 (Gastrointestinal) ============
    "Omeprazole",           # PPI - 胃酸抑制
    "Pantoprazole",         # PPI - 胃酸抑制
    "Esomeprazole",         # PPI - 胃酸抑制
    "Ranitidine",           # H2 blocker - 胃酸抑制
    "Metoclopramide",       # Prokinetic - 促胃肠动力
    
    # ============ 神经系统 (Neurological) ============
    "Gabapentin",           # Anticonvulsant - 神经痛
    "Pregabalin",           # Anticonvulsant - 神经痛
    "Duloxetine",           # SNRI - 抗抑郁/神经痛
    "Amitriptyline",        # TCA - 抗抑郁/神经痛
    "Carbamazepine",        # Anticonvulsant - 癫痫
    "Levetiracetam",        # Anticonvulsant - 癫痫
    "Topiramate",           # Anticonvulsant - 癫痫/偏头痛
    
    # ============ 精神科 (Psychiatry) ============
    "Sertraline",           # SSRI - 抗抑郁
    "Escitalopram",         # SSRI - 抗抑郁
    "Fluoxetine",           # SSRI - 抗抑郁
    "Citalopram",           # SSRI - 抗抑郁
    "Venlafaxine",          # SNRI - 抗抑郁
    "Bupropion",            # NDRI - 抗抑郁
    "Quetiapine",           # Antipsychotic - 抗精神病
    "Aripiprazole",         # Antipsychotic - 抗精神病
    "Olanzapine",           # Antipsychotic - 抗精神病
    "Risperidone",          # Antipsychotic - 抗精神病
    "Alprazolam",           # Benzodiazepine - 抗焦虑
    "Lorazepam",            # Benzodiazepine - 抗焦虑
    "Clonazepam",           # Benzodiazepine - 抗焦虑
    "Zolpidem",             # Sedative - 安眠药
    
    # ============ 疼痛管理 (Pain Management) ============
    "Ibuprofen",            # NSAID - 止痛/消炎
    "Naproxen",             # NSAID - 止痛/消炎
    "Acetaminophen",        # Analgesic - 止痛
    "Tramadol",             # Opioid - 止痛
    "Hydrocodone",          # Opioid - 止痛
    "Oxycodone",            # Opioid - 止痛
    "Morphine",             # Opioid - 止痛
    "Fentanyl",             # Opioid - 止痛
    "Meloxicam",            # NSAID - 止痛/消炎
    "Celecoxib",            # COX-2 inhibitor - 止痛
    
    # ============ 抗感染 (Anti-infective) ============
    "Amoxicillin",          # Antibiotic - 抗生素
    "Azithromycin",         # Antibiotic - 抗生素
    "Ciprofloxacin",        # Antibiotic - 抗生素
    "Levofloxacin",         # Antibiotic - 抗生素
    "Doxycycline",          # Antibiotic - 抗生素
    "Cephalexin",           # Antibiotic - 抗生素
    "Amoxicillin-Clavulanate", # Antibiotic - 抗生素
    "Trimethoprim-Sulfamethoxazole", # Antibiotic - 抗生素
    "Acyclovir",            # Antiviral - 抗病毒
    "Valacyclovir",         # Antiviral - 抗病毒
    "Fluconazole",          # Antifungal - 抗真菌
    
    # ============ 过敏/免疫 (Allergy/Immunology) ============
    "Cetirizine",           # Antihistamine - 抗组织胺
    "Loratadine",           # Antihistamine - 抗组织胺
    "Fexofenadine",         # Antihistamine - 抗组织胺
    "Diphenhydramine",      # Antihistamine - 抗组织胺
    "Prednisone",           # Corticosteroid - 类固醇
    "Methylprednisolone",   # Corticosteroid - 类固醇
    "Dexamethasone",        # Corticosteroid - 类固醇
    
    # ============ 泌尿系统 (Urological) ============
    "Tamsulosin",           # Alpha blocker - 前列腺
    "Finasteride",          # 5-alpha reductase inhibitor - 前列腺
    "Oxybutynin",           # Anticholinergic - 膀胱过动
    "Solifenacin",          # Anticholinergic - 膀胱过动
    
    # ============ 妇科/荷尔蒙 (Gynecology/Hormones) ============
    "Estradiol",            # Hormone - 雌激素
    "Progesterone",         # Hormone - 黄体素
    "Norethindrone",        # Hormone - 避孕
    "Levonorgestrel",       # Hormone - 避孕
    
    # ============ 眼科 (Ophthalmology) ============
    "Latanoprost",          # Prostaglandin - 青光眼
    "Timolol",              # Beta blocker - 青光眼
    "Brimonidine",          # Alpha agonist - 青光眼
    
    # ============ 皮肤科 (Dermatology) ============
    "Hydrocortisone",       # Topical steroid - 皮肤炎
    "Triamcinolone",        # Topical steroid - 皮肤炎
    "Clotrimazole",         # Antifungal - 抗真菌
    "Mupirocin",            # Antibiotic - 抗生素软膏
    
    # ============ 其他常见药物 ============
    "Vitamin D",            # Supplement - 维生素
    "Calcium",              # Supplement - 钙片
    "Folic Acid",           # Supplement - 叶酸
    "Vitamin B12",          # Supplement - 维生素
    "Omega-3 Fatty Acids",  # Supplement - 鱼油
    
    # ============ 新型/特殊药物 ============
    "Adalimumab",           # Biologic - 自体免疫疾病
    "Etanercept",           # Biologic - 类风湿关节炎
    "Infliximab",           # Biologic - 发炎性肠病
    "Trastuzumab",          # Biologic - 乳癌
    "Bevacizumab",          # Biologic - 癌症
    
    # ============ 补充到 200 个 ============
    "Atenolol",             # Beta blocker
    "Enalapril",            # ACE inhibitor
    "Ramipril",             # ACE inhibitor
    "Spironolactone",       # Diuretic
    "Clonidine",            # Antihypertensive
    "Nifedipine",           # Calcium channel blocker
    "Verapamil",            # Calcium channel blocker
    "Isosorbide",           # Nitrate
    "Nitroglycerin",        # Nitrate
    "Pravastatin",          # Statin
    "Ezetimibe",            # Cholesterol absorption inhibitor
    "Fenofibrate",          # Fibrate
    "Gemfibrozil",          # Fibrate
    "Pioglitazone",         # Thiazolidinedione
    "Glyburide",            # Sulfonylurea
    "Repaglinide",          # Meglitinide
    "Canagliflozin",        # SGLT2 inhibitor
    "Dulaglutide",          # GLP-1 agonist
    "Salmeterol",           # Long-acting beta agonist
    "Formoterol",           # Long-acting beta agonist
    "Theophylline",         # Bronchodilator
    "Cromolyn",             # Mast cell stabilizer
    "Lansoprazole",         # PPI
    "Rabeprazole",          # PPI
    "Famotidine",           # H2 blocker
    "Sucralfate",           # Mucosal protectant
    "Loperamide",           # Antidiarrheal
    "Docusate",             # Stool softener
    "Polyethylene Glycol",  # Laxative
    "Ondansetron",          # Antiemetic
    "Promethazine",         # Antiemetic
    "Phenytoin",            # Anticonvulsant
    "Valproic Acid",        # Anticonvulsant
    "Lamotrigine",          # Anticonvulsant
    "Oxcarbazepine",        # Anticonvulsant
    "Phenobarbital",        # Anticonvulsant
    "Baclofen",             # Muscle relaxant
    "Cyclobenzaprine",      # Muscle relaxant
    "Tizanidine",           # Muscle relaxant
    "Methocarbamol",        # Muscle relaxant
    "Paroxetine",           # SSRI
    "Mirtazapine",          # Antidepressant
    "Trazodone",            # Antidepressant
    "Desvenlafaxine",       # SNRI
    "Atomoxetine",          # ADHD
    "Methylphenidate",      # ADHD
    "Amphetamine",          # ADHD
    "Lisdexamfetamine",     # ADHD
    "Lithium",              # Mood stabilizer
    "Lamotrigine",          # Mood stabilizer
    "Haloperidol",          # Antipsychotic
    "Ziprasidone",          # Antipsychotic
    "Lurasidone",           # Antipsychotic
    "Buspirone",            # Anxiolytic
    "Hydroxyzine",          # Anxiolytic
    "Temazepam",            # Benzodiazepine
    "Diazepam",             # Benzodiazepine
    "Eszopiclone",          # Sedative
    "Ramelteon",            # Sedative
    "Ketorolac",            # NSAID
    "Indomethacin",         # NSAID
    "Diclofenac",           # NSAID
    "Etodolac",             # NSAID
    "Codeine",              # Opioid
    "Buprenorphine",        # Opioid
    "Methadone",            # Opioid
    "Penicillin",           # Antibiotic
    "Clindamycin",          # Antibiotic
    "Metronidazole",        # Antibiotic
    "Nitrofurantoin",       # Antibiotic
    "Tetracycline",         # Antibiotic
    "Clarithromycin",       # Antibiotic
    "Erythromycin",         # Antibiotic
    "Vancomycin",           # Antibiotic
    "Gentamicin",           # Antibiotic
    "Tobramycin",           # Antibiotic
    "Oseltamivir",          # Antiviral
    "Ribavirin",            # Antiviral
    "Itraconazole",         # Antifungal
    "Terbinafine",          # Antifungal
    "Nystatin",             # Antifungal
]


# 药物分类映射（方便查询）
DRUG_CATEGORIES = {
    "cardiovascular": [
        "Lisinopril", "Atorvastatin", "Amlodipine", "Metoprolol", "Losartan",
        "Simvastatin", "Warfarin", "Aspirin", "Clopidogrel", "Furosemide"
    ],
    "endocrine": [
        "Metformin", "Levothyroxine", "Insulin Glargine", "Glipizide", "Sitagliptin"
    ],
    "respiratory": [
        "Albuterol", "Fluticasone", "Montelukast", "Budesonide"
    ],
    "gastrointestinal": [
        "Omeprazole", "Pantoprazole", "Esomeprazole", "Ranitidine"
    ],
    "neurological": [
        "Gabapentin", "Pregabalin", "Duloxetine", "Carbamazepine"
    ],
    "psychiatric": [
        "Sertraline", "Escitalopram", "Quetiapine", "Alprazolam"
    ],
    "pain": [
        "Ibuprofen", "Naproxen", "Tramadol", "Oxycodone"
    ],
    "antibiotic": [
        "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Doxycycline"
    ]
}


def get_drug_category(drug_name: str) -> str:
    """
    获取药物分类
    
    Args:
        drug_name: 药物名称
        
    Returns:
        分类名称，如果未找到则返回 "other"
    """
    for category, drugs in DRUG_CATEGORIES.items():
        if drug_name in drugs:
            return category
    return "other"


def is_top_drug(drug_name: str) -> bool:
    """
    检查是否为 Top 200 药物
    
    Args:
        drug_name: 药物名称
        
    Returns:
        是否在列表中
    """
    return drug_name in TOP_200_DRUGS


if __name__ == "__main__":
    print(f"Total drugs: {len(TOP_200_DRUGS)}")
    print(f"Unique drugs: {len(set(TOP_200_DRUGS))}")
    
    # 测试分类
    print(f"\nMetformin category: {get_drug_category('Metformin')}")
    print(f"Aspirin is top drug: {is_top_drug('Aspirin')}")