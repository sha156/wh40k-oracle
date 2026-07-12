import { ChatApp } from "@/components/chat/ChatApp";
import { broadsideVsKnight } from "@/lib/fixtures/broadside-vs-knight";

/**
 * 聊天主页（Stage 3 闭环）：首屏展示 fixture 示例，提问后经 /chat SSE 走真后端逐槽位填充。
 * 契约唯一真源 web/src/lib/answer.ts；后端 web_api 按同一契约产出。
 */
export default function ChatPage() {
  return <ChatApp initial={broadsideVsKnight} />;
}
