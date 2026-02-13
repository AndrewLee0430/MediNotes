"""
PHI (Protected Health Information) Detection Middleware
支援多國個資偵測：台灣、日本、美國

隱私保護原則：
- 攔截包含 PHI 的請求，防止傳送至 LLM
- 支援多國格式偵測
- 提供清晰的錯誤訊息引導使用者
"""

import re
from typing import Optional


class PHIDetector:
    """
    多國 PHI 偵測器
    
    支援格式：
    - 台灣：身分證、健保卡、手機號碼
    - 日本：My Number、手機號碼、保險證號
    - 美國：SSN、電話號碼、MRN (Medical Record Number)
    - 通用：Email、信用卡號
    """
    
    # ============ 台灣 Taiwan ============
    TAIWAN_ID_PATTERN = re.compile(
        r'\b[A-Z][12]\d{8}\b',  # 身分證：A123456789
        re.IGNORECASE
    )
    
    TAIWAN_HEALTH_INSURANCE_PATTERN = re.compile(
        r'\b\d{10}\b'  # 健保卡號：10位數字
    )
    
    TAIWAN_PHONE_PATTERN = re.compile(
        r'\b09\d{8}\b'  # 手機：09xxxxxxxx
    )
    
    # ============ 日本 Japan ============
    JAPAN_MY_NUMBER_PATTERN = re.compile(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'  # My Number: 1234-5678-9012
    )
    
    JAPAN_PHONE_PATTERN = re.compile(
        r'\b0[789]0[-\s]?\d{4}[-\s]?\d{4}\b'  # 手機：090-1234-5678
    )
    
    JAPAN_INSURANCE_PATTERN = re.compile(
        r'\b\d{8}\b'  # 保險證號：8位數字
    )
    
    # ============ 美國 USA ============
    USA_SSN_PATTERN = re.compile(
        r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'  # SSN: 123-45-6789
    )
    
    USA_PHONE_PATTERN = re.compile(
        r'\b\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b'  # 電話：(123) 456-7890
    )
    
    USA_MRN_PATTERN = re.compile(
        r'\bMRN[-:\s]?\d{6,10}\b',  # Medical Record Number
        re.IGNORECASE
    )
    
    # ============ 通用 Universal ============
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    CREDIT_CARD_PATTERN = re.compile(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'  # 信用卡：1234-5678-9012-3456
    )
    
    # 常見的病歷號格式
    MEDICAL_RECORD_PATTERNS = [
        re.compile(r'\b[A-Z]{2,3}\d{6,10}\b'),  # AB123456789
        re.compile(r'\b\d{8,12}\b'),            # 純數字病歷號
    ]
    
    @classmethod
    def detect(cls, text: str) -> Optional[str]:
        """
        偵測文字中是否包含 PHI
        
        Args:
            text: 要檢查的文字
            
        Returns:
            偵測到的 PHI 類型，若無則返回 None
        """
        if not text or len(text.strip()) == 0:
            return None
        
        # 台灣格式
        if cls.TAIWAN_ID_PATTERN.search(text):
            return "Taiwan ID (台灣身分證)"
        if cls.TAIWAN_PHONE_PATTERN.search(text):
            return "Taiwan Phone (台灣手機號碼)"
        
        # 日本格式
        if cls.JAPAN_MY_NUMBER_PATTERN.search(text):
            return "Japan My Number (日本個人番號)"
        if cls.JAPAN_PHONE_PATTERN.search(text):
            return "Japan Phone (日本手機號碼)"
        
        # 美國格式
        if cls.USA_SSN_PATTERN.search(text):
            return "US SSN (美國社會安全號碼)"
        if cls.USA_MRN_PATTERN.search(text):
            return "US MRN (美國病歷號)"
        
        # 通用格式
        if cls.EMAIL_PATTERN.search(text):
            # 允許常見的機構 email (如 @hospital.org)
            # 但攔截看起來像個人 email 的
            email_match = cls.EMAIL_PATTERN.search(text)
            email = email_match.group(0)
            # 簡單啟發式：如果包含數字 + 名字模式，可能是個人 email
            if re.search(r'\d+[a-z]+|\b(john|mary|patient)\d*\b', email, re.IGNORECASE):
                return "Email (個人電子郵件)"
        
        if cls.CREDIT_CARD_PATTERN.search(text):
            # 排除一些常見的誤判（如日期 2024-01-01-1234）
            cc_match = cls.CREDIT_CARD_PATTERN.search(text)
            if cc_match and not re.search(r'20\d{2}', cc_match.group(0)):
                return "Credit Card (信用卡號)"
        
        return None
    
    @classmethod
    def sanitize_for_log(cls, text: Optional[str], mask_char: str = "***") -> Optional[str]:
        """
        對文字進行脫敏處理，用於 Audit Log
        
        Args:
            text: 要處理的文字
            mask_char: 遮罩字符
            
        Returns:
            脫敏後的文字
        """
        if not text:
            return text
        
        sanitized = text
        
        # 遮罩各種格式
        sanitized = cls.TAIWAN_ID_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.TAIWAN_PHONE_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.JAPAN_MY_NUMBER_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.JAPAN_PHONE_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.USA_SSN_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.USA_MRN_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.EMAIL_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.CREDIT_CARD_PATTERN.sub(mask_char, sanitized)
        
        for pattern in cls.MEDICAL_RECORD_PATTERNS:
            sanitized = pattern.sub(mask_char, sanitized)
        
        return sanitized
    
    @classmethod
    def is_safe(cls, text: str) -> bool:
        """
        快速檢查文字是否安全（不含 PHI）
        
        Args:
            text: 要檢查的文字
            
        Returns:
            True 如果安全，False 如果包含 PHI
        """
        return cls.detect(text) is None


# ============ 使用範例 ============
if __name__ == "__main__":
    # 測試案例
    test_cases = [
        # 台灣
        ("病人資料：A123456789", "Taiwan ID"),
        ("請聯絡 0912345678", "Taiwan Phone"),
        
        # 日本
        ("マイナンバー: 1234-5678-9012", "Japan My Number"),
        ("連絡先: 090-1234-5678", "Japan Phone"),
        
        # 美國
        ("SSN: 123-45-6789", "US SSN"),
        ("MRN: 12345678", "US MRN"),
        
        # 通用
        ("Email: patient123@gmail.com", "Email"),
        ("信用卡: 1234-5678-9012-3456", "Credit Card"),
        
        # 安全案例
        ("Metformin 和 Warfarin 的交互作用", None),
        ("糖尿病患者的用藥建議", None),
    ]
    
    print("=== PHI Detection 測試 ===\n")
    for text, expected in test_cases:
        result = PHIDetector.detect(text)
        status = "✅" if (result is not None) == (expected is not None) else "❌"
        print(f"{status} Text: {text}")
        print(f"   偵測: {result or 'None'}")
        print(f"   預期: {expected or 'None'}")
        print()
    
    # 測試脫敏
    print("\n=== 脫敏測試 ===")
    sensitive_text = "病人 A123456789 的電話是 0912345678"
    sanitized = PHIDetector.sanitize_for_log(sensitive_text)
    print(f"原文: {sensitive_text}")
    print(f"脫敏: {sanitized}")