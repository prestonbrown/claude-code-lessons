// SPDX-License-Identifier: MIT
// OpenCode adapter for coding-agent-lessons
//
// Hooks into OpenCode events to:
// 1. Inject lessons context at session start
// 2. Track lesson citations when AI responds
// 3. Capture LESSON: commands from user input

import type { Plugin } from "@opencode-ai/plugin"

const MANAGER = "~/.config/coding-agent-lessons/lessons-manager.sh"

export const LessonsPlugin: Plugin = async ({ $, client }) => {
  return {
    // Inject lessons at session start
    "session.created": async (input) => {
      try {
        // Get lesson context to inject
        const { stdout } = await $`${MANAGER} inject 5`
        
        if (stdout && stdout.trim()) {
          // Inject into session as context without triggering AI response
          await client.session.prompt({
            path: { id: input.session.id },
            body: {
              noReply: true,
              parts: [{ 
                type: "text", 
                text: `<lessons-context>\n${stdout}\n</lessons-context>` 
              }],
            },
          })
        }
      } catch (e) {
        // Silently fail if lessons system not installed
        console.error("[lessons] Failed to inject:", e)
      }
    },

    // Track citations when session goes idle (AI finished responding)
    "session.idle": async (input) => {
      try {
        // Get the messages from this session
        const messages = await client.session.messages({ 
          path: { id: input.session.id } 
        })
        
        // Find the last assistant message
        const assistantMessages = messages.filter(m => m.info.role === "assistant")
        const lastAssistant = assistantMessages[assistantMessages.length - 1]
        
        if (!lastAssistant) return

        // Extract text content
        const content = lastAssistant.parts
          .filter(p => p.type === "text")
          .map(p => (p as { type: "text"; text: string }).text)
          .join("")

        // Find [L###] or [S###] citations
        const citations = content.match(/\[(L|S)\d{3}\]/g) || []
        const uniqueCitations = [...new Set(citations)]

        // Cite each lesson
        for (const cite of uniqueCitations) {
          const lessonId = cite.slice(1, -1) // Remove brackets
          await $`${MANAGER} cite ${lessonId}`
        }

        if (uniqueCitations.length > 0) {
          console.log(`[lessons] Cited: ${uniqueCitations.join(", ")}`)
        }
      } catch (e) {
        // Silently fail
      }
    },

    // Capture LESSON: commands from user messages
    "message.updated": async (input) => {
      if (input.message.role !== "user") return

      try {
        const text = input.message.parts
          .filter(p => p.type === "text")
          .map(p => (p as { type: "text"; text: string }).text)
          .join("")

        // Check for LESSON: or SYSTEM LESSON: prefix
        const systemMatch = text.match(/^SYSTEM\s+LESSON:\s*(.+)$/im)
        const projectMatch = text.match(/^LESSON:\s*(.+)$/im)

        if (systemMatch || projectMatch) {
          const isSystem = !!systemMatch
          const lessonText = (systemMatch?.[1] || projectMatch?.[1] || "").trim()

          // Parse category: title - content
          let category = "correction"
          let title = lessonText
          let content = lessonText

          const catMatch = lessonText.match(/^([a-z]+):\s*(.+)$/i)
          if (catMatch) {
            category = catMatch[1].toLowerCase()
            const rest = catMatch[2]
            const dashMatch = rest.match(/^(.+?)\s*-\s*(.+)$/)
            if (dashMatch) {
              title = dashMatch[1].trim()
              content = dashMatch[2].trim()
            } else {
              title = rest
              content = rest
            }
          } else {
            const dashMatch = lessonText.match(/^(.+?)\s*-\s*(.+)$/)
            if (dashMatch) {
              title = dashMatch[1].trim()
              content = dashMatch[2].trim()
            }
          }

          // Add the lesson
          const cmd = isSystem ? "add-system" : "add"
          const result = await $`${MANAGER} ${cmd} ${category} ${title} ${content}`
          console.log(`[lessons] ${result.stdout}`)
        }
      } catch (e) {
        // Silently fail
      }
    },
  }
}
