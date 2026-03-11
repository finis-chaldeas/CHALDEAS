import { useMemo } from 'react'

interface Props {
  text: string
  className?: string
}

/**
 * Renders text with basic inline markdown support:
 * - **bold** → <strong>
 * - *italic* → <em>
 * - Newlines preserved via white-space: pre-line in CSS
 */
export function MarkdownText({ text, className }: Props) {
  const parts = useMemo(() => parseInlineMarkdown(text), [text])

  return (
    <div className={className}>
      {parts.map((part, i) => {
        if (part.type === 'bold') return <strong key={i}>{part.text}</strong>
        if (part.type === 'italic') return <em key={i}>{part.text}</em>
        return <span key={i}>{part.text}</span>
      })}
    </div>
  )
}

interface TextPart {
  type: 'text' | 'bold' | 'italic'
  text: string
}

function parseInlineMarkdown(input: string): TextPart[] {
  const parts: TextPart[] = []
  // Match **bold** first, then *italic*
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*)/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(input)) !== null) {
    // Text before the match
    if (match.index > lastIndex) {
      parts.push({ type: 'text', text: input.slice(lastIndex, match.index) })
    }

    if (match[2]) {
      // **bold**
      parts.push({ type: 'bold', text: match[2] })
    } else if (match[3]) {
      // *italic*
      parts.push({ type: 'italic', text: match[3] })
    }

    lastIndex = match.index + match[0].length
  }

  // Remaining text
  if (lastIndex < input.length) {
    parts.push({ type: 'text', text: input.slice(lastIndex) })
  }

  if (parts.length === 0) {
    parts.push({ type: 'text', text: input })
  }

  return parts
}
