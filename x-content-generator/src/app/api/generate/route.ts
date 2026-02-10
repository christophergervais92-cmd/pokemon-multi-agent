import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";

export const runtime = "edge";

interface GenerateRequest {
  topic: string;
  tone: string;
  contentType: string;
  audience: string;
  includeHashtags: boolean;
  includeEmojis: boolean;
  apiKey: string;
}

function buildPrompt(req: GenerateRequest): string {
  const toneDescriptions: Record<string, string> = {
    professional: "professional, authoritative, and polished",
    casual: "casual, friendly, and relatable",
    witty: "witty, clever, and engaging with sharp observations",
    educational: "educational, informative, and clear",
    provocative: "bold, provocative, and attention-grabbing (but not offensive)",
    inspirational: "inspirational, motivating, and uplifting",
  };

  const contentTypeInstructions: Record<string, string> = {
    single:
      "Generate a single X (Twitter) post. Keep it under 280 characters. Make it impactful and engaging.",
    thread:
      "Generate an X (Twitter) thread with 4-6 posts. Number each post (1/, 2/, etc.). Each post should be under 280 characters. Start with a hook that grabs attention. End with a call to action.",
    reply:
      "Generate a compelling reply or quote-tweet style response. Keep it under 280 characters. Make it add value to the conversation.",
    poll:
      "Generate an X (Twitter) poll post. Include: 1) An engaging question (under 280 chars), 2) 2-4 poll options (each under 25 chars). Format the options as bullet points.",
  };

  let prompt = `You are an expert X (Twitter) content creator. Generate content with the following specifications:

**Topic:** ${req.topic}
**Tone:** ${toneDescriptions[req.tone] || req.tone}
**Format:** ${contentTypeInstructions[req.contentType] || "Single post under 280 characters"}`;

  if (req.audience) {
    prompt += `\n**Target Audience:** ${req.audience}`;
  }

  prompt += `\n\n**Requirements:**`;

  if (req.includeHashtags) {
    prompt += `\n- Include 2-3 relevant hashtags`;
  } else {
    prompt += `\n- Do NOT include any hashtags`;
  }

  if (req.includeEmojis) {
    prompt += `\n- Use emojis strategically to enhance the message`;
  } else {
    prompt += `\n- Do NOT use any emojis`;
  }

  prompt += `
- Optimize for engagement (likes, retweets, replies)
- Use line breaks for readability where appropriate
- Make it feel authentic and human, not AI-generated
- Do NOT include any meta-commentary or explanations, just the post content itself`;

  return prompt;
}

export async function POST(request: NextRequest) {
  try {
    const body: GenerateRequest = await request.json();

    if (!body.topic?.trim()) {
      return NextResponse.json(
        { error: "Topic is required" },
        { status: 400 }
      );
    }

    if (!body.apiKey?.trim()) {
      return NextResponse.json(
        { error: "OpenAI API key is required" },
        { status: 400 }
      );
    }

    const openai = new OpenAI({
      apiKey: body.apiKey.trim(),
    });

    const prompt = buildPrompt(body);

    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content:
            "You are an expert social media content creator specializing in X (Twitter). You create viral, engaging content that drives meaningful engagement. Output only the post content, no explanations or meta-commentary.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      temperature: 0.8,
      max_tokens: 1000,
    });

    const content = completion.choices[0]?.message?.content?.trim();

    if (!content) {
      return NextResponse.json(
        { error: "Failed to generate content. Please try again." },
        { status: 500 }
      );
    }

    return NextResponse.json({ content });
  } catch (error: unknown) {
    console.error("Generation error:", error);

    if (error instanceof OpenAI.APIError) {
      if (error.status === 401) {
        return NextResponse.json(
          { error: "Invalid API key. Please check your OpenAI API key and try again." },
          { status: 401 }
        );
      }
      if (error.status === 429) {
        return NextResponse.json(
          { error: "Rate limit exceeded. Please wait a moment and try again." },
          { status: 429 }
        );
      }
      return NextResponse.json(
        { error: `OpenAI API error: ${error.message}` },
        { status: error.status || 500 }
      );
    }

    return NextResponse.json(
      { error: "An unexpected error occurred. Please try again." },
      { status: 500 }
    );
  }
}
