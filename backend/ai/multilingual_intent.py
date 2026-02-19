"""
Valora AI - Multilingual Intent Detection

Supports intent detection in Hindi, Kannada, Tamil.
Uses transliteration for location names.
Maps regional language patterns to intents.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("valora.multilingual")


class SupportedLanguage(Enum):
    """Supported languages for intent detection."""
    ENGLISH = 'en'
    HINDI = 'hi'
    KANNADA = 'kn'
    TAMIL = 'ta'
    TELUGU = 'te'
    MALAYALAM = 'ml'


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: SupportedLanguage
    confidence: float
    is_transliterated: bool = False
    original_text: str = ""
    normalized_text: str = ""


# Language patterns for intent detection
LANGUAGE_PATTERNS = {
    'hi': {  # Hindi
        'investment': [
            'निवेश', 'invest', 'पैसा लगाना', 'निवेश करना', 
            'invest करना', 'पैसे लगाना', 'मुनाफा'
        ],
        'price': [
            'कीमत', 'भाव', 'rate', 'दाम', 'मूल्य',
            'कितने का', 'कितना पैसा'
        ],
        'area_info': [
            'क्षेत्र', 'इलाका', 'जगह', 'एरिया', 'इलाके में',
            'यहाँ', 'वहाँ', 'कैसा इलाका'
        ],
        'comparison': [
            'तुलना', 'compare', 'बेहतर', 'अच्छा', 'से बेहतर',
            'कौन सा अच्छा', 'फर्क'
        ],
        'amenities': [
            'सुविधाएं', 'स्कूल', 'अस्पताल', 'हॉस्पिटल',
            'बाजार', 'दुकान', 'पार्क', 'मेट्रो'
        ],
        'safety': [
            'सुरक्षित', 'सेफ', 'सुरक्षा', 'खतरनाक',
            'सुरक्षित है', 'असुरक्षित'
        ],
        'greeting': [
            'नमस्ते', 'नमस्कार', 'हैलो', 'सत् श्री अकाल',
            'आदाब', 'प्रणाम'
        ],
        'thanks': [
            'धन्यवाद', 'शुक्रिया', 'थैंक्स', 'थैंक यू'
        ],
    },
    'kn': {  # Kannada
        'investment': [
            'ಹೂಡಿಕೆ', 'ಬಂಡವಾಳ', 'ಹಣ ಹೂಡುವುದು',
            'invest', 'ಲಾಭ', 'ಮುನ್ನೋಟ'
        ],
        'price': [
            'ಬೆಲೆ', 'ದರ', 'ರೇಟ್', 'ಎಷ್ಟು',
            'ಬೆಲೆ ಎಷ್ಟು', 'ಮೌಲ್ಯ'
        ],
        'area_info': [
            'ಪ್ರದೇಶ', 'ಜಾಗ', 'ಏರಿಯಾ', 'ಸ್ಥಳ',
            'ಇಲ್ಲಿ', 'ಅಲ್ಲಿ', 'ಹೇಗಿದೆ'
        ],
        'comparison': [
            'ಹೋಲಿಕೆ', 'compare', 'ಯಾವುದು ಒಳ್ಳೆಯದು',
            'ವ್ಯತ್ಯಾಸ', 'ಹೆಚ್ಚು ಒಳ್ಳೆಯದು'
        ],
        'amenities': [
            'ಸೌಲಭ್ಯಗಳು', 'ಶಾಲೆ', 'ಆಸ್ಪತ್ರೆ', 'ಆಸ್ಪತ್ರೆ',
            'ಮಾರುಕಟ್ಟೆ', 'ಪಾರ್ಕ್', 'ಮೆಟ್ರೋ'
        ],
        'safety': [
            'ಸುರಕ್ಷಿತ', 'ಸೇಫ್', 'ಸುರಕ್ಷತೆ',
            'ಅಪಾಯಕಾರಿ', 'ಭದ್ರತೆ'
        ],
        'greeting': [
            'ನಮಸ್ಕಾರ', 'ಹಲೋ', 'ನಮಸ್ಕಾರಗಳು',
            'ಶುಭೋದಯ', 'ಶುಭ ಸಂಜೆ'
        ],
        'thanks': [
            'ಧನ್ಯವಾದ', 'ಧನ್ಯವಾದಗಳು', 'ಥ್ಯಾಂಕ್ಸ್',
            'ಥ್ಯಾಂಕ್ ಯೂ'
        ],
    },
    'ta': {  # Tamil
        'investment': [
            'முதலீடு', 'பணம் முதலீடு', 'invest',
            'லாபம்', 'வருமானம்'
        ],
        'price': [
            'விலை', 'விலை எவ்வளவு', 'rate',
            'எவ்வளவு', 'மதிப்பு'
        ],
        'area_info': [
            'பகுதி', 'இடம்', 'பகுதியில்',
            'இங்கே', 'அங்கே', 'எப்படி இருக்கிறது'
        ],
        'comparison': [
            'ஒப்பீடு', 'compare', 'எது சிறந்தது',
            'வித்தியாசம்', 'மேல்'
        ],
        'amenities': [
            'வசதிகள்', 'பள்ளி', 'மருத்துவமனை', 'மருத்துவமனை',
            'சந்தை', 'பூங்கா', 'மெட்ரோ'
        ],
        'safety': [
            'பாதுகாப்பான', 'பாதுகாப்பு', 'ஆபத்தான',
            'சேஃப்'
        ],
        'greeting': [
            'வணக்கம்', 'ஹலோ', 'வணக்கங்கள்',
            'காலை வணக்கம்', 'மாலை வணக்கம்'
        ],
        'thanks': [
            'நன்றி', 'நன்றிகள்', 'தாங்க்ஸ்',
            'தாங்க் யூ'
        ],
    },
    'te': {  # Telugu
        'investment': [
            'పెట్టుబడి', 'పెట్టుబడి పెట్టడం', 'invest',
            'లాభం', 'ఆదాయం'
        ],
        'price': [
            'ధర', 'ధర ఎంత', 'rate',
            'ఎంత', 'విలువ'
        ],
        'area_info': [
            'ప్రాంతం', 'ప్రదేశం', 'ఏరియా',
            'ఇక్కడ', 'అక్కడ', 'ఎలా ఉంది'
        ],
        'comparison': [
            'పోలిక', 'compare', 'ఏది మంచిది',
            'తేడా', 'మెరుగైనది'
        ],
        'amenities': [
            'సౌకర్యాలు', 'పాఠశాల', 'ఆసుపత్రి',
            'మార్కెట్', 'పార్క్', 'మెట్రో'
        ],
        'safety': [
            'సురక్షితమైన', 'సేఫ్', 'ప్రమాదకరమైన',
            'భద్రత'
        ],
        'greeting': [
            'నమస్కారం', 'హలో', 'నమస్కారాలు',
            'శుభోదయం', 'శుభ సాయంత్రం'
        ],
        'thanks': [
            'ధన్యవాదాలు', 'థాంక్స్', 'థాంక్ యూ',
            'కృతజ్ఞతలు'
        ],
    },
    'ml': {  # Malayalam
        'investment': [
            'നിക്ഷേപം', 'പണം നിക്ഷേപിക്കൽ', 'invest',
            'ലാഭം', 'വരുമാനം'
        ],
        'price': [
            'വില', 'വില എന്ത്', 'rate',
            'എന്ത്', 'മൂല്യം'
        ],
        'area_info': [
            'പ്രദേശം', 'സ്ഥലം', 'ഏരിയാ',
            'ഇവിടെ', 'അവിടെ', 'എങ്ങനെയുണ്ട്'
        ],
        'comparison': [
            'താരതമ്യം', 'compare', 'ഏതാണ് നല്ലത്',
            'വ്യത്യാസം', 'മികച്ചത്'
        ],
        'amenities': [
            'സൗകര്യങ്ങൾ', 'സ്കൂൾ', 'ആശുപത്രി',
            'മാർക്കറ്റ്', 'പാർക്ക്', 'മെട്രോ'
        ],
        'safety': [
            'സുരക്ഷിതമായ', 'സേഫ്', 'അപകടകരമായ',
            'സുരക്ഷ'
        ],
        'greeting': [
            'നമസ്കാരം', 'ഹലോ', 'നമസ്കാരങ്ങൾ',
            'സുപ്രഭാതം', 'ശുഭ സന്ധ്യ'
        ],
        'thanks': [
            'നന്ദി', 'താങ്ക്സ്', 'താങ്ക് യൂ',
            'നന്ദി അർപ്പിക്കുന്നു'
        ],
    }
}

# Transliteration patterns for common Bangalore location names
LOCATION_TRANSLITERATIONS = {
    # Hindi transliterations
    'hi': {
        'कोरमंगला': 'Koramangala',
        'इंदिरानगर': 'Indiranagar',
        'व्हाइटफील्ड': 'Whitefield',
        'हेब्बल': 'Hebbal',
        'जयनगर': 'Jayanagar',
        'जेपी नगर': 'JP Nagar',
        'एचएसआर लेआउट': 'HSR Layout',
        'बीटीएम लेआउट': 'BTM Layout',
        'बेलंदूर': 'Bellandur',
        'मार्थाहल्ली': 'Marathahalli',
        'इलेक्ट्रॉनिक सिटी': 'Electronic City',
        'बनशंकरी': 'Banashankari',
        'मल्लेश्वरम': 'Malleshwaram',
        'राजाजीनगर': 'Rajajinagar',
        'एमजी रोड': 'MG Road',
        'बैंगलोर': 'Bangalore',
        'बेंगलुरु': 'Bengaluru',
    },
    # Kannada transliterations (native script to English)
    'kn': {
        'ಕೋರಮಂಗಲ': 'Koramangala',
        'ಇಂದಿರಾನಗರ': 'Indiranagar',
        'ವೈಟ್‌ಫೀಲ್ಡ್': 'Whitefield',
        'ಹೆಬ್ಬಾಳ': 'Hebbal',
        'ಜಯನಗರ': 'Jayanagar',
        'ಜೆಪಿ ನಗರ': 'JP Nagar',
        'ಎಚ್‌ಎಸ್‌ಆರ್ ಲೇಔಟ್': 'HSR Layout',
        'ಬಿಟಿಎಂ ಲೇಔಟ್': 'BTM Layout',
        'ಬೆಳಂದೂರು': 'Bellandur',
        'ಮಾರತಹಳ್ಳಿ': 'Marathahalli',
        'ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಸಿಟಿ': 'Electronic City',
        'ಬನಶಂಕರಿ': 'Banashankari',
        'ಮಲ್ಲೇಶ್ವರಂ': 'Malleshwaram',
        'ರಾಜಾಜಿನಗರ': 'Rajajinagar',
        'ಎಂಜಿ ರಸ್ತೆ': 'MG Road',
        'ಬೆಂಗಳೂರು': 'Bengaluru',
    },
    # Tamil transliterations
    'ta': {
        'கொரமங்கலா': 'Koramangala',
        'இந்திராநகர்': 'Indiranagar',
        'வைட்ஃபீல்ட்': 'Whitefield',
        'ஹெப்பல்': 'Hebbal',
        'ஜெயநகர்': 'Jayanagar',
        'ஜேபி நகர்': 'JP Nagar',
        'பெங்களூரு': 'Bengaluru',
    },
    # Telugu transliterations
    'te': {
        'కొరమాంగల': 'Koramangala',
        'ఇందిరానగర్': 'Indiranagar',
        'వైట్‌ఫీల్డ్': 'Whitefield',
        'హెబ్బాల్': 'Hebbal',
        'జయనగర్': 'Jayanagar',
        'బెంగళూరు': 'Bengaluru',
    },
    # Malayalam transliterations
    'ml': {
        'കൊറമംഗല': 'Koramangala',
        'ഇന്ദിരാനഗർ': 'Indiranagar',
        'വൈറ്റ്ഫീൽഡ്': 'Whitefield',
        'ഹെബ്ബാൽ': 'Hebbal',
        'ബെംഗളൂരു': 'Bengaluru',
    }
}

# Common Hinglish/Kanglish/Tanglish patterns (mixed English + regional)
MIXED_LANGUAGE_PATTERNS = {
    'investment': [
        r'\b(invest|investment|investing)\b',
        r'\b(पैसा|पैसे)\s*(लगाना|लगाने)\b',
        r'\b(हूडिके|ಹೂಡಿಕೆ)\b',
        r'\b(मुनाफा|लाभ|profit)\b',
        r'\b(roi|ROI)\b',
    ],
    'price': [
        r'\b(price|rate|cost)\b',
        r'\b(कीमत|भाव|दाम)\b',
        r'\b(बेलೆ|ಬೆಲೆ)\b',
        r'\b(विलை|விலை)\b',
        r'\b(kitna|kitne|कितना|ಎಷ್ಟು)\b',
    ],
    'area_info': [
        r'\b(area|locality|neighborhood)\b',
        r'\b(इलाका|क्षेत्र|एरिया)\b',
        r'\b(ಪ್ರದೇಶ|ಏರಿಯಾ)\b',
        r'\b(பகுதி|ஏரியா)\b',
        r'\b(kaisa|kaisi|कैसा|ಹೇಗೆ)\b',
    ],
    'comparison': [
        r'\b(compare|vs|versus)\b',
        r'\b(तुलना|compare)\b',
        r'\b(ಹೋಲಿಕೆ)\b',
        r'\b(ஒப்பீடு)\b',
        r'\b(better|बेहतर|ಉತ್ತಮ)\b',
    ],
    'amenities': [
        r'\b(school|hospital|mall|park|metro)\b',
        r'\b(स्कूल|अस्पताल|मॉल)\b',
        r'\b(ಶಾಲೆ|ಆಸ್ಪತ್ರೆ|ಮಾಲ್)\b',
        r'\b(பள்ளி|மருத்துவமனை)\b',
    ],
    'safety': [
        r'\b(safe|safety|secure)\b',
        r'\b(सुरक्षित|सेफ)\b',
        r'\b(ಸುರಕ್ಷಿತ|ಸೇಫ್)\b',
        r'\b(பாதுகாப்பான)\b',
    ],
}


class MultilingualIntentDetector:
    """
    Detects intents from multilingual queries.
    
    Supports:
    - Hindi, Kannada, Tamil, Telugu, Malayalam
    - Transliterated location names
    - Mixed language queries (Hinglish, Kanglish, etc.)
    """
    
    def __init__(self):
        """Initialize the multilingual detector."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self._compiled_mixed = {}
        for intent, patterns in MIXED_LANGUAGE_PATTERNS.items():
            self._compiled_mixed[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect the language of the input text.
        
        Args:
            text: Input text
            
        Returns:
            LanguageDetectionResult with detected language
        """
        # Check for Devanagari script (Hindi)
        if re.search(r'[\u0900-\u097F]', text):
            return LanguageDetectionResult(
                language=SupportedLanguage.HINDI,
                confidence=0.95,
                original_text=text,
                normalized_text=text
            )
        
        # Check for Kannada script
        if re.search(r'[\u0C80-\u0CFF]', text):
            return LanguageDetectionResult(
                language=SupportedLanguage.KANNADA,
                confidence=0.95,
                original_text=text,
                normalized_text=text
            )
        
        # Check for Tamil script
        if re.search(r'[\u0B80-\u0BFF]', text):
            return LanguageDetectionResult(
                language=SupportedLanguage.TAMIL,
                confidence=0.95,
                original_text=text,
                normalized_text=text
            )
        
        # Check for Telugu script
        if re.search(r'[\u0C00-\u0C7F]', text):
            return LanguageDetectionResult(
                language=SupportedLanguage.TELUGU,
                confidence=0.95,
                original_text=text,
                normalized_text=text
            )
        
        # Check for Malayalam script
        if re.search(r'[\u0D00-\u0D7F]', text):
            return LanguageDetectionResult(
                language=SupportedLanguage.MALAYALAM,
                confidence=0.95,
                original_text=text,
                normalized_text=text
            )
        
        # Default to English, but check for mixed language patterns
        return LanguageDetectionResult(
            language=SupportedLanguage.ENGLISH,
            confidence=0.7,
            is_transliterated=self._is_transliterated(text),
            original_text=text,
            normalized_text=text
        )
    
    def _is_transliterated(self, text: str) -> bool:
        """Check if text contains transliterated regional words."""
        # Common transliteration patterns
        translit_patterns = [
            r'\b(namaste|namaskar|hello|hai)\b',
            r'\b(dhanyavad|shukriya|nandri)\b',
            r'\b(kitna|kitne|kaisa|kaisi)\b',
            r'\b(accha|achha|theek)\b',
            r'\b(bhai|didi|anna|akka)\b',
        ]
        
        for pattern in translit_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def transliterate_location(
        self, 
        text: str, 
        source_lang: SupportedLanguage
    ) -> str:
        """
        Transliterate location names from regional script to English.
        
        Args:
            text: Text containing location names
            source_lang: Source language
            
        Returns:
            Text with transliterated location names
        """
        if source_lang == SupportedLanguage.ENGLISH:
            return text
        
        lang_code = source_lang.value
        transliterations = LOCATION_TRANSLITERATIONS.get(lang_code, {})
        
        result = text
        for native, english in transliterations.items():
            result = result.replace(native, english)
        
        return result
    
    def detect_intent_multilingual(
        self,
        text: str,
        language: Optional[SupportedLanguage] = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Detect intent from multilingual text.
        
        Args:
            text: Input text
            language: Optional pre-detected language
            
        Returns:
            Tuple of (intent, confidence, metadata)
        """
        if language is None:
            lang_result = self.detect_language(text)
            language = lang_result.language
        
        lang_code = language.value
        
        # First, check language-specific patterns
        lang_patterns = LANGUAGE_PATTERNS.get(lang_code, {})
        
        intent_scores: Dict[str, float] = {}
        
        for intent, patterns in lang_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    intent_scores[intent] = intent_scores.get(intent, 0) + 0.3
        
        # Also check mixed language patterns
        for intent, patterns in self._compiled_mixed.items():
            for pattern in patterns:
                if pattern.search(text):
                    intent_scores[intent] = intent_scores.get(intent, 0) + 0.25
        
        if not intent_scores:
            return 'general', 0.5, {'language': lang_code}
        
        # Get best intent
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(1.0, intent_scores[best_intent])
        
        return best_intent, confidence, {'language': lang_code}
    
    def normalize_query(
        self,
        text: str,
        language: Optional[SupportedLanguage] = None
    ) -> str:
        """
        Normalize a multilingual query for processing.
        
        Transliterates location names and standardizes format.
        
        Args:
            text: Input text
            language: Optional pre-detected language
            
        Returns:
            Normalized text
        """
        if language is None:
            lang_result = self.detect_language(text)
            language = lang_result.language
        
        # Transliterate location names
        normalized = self.transliterate_location(text, language)
        
        return normalized
    
    def get_response_language(
        self,
        user_language: SupportedLanguage,
        user_preference: Optional[str] = None
    ) -> SupportedLanguage:
        """
        Determine the language to use for response.
        
        Args:
            user_language: Detected user language
            user_preference: User's stated preference
            
        Returns:
            Language to use for response
        """
        if user_preference:
            try:
                return SupportedLanguage(user_preference)
            except ValueError:
                pass
        
        # Respond in the same language as the user
        return user_language
    
    def get_localized_greeting(
        self,
        language: SupportedLanguage
    ) -> str:
        """Get a localized greeting."""
        greetings = {
            SupportedLanguage.ENGLISH: "Hello! How can I help you with real estate today?",
            SupportedLanguage.HINDI: "नमस्ते! आज रियल एस्टेट में मैं आपकी कैसे मदद कर सकता हूं?",
            SupportedLanguage.KANNADA: "ನಮಸ್ಕಾರ! ಇಂದು ರಿಯಲ್ ಎಸ್ಟೇಟ್‌ನಲ್ಲಿ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
            SupportedLanguage.TAMIL: "வணக்கம்! இன்று ரியல் எஸ்டேட்டில் நான் உங்களுக்கு எப்படி உதவ முடியும்?",
            SupportedLanguage.TELUGU: "నమస్కారం! ఈరోజు రియల్ ఎస్టేట్‌లో నేను మీకు ఎలా సహాయం చేయగలను?",
            SupportedLanguage.MALAYALAM: "നമസ്കാരം! ഇന്ന് റിയൽ എസ്റ്റേറ്റിൽ ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കാം?",
        }
        return greetings.get(language, greetings[SupportedLanguage.ENGLISH])


# Singleton instance
_detector_instance: Optional[MultilingualIntentDetector] = None


def get_multilingual_detector() -> MultilingualIntentDetector:
    """Get or create the singleton multilingual detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = MultilingualIntentDetector()
    return _detector_instance


def detect_language(text: str) -> LanguageDetectionResult:
    """Convenience function to detect language."""
    return get_multilingual_detector().detect_language(text)


def detect_intent_multilingual(
    text: str,
    language: Optional[SupportedLanguage] = None
) -> Tuple[str, float, Dict[str, Any]]:
    """Convenience function to detect intent from multilingual text."""
    return get_multilingual_detector().detect_intent_multilingual(text, language)


def normalize_query(text: str) -> str:
    """Convenience function to normalize a multilingual query."""
    return get_multilingual_detector().normalize_query(text)
