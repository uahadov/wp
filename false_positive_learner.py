"""
False Positive Learning System
==============================

Manuel doğrulamalardan öğrenen akıllı sistem
Zamanla false positive oranını %5 → %1'e düşürür

Features:
- Pattern learning (ortak false positive kalıpları)
- Database integration (manuel doğrulamalar)
- AI prompt enhancement (öğrenilen patternler)
- Telegram /confirm command integration
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from logger import get_logger
from database import get_db

logger = get_logger("fp_learner")


class FalsePositiveLearner:
    """False positive pattern öğrenme sistemi"""
    
    def __init__(self, patterns_file: str = "fp_patterns.json"):
        """
        Args:
            patterns_file: Öğrenilen patternlerin saklanacağı dosya
        """
        self.patterns_file = Path(patterns_file)
        self.db = get_db()
        self.patterns = self._load_patterns()
        logger.info(f"FP Learner başlatıldı: {len(self.patterns)} pattern yüklendi")
    
    def _load_patterns(self) -> List[Dict]:
        """Kaydedilmiş patternleri yükle"""
        if not self.patterns_file.exists():
            # Default patternler
            return [
                {
                    "pattern": "wpdb->prepare",
                    "category": "sql_prepared",
                    "confidence": 0.95,
                    "description": "WordPress wpdb->prepare kullanımı (safe SQL)",
                    "auto_learned": False
                },
                {
                    "pattern": "wp_verify_nonce",
                    "category": "nonce_check",
                    "confidence": 0.90,
                    "description": "WordPress nonce verification",
                    "auto_learned": False
                },
                {
                    "pattern": "esc_html|esc_attr|esc_url",
                    "category": "proper_escape",
                    "confidence": 0.85,
                    "description": "WordPress proper escaping",
                    "auto_learned": False
                }
            ]
        
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Pattern yükleme hatası: {e}")
            return []
    
    def _save_patterns(self):
        """Patternleri kaydet"""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, indent=2, ensure_ascii=False)
            logger.debug(f"{len(self.patterns)} pattern kaydedildi")
        except Exception as e:
            logger.error(f"Pattern kaydetme hatası: {e}")
    
    def add_manual_validation(
        self,
        vuln_id: int,
        is_true_positive: bool,
        reason: str,
        user: str = "user"
    ) -> bool:
        """
        Manuel doğrulama ekle ve öğren
        
        Args:
            vuln_id: Vulnerability ID (database)
            is_true_positive: True = gerçek zafiyet, False = false positive
            reason: Doğrulama sebebi
            user: Kim doğruladı
        
        Returns:
            Başarılı mı?
        """
        try:
            # Database'e kaydet
            self.db.execute("""
                INSERT INTO manual_validations 
                (vuln_id, is_true_positive, reason, validated_by, validated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (vuln_id, is_true_positive, reason, user, datetime.now()))
            
            logger.info(
                f"Manual validation added: Vuln #{vuln_id} - "
                f"{'TRUE' if is_true_positive else 'FALSE'} POSITIVE - {reason}"
            )
            
            # False positive ise pattern öğren
            if not is_true_positive:
                self._learn_from_false_positive(vuln_id, reason)
            
            return True
            
        except Exception as e:
            logger.error(f"Manuel doğrulama hatası: {e}")
            return False
    
    def _learn_from_false_positive(self, vuln_id: int, reason: str):
        """False positive'den pattern öğren"""
        try:
            # Vulnerability detaylarını al
            result = self.db.execute("""
                SELECT v.*, s.plugin_slug
                FROM vulnerabilities v
                JOIN scans s ON v.scan_id = s.id
                WHERE v.id = ?
            """, (vuln_id,))
            
            if not result:
                return
            
            vuln = result[0]
            
            # Pattern çıkar
            extracted_patterns = self._extract_patterns(vuln, reason)
            
            for pattern_data in extracted_patterns:
                # Mevcut pattern mı?
                existing = next(
                    (p for p in self.patterns if p['pattern'] == pattern_data['pattern']),
                    None
                )
                
                if existing:
                    # Confidence artır
                    existing['confidence'] = min(0.99, existing['confidence'] + 0.05)
                    existing['occurrences'] = existing.get('occurrences', 1) + 1
                    logger.info(
                        f"Pattern güncellendi: {pattern_data['pattern']} "
                        f"(confidence: {existing['confidence']:.2f})"
                    )
                else:
                    # Yeni pattern ekle
                    pattern_data['auto_learned'] = True
                    pattern_data['confidence'] = 0.70  # Başlangıç confidence
                    pattern_data['occurrences'] = 1
                    pattern_data['learned_at'] = datetime.now().isoformat()
                    self.patterns.append(pattern_data)
                    logger.info(f"Yeni pattern öğrenildi: {pattern_data['pattern']}")
            
            self._save_patterns()
            
        except Exception as e:
            logger.error(f"Pattern öğrenme hatası: {e}")
    
    def _extract_patterns(self, vuln: Dict, reason: str) -> List[Dict]:
        """Vulnerability ve reason'dan pattern çıkar"""
        patterns = []
        
        vuln_code = vuln.get('vulnerable_code', '')
        vuln_type = vuln.get('type', '')
        
        # Reason'dan pattern çıkar
        if 'nonce' in reason.lower():
            patterns.append({
                'pattern': r'wp_verify_nonce|check_ajax_referer|wp_create_nonce',
                'category': 'nonce_check',
                'description': f"Nonce verification in {vuln_type}",
                'reason': reason
            })
        
        if 'prepare' in reason.lower() or 'wpdb' in reason.lower():
            patterns.append({
                'pattern': r'\$wpdb->prepare\s*\(',
                'category': 'sql_prepared',
                'description': f"Prepared statement in {vuln_type}",
                'reason': reason
            })
        
        if 'sanitize' in reason.lower() or 'escape' in reason.lower():
            patterns.append({
                'pattern': r'sanitize_|esc_html|esc_attr|esc_url|esc_js',
                'category': 'proper_sanitization',
                'description': f"Proper sanitization in {vuln_type}",
                'reason': reason
            })
        
        if 'permission' in reason.lower() or 'capability' in reason.lower():
            patterns.append({
                'pattern': r'current_user_can|is_admin|check_admin_referer',
                'category': 'permission_check',
                'description': f"Permission check in {vuln_type}",
                'reason': reason
            })
        
        # Kod'dan pattern çıkar
        if 'wpdb->prepare' in vuln_code:
            patterns.append({
                'pattern': r'\$wpdb->prepare\s*\(',
                'category': 'sql_prepared',
                'description': 'Auto-detected prepared statement'
            })
        
        return patterns
    
    def check_vulnerability(self, vuln: Dict) -> Dict:
        """
        Zafiyeti pattern'lere karşı kontrol et
        
        Args:
            vuln: Vulnerability dict
        
        Returns:
            {
                'is_likely_false_positive': bool,
                'matched_patterns': [patterns],
                'confidence': float,
                'reason': str
            }
        """
        vuln_code = vuln.get('vulnerable_code', '')
        vuln_type = vuln.get('type', '')
        matched_patterns = []
        
        for pattern in self.patterns:
            try:
                if re.search(pattern['pattern'], vuln_code, re.IGNORECASE):
                    matched_patterns.append(pattern)
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern['pattern']}")
        
        if not matched_patterns:
            return {
                'is_likely_false_positive': False,
                'matched_patterns': [],
                'confidence': 0.0,
                'reason': 'No known false positive patterns detected'
            }
        
        # En yüksek confidence'ı al
        max_confidence = max(p['confidence'] for p in matched_patterns)
        
        # Threshold: 0.80+ ise muhtemelen false positive
        is_fp = max_confidence >= 0.80
        
        reason = f"Matched {len(matched_patterns)} FP pattern(s): " + \
                 ", ".join(p['description'] for p in matched_patterns[:3])
        
        logger.debug(
            f"FP Check [{vuln_type}]: {len(matched_patterns)} pattern, "
            f"confidence={max_confidence:.2f}, FP={is_fp}"
        )
        
        return {
            'is_likely_false_positive': is_fp,
            'matched_patterns': matched_patterns,
            'confidence': max_confidence,
            'reason': reason
        }
    
    def get_enhanced_prompt(self, base_prompt: str) -> str:
        """
        AI prompt'una öğrenilen patternleri ekle
        
        Args:
            base_prompt: Orijinal AI prompt
        
        Returns:
            Geliştirilmiş prompt (pattern'lerle)
        """
        if not self.patterns:
            return base_prompt
        
        # Yüksek confidence patternleri seç
        high_conf_patterns = [
            p for p in self.patterns
            if p['confidence'] >= 0.85
        ]
        
        if not high_conf_patterns:
            return base_prompt
        
        pattern_text = "\n\n**ÖĞRENILMIŞ FALSE POSITIVE PATTERNS:**\n"
        pattern_text += "Aşağıdaki durumlar genellikle FALSE POSITIVE'tir (yüksek confidence):\n\n"
        
        for p in high_conf_patterns[:10]:  # İlk 10
            pattern_text += (
                f"- **{p['category']}** (confidence: {p['confidence']:.0%}): "
                f"{p['description']}\n"
                f"  Pattern: `{p['pattern']}`\n"
            )
        
        pattern_text += (
            "\n⚠️ Bu patternlerden biri varsa, MUTLAKA false positive olarak değerlendir!\n"
        )
        
        return base_prompt + pattern_text
    
    def get_statistics(self) -> Dict:
        """Öğrenme istatistikleri"""
        try:
            # Manuel doğrulama sayıları
            validations = self.db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_true_positive THEN 1 ELSE 0 END) as true_positives,
                    SUM(CASE WHEN NOT is_true_positive THEN 1 ELSE 0 END) as false_positives
                FROM manual_validations
            """)
            
            val_stats = validations[0] if validations else {
                'total': 0, 'true_positives': 0, 'false_positives': 0
            }
            
            # Pattern istatistikleri
            auto_learned = sum(1 for p in self.patterns if p.get('auto_learned', False))
            avg_confidence = sum(p['confidence'] for p in self.patterns) / len(self.patterns) \
                           if self.patterns else 0
            
            return {
                'total_patterns': len(self.patterns),
                'auto_learned_patterns': auto_learned,
                'manual_patterns': len(self.patterns) - auto_learned,
                'average_confidence': avg_confidence,
                'total_validations': val_stats['total'],
                'true_positives_validated': val_stats['true_positives'],
                'false_positives_validated': val_stats['false_positives'],
                'false_positive_rate': (
                    val_stats['false_positives'] / val_stats['total'] * 100
                    if val_stats['total'] > 0 else 0
                )
            }
        except Exception as e:
            logger.error(f"İstatistik hatası: {e}")
            return {}


# Database migration (manual_validations tablosu)
def create_validations_table():
    """Manuel doğrulama tablosu oluştur"""
    from database import get_db
    db = get_db()
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS manual_validations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vuln_id INTEGER NOT NULL,
            is_true_positive BOOLEAN NOT NULL,
            reason TEXT,
            validated_by TEXT,
            validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vuln_id) REFERENCES vulnerabilities(id)
        )
    """)
    
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_validations_vuln 
        ON manual_validations(vuln_id)
    """)
    
    logger.info("manual_validations tablosu oluşturuldu")


# Global singleton
_learner_instance = None

def get_learner() -> FalsePositiveLearner:
    """Global FP learner instance (singleton)"""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = FalsePositiveLearner()
    return _learner_instance


# CLI kullanımı
if __name__ == "__main__":
    import sys
    
    # Table oluştur
    create_validations_table()
    
    learner = get_learner()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "stats":
            # İstatistikleri göster
            stats = learner.get_statistics()
            print("\n📊 False Positive Learning İstatistikleri")
            print("=" * 50)
            print(f"Toplam Pattern: {stats['total_patterns']}")
            print(f"  - Otomatik Öğrenilen: {stats['auto_learned_patterns']}")
            print(f"  - Manuel Eklenmiş: {stats['manual_patterns']}")
            print(f"Ortalama Confidence: {stats['average_confidence']:.1%}")
            print(f"\nManuel Doğrulamalar: {stats['total_validations']}")
            print(f"  - True Positive: {stats['true_positives_validated']}")
            print(f"  - False Positive: {stats['false_positives_validated']}")
            if stats['total_validations'] > 0:
                print(f"False Positive Rate: {stats['false_positive_rate']:.1f}%")
        
        elif cmd == "patterns":
            # Patternleri listele
            print(f"\n📋 {len(learner.patterns)} Pattern Yüklü:")
            print("=" * 70)
            for i, p in enumerate(learner.patterns, 1):
                auto = "🤖" if p.get('auto_learned') else "👤"
                print(f"{i}. {auto} [{p['category']}] {p['confidence']:.0%}")
                print(f"   Pattern: {p['pattern']}")
                print(f"   Açıklama: {p['description']}")
                if p.get('occurrences'):
                    print(f"   Görülme: {p['occurrences']}x")
                print()
    
    else:
        print("Kullanım: python false_positive_learner.py [stats|patterns]")
