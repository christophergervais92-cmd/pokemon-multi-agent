#!/usr/bin/env python3
"""
AI-Powered Topic Generator for TikTok Videos

Generates engaging topics and scripts about tribal cultures
optimized for TikTok's short-form video format.
"""
import os
import json
import re
from typing import Dict, List, Optional
from datetime import datetime

from agents.utils.logger import get_logger

logger = get_logger("topic_generator")

# Try OpenAI first, fall back to Anthropic
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class TopicGenerator:
    """
    AI-powered topic and script generator for tribal culture videos.
    
    Features:
    - Generates viral TikTok topics
    - Creates 10-60 second scripts
    - Extracts keywords for asset matching
    - Multiple topic categories
    """
    
    CATEGORIES = [
        "culture",
        "traditions",
        "lifestyle",
        "festivals",
        "crafts",
        "hunting",
        "cooking",
        "ceremonies",
        "music",
        "clothing",
    ]
    
    LOCATIONS = [
        "Mongolia",
        "Nepal",
        "Papua New Guinea",
    ]
    
    def __init__(self):
        """Initialize topic generator with available AI service."""
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        if self.openai_key and HAS_OPENAI:
            self.client = OpenAI(api_key=self.openai_key)
            self.provider = "openai"
            logger.info("Initialized with OpenAI")
        elif self.anthropic_key and HAS_ANTHROPIC:
            self.client = Anthropic(api_key=self.anthropic_key)
            self.provider = "anthropic"
            logger.info("Initialized with Anthropic")
        else:
            self.client = None
            self.provider = "demo"
            logger.warning("No AI API keys found, using demo mode")
    
    def generate_topic(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        duration: int = 30
    ) -> Dict:
        """
        Generate a video topic and script.
        
        Args:
            category: Topic category (culture, traditions, etc.)
            location: Specific location (Mongolia, Nepal, PNG)
            duration: Target video duration in seconds
        
        Returns:
            Dict with: topic, script, keywords, category, location, duration
        """
        if self.provider == "demo":
            return self._generate_demo_topic(category, location, duration)
        
        # Build prompt
        prompt = self._build_prompt(category, location, duration)
        
        # Generate with AI
        if self.provider == "openai":
            response = self._generate_openai(prompt)
        else:
            response = self._generate_anthropic(prompt)
        
        # Parse response
        topic_data = self._parse_response(response, category, location, duration)
        
        logger.info(f"Generated topic: {topic_data['topic']}")
        
        return topic_data
    
    def _build_prompt(self, category: Optional[str], location: Optional[str], duration: int) -> str:
        """Build prompt for AI."""
        location_str = location if location else "Mongolia, Nepal, or Papua New Guinea"
        category_str = category if category else "any aspect of tribal life"
        
        prompt = f"""Generate a captivating TikTok video topic and script about tribal cultures.

Requirements:
- Location: {location_str}
- Category: {category_str}
- Duration: {duration} seconds (approximately {duration * 3} words)
- Style: Documentary-style, educational but engaging
- Tone: Respectful, informative, fascinating

The script should:
1. Hook viewers in the first 2 seconds
2. Share interesting facts or cultural insights
3. Be optimized for TikTok (short, punchy, visual)
4. End with a call-to-action (like, follow, etc.)

Return ONLY a JSON object with this structure:
{{
  "topic": "Brief topic title (5-8 words)",
  "script": "The complete voiceover script",
  "keywords": ["keyword1", "keyword2", ...],
  "hook": "Opening line that grabs attention"
}}

Keywords should include: location, activities, objects, and visual elements mentioned in the script."""
        
        return prompt
    
    def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a creative content writer specializing in documentary-style short videos about tribal cultures."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._generate_demo_response()
    
    def _generate_anthropic(self, prompt: str) -> str:
        """Generate using Anthropic."""
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return self._generate_demo_response()
    
    def _parse_response(self, response: str, category: Optional[str], location: Optional[str], duration: int) -> Dict:
        """Parse AI response into structured data."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # Add metadata
            data['category'] = category or self._infer_category(data['script'])
            data['location'] = location or self._infer_location(data['script'])
            data['duration'] = duration
            data['generated_at'] = datetime.now().isoformat()
            
            # Ensure all required fields
            if 'topic' not in data or 'script' not in data:
                raise ValueError("Missing required fields")
            
            if 'keywords' not in data:
                data['keywords'] = self._extract_keywords(data['script'])
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return self._generate_demo_topic(category, location, duration)
    
    def _infer_category(self, script: str) -> str:
        """Infer category from script content."""
        script_lower = script.lower()
        for cat in self.CATEGORIES:
            if cat in script_lower:
                return cat
        return "culture"
    
    def _infer_location(self, script: str) -> str:
        """Infer location from script content."""
        for loc in self.LOCATIONS:
            if loc.lower() in script.lower():
                return loc
        return "Mongolia"  # Default
    
    def _extract_keywords(self, script: str) -> List[str]:
        """Extract keywords from script."""
        keywords = []
        
        # Add locations found
        for loc in self.LOCATIONS:
            if loc.lower() in script.lower():
                keywords.append(loc.lower())
        
        # Add categories found
        for cat in self.CATEGORIES:
            if cat in script.lower():
                keywords.append(cat)
        
        # Common visual elements
        visual_keywords = [
            'hunting', 'festival', 'cooking', 'dancing', 'ceremony',
            'clothing', 'crafts', 'music', 'nature', 'mountains',
            'fire', 'traditional', 'community', 'family'
        ]
        
        for keyword in visual_keywords:
            if keyword in script.lower():
                keywords.append(keyword)
        
        return list(set(keywords))[:8]  # Return unique, max 8
    
    def _generate_demo_topic(self, category: Optional[str], location: Optional[str], duration: int) -> Dict:
        """Generate demo topic for testing without API keys."""
        location = location or "Mongolia"
        category = category or "hunting"
        
        demo_topics = {
            "Mongolia": {
                "hunting": {
                    "topic": "Ancient Mongolian Eagle Hunting Tradition",
                    "script": "Watch this! In Mongolia's Altai Mountains, eagle hunters train golden eagles to hunt foxes and rabbits. This tradition dates back 4,000 years. The bond between hunter and eagle is sacred - they work together as partners, not master and pet. These magnificent birds can spot prey from two miles away. Follow for more incredible tribal traditions!",
                    "hook": "Watch this! In Mongolia's Altai Mountains...",
                    "keywords": ["mongolia", "hunting", "eagle", "traditional", "mountains", "nature"]
                },
                "festivals": {
                    "topic": "Mongolia's Epic Naadam Festival",
                    "script": "Every summer, Mongolia explodes with color during Naadam - the festival of 'Three Manly Games.' Wrestling, archery, and horse racing bring thousands together. Wrestlers wear traditional costumes dating back to Genghis Khan. Children as young as 5 race horses across 20 miles of open steppe. This isn't just a festival - it's keeping 800 years of warrior culture alive. Double tap if this amazed you!",
                    "hook": "Every summer, Mongolia explodes with color...",
                    "keywords": ["mongolia", "festival", "traditional", "wrestling", "archery", "horses"]
                }
            },
            "Nepal": {
                "ceremonies": {
                    "topic": "Nepal's Living Goddess Tradition",
                    "script": "In Nepal, a young girl becomes a living goddess called Kumari. Selected through ancient rituals, she's worshipped as the incarnation of divine power. She lives in a palace, never touching the ground, until she reaches puberty. This tradition has existed for over 300 years in the Kathmandu Valley. The selection process involves 32 specific physical and astrological requirements. Mind-blowing, right? Follow for more!",
                    "hook": "In Nepal, a young girl becomes a living goddess...",
                    "keywords": ["nepal", "ceremony", "traditional", "goddess", "ritual", "cultural"]
                }
            },
            "Papua New Guinea": {
                "culture": {
                    "topic": "Papua New Guinea's 800 Languages",
                    "script": "Papua New Guinea has more languages than any country on Earth - over 800! In some villages, tribes 5 miles apart can't understand each other. The island's rugged mountains isolated communities for thousands of years. Each tribe developed unique languages, customs, and traditions. This is the most culturally diverse place on the planet. Like and follow to learn more about these incredible cultures!",
                    "hook": "Papua New Guinea has more languages than any country on Earth...",
                    "keywords": ["papua new guinea", "culture", "traditional", "tribes", "languages", "diversity"]
                }
            }
        }
        
        topic_data = demo_topics.get(location, demo_topics["Mongolia"]).get(category, demo_topics["Mongolia"]["hunting"])
        topic_data['category'] = category
        topic_data['location'] = location
        topic_data['duration'] = duration
        topic_data['generated_at'] = datetime.now().isoformat()
        
        logger.info(f"Generated demo topic: {topic_data['topic']}")
        
        return topic_data
    
    def _generate_demo_response(self) -> str:
        """Generate demo JSON response."""
        return json.dumps({
            "topic": "Traditional Mongolian Nomadic Life",
            "script": "Step inside a Mongolian ger and experience nomadic life. These portable homes have sheltered families for centuries across the vast steppes. Every element has meaning - the central stove represents the heart of the home, the door always faces south for warmth. Nomads still migrate with the seasons, just as their ancestors did. This lifestyle connects them deeply to nature and tradition. Follow for more amazing tribal cultures!",
            "keywords": ["mongolia", "nomadic", "traditional", "ger", "lifestyle", "culture"],
            "hook": "Step inside a Mongolian ger..."
        })
    
    def generate_batch(self, count: int = 5) -> List[Dict]:
        """
        Generate multiple topics at once.
        
        Args:
            count: Number of topics to generate
        
        Returns:
            List of topic dictionaries
        """
        topics = []
        
        for i in range(count):
            # Rotate through categories and locations
            category = self.CATEGORIES[i % len(self.CATEGORIES)]
            location = self.LOCATIONS[i % len(self.LOCATIONS)]
            
            topic = self.generate_topic(category=category, location=location)
            topics.append(topic)
        
        logger.info(f"Generated {len(topics)} topics")
        
        return topics


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    generator = TopicGenerator()
    
    # Generate single topic
    topic = generator.generate_topic(category="hunting", location="Mongolia")
    print(json.dumps(topic, indent=2))
    
    # Generate batch
    # topics = generator.generate_batch(count=5)
    # for t in topics:
    #     print(f"\n{t['topic']}")
