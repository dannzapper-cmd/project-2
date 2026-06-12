"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Mic, Send, Volume2 } from "lucide-react"

import {
  chatWithProduct,
  type AnalysisCitation,
  type AnalysisResponse,
  type ChatMessage,
} from "@/lib/snapinsight-api"
import { getSnapInsightApiErrorMessage } from "@/lib/deployment-errors"
import { cn } from "@/lib/utils"

interface ProductChatPanelProps {
  analysis: AnalysisResponse
}

interface ChatTurn {
  id: string
  role: "user" | "assistant"
  content: string
  citations?: AnalysisCitation[]
  warnings?: string[]
}

type SpeechRecognitionConstructor = new () => SpeechRecognition

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult:
    | ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void)
    | null
  onend: (() => void) | null
  onerror: (() => void) | null
}

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: SpeechRecognitionConstructor
  webkitSpeechRecognition?: SpeechRecognitionConstructor
}

const SUGGESTED_QUESTIONS = [
  "What should I check on the label?",
  "Any allergens listed?",
  "Explain the nutrition info simply",
  "What data is uncertain?",
]

function buildHistory(turns: ChatTurn[]): ChatMessage[] {
  return turns.map((turn) => ({
    role: turn.role,
    content: turn.content,
  }))
}

function getSpeechRecognition(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null
  const speechWindow = window as SpeechRecognitionWindow
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null
}

export function ProductChatPanel({ analysis }: ProductChatPanelProps) {
  const [input, setInput] = useState("")
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [speechSupported] = useState(() => Boolean(getSpeechRecognition()))
  const [ttsSupported] = useState(
    () => typeof window !== "undefined" && "speechSynthesis" in window
  )
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
    }
  }, [])

  const sendQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      if (!trimmed || isLoading) return

      const userTurn: ChatTurn = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
      }
      const nextTurns = [...turns, userTurn]
      setTurns(nextTurns)
      setInput("")
      setError(null)
      setIsLoading(true)

      try {
        const response = await chatWithProduct(
          analysis,
          buildHistory(nextTurns),
          trimmed
        )
        setTurns((current) => [
          ...current,
          {
            id: response.request_id,
            role: "assistant",
            content: response.answer,
            citations: response.citations_used,
            warnings: response.warnings,
          },
        ])
      } catch (err) {
        setError(getSnapInsightApiErrorMessage(err))
      } finally {
        setIsLoading(false)
      }
    },
    [analysis, isLoading, turns]
  )

  const toggleListening = useCallback(() => {
    const Recognition = getSpeechRecognition()
    if (!Recognition) return

    if (isListening) {
      recognitionRef.current?.stop()
      setIsListening(false)
      return
    }

    const recognition = new Recognition()
    recognition.continuous = false
    recognition.interimResults = false
    // Uses browser locale for recognition accuracy.
    // Language selection is deferred to a later block.
    recognition.lang = navigator.language || "en-US"
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript
      if (transcript) {
        setInput(transcript)
      }
    }
    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)
    recognitionRef.current = recognition
    setIsListening(true)
    recognition.start()
  }, [isListening])

  const readAnswer = useCallback((answer: string) => {
    if (!ttsSupported || typeof window === "undefined") return
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(answer))
  }, [ttsSupported])

  return (
    <section className="glass-card mt-5 p-5">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-foreground">Ask about this product</h2>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          Answers are based on the current analysis and available source data.
          Verify product labels for decisions.
        </p>
        {(analysis.grounding_status === "no_match" ||
          analysis.grounding_status === "grounding_unavailable") && (
          <p className="mt-2 text-xs text-amber-200/80">
            Source data is limited for this product, so answers may be less complete.
          </p>
        )}
        {analysis.product_enrichment?.enrichment_source_confidence === "medium" && (
          <p className="mt-2 text-xs text-muted-foreground">
            Source matched by product name. Verify with the product label.
          </p>
        )}
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {SUGGESTED_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => void sendQuestion(question)}
            disabled={isLoading}
            className="rounded-full border border-white/10 bg-slate-900/60 px-3 py-1.5 text-left text-xs text-muted-foreground hover:bg-slate-800/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {question}
          </button>
        ))}
      </div>

      <div className="mb-4 space-y-3">
        {turns.map((turn) => (
          <div
            key={turn.id}
            className={cn(
              "rounded-2xl border p-3 text-sm",
              turn.role === "user"
                ? "ml-6 border-violet-500/20 bg-violet-500/10 text-violet-100"
                : "mr-6 border-white/5 bg-slate-800/50 text-muted-foreground"
            )}
          >
            <p className="leading-relaxed">{turn.content}</p>
            {turn.role === "assistant" && turn.citations && turn.citations.length > 0 && (
              <div className="mt-3 space-y-1 border-t border-white/5 pt-2">
                <p className="text-xs font-medium text-foreground">Sources used</p>
                {turn.citations.map((citation) => (
                  <p key={`${turn.id}-${citation.field}-${citation.value}`} className="text-xs">
                    {citation.field_label}: {citation.value}
                  </p>
                ))}
              </div>
            )}
            {turn.role === "assistant" && turn.warnings && turn.warnings.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-amber-100/80">
                {turn.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
            {turn.role === "assistant" && ttsSupported && (
              <button
                type="button"
                onClick={() => readAnswer(turn.content)}
                className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-violet-300 hover:text-violet-200"
              >
                <Volume2 className="h-3.5 w-3.5" />
                Read answer
              </button>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="mr-6 rounded-2xl border border-white/5 bg-slate-800/50 p-3 text-sm text-muted-foreground">
            Thinking...
          </div>
        )}
      </div>

      {error && (
        <p className="mb-3 rounded-2xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <form
        className="flex items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          void sendQuestion(input)
        }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about this product..."
          className="min-h-11 flex-1 rounded-full border border-white/10 bg-slate-900/70 px-4 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-violet-500/40"
        />
        {speechSupported ? (
          <button
            type="button"
            onClick={toggleListening}
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-slate-900/70 text-muted-foreground hover:bg-slate-800/80",
              isListening && "border-violet-500/40 text-violet-300"
            )}
            aria-label={isListening ? "Stop voice input" : "Start voice input"}
          >
            <Mic className="h-4 w-4" />
          </button>
        ) : (
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Voice input not supported in this browser.
          </span>
        )}
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="flex h-11 w-11 items-center justify-center rounded-full border border-violet-500/30 bg-violet-500/15 text-violet-300 hover:bg-violet-500/25 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Send question"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </section>
  )
}
