import { AnswerHead } from "@/components/chat/AnswerHead";
import { AskCard } from "@/components/chat/AskCard";
import { CalcList } from "@/components/chat/CalcList";
import { CiteSeals } from "@/components/chat/CiteSeals";
import { Composer } from "@/components/chat/Composer";
import { Datasheet } from "@/components/chat/Datasheet";
import { SensitivityCta } from "@/components/chat/SensitivityCta";
import { SiteHeader } from "@/components/chat/SiteHeader";
import { ToolTrace } from "@/components/chat/ToolTrace";
import { VerdictCard } from "@/components/chat/VerdictCard";
import { broadsideVsKnight } from "@/lib/fixtures/broadside-vs-knight";

/**
 * 聊天主页静态版（Stage 2）：数据全部来自 fixture（永久回归样例），
 * Stage 3 接 FastAPI 后同一契约直接替换数据源。
 */
export default function ChatPage() {
  const { question, context, answer } = broadsideVsKnight;
  return (
    <>
      <SiteHeader context={context} />
      <main className="mx-auto max-w-[1100px] px-5 pt-[26px] pb-[150px] max-tablet:px-2.5 max-tablet:pt-4 max-tablet:pb-[210px]">
        <AskCard question={question} />
        <div>
          <AnswerHead summary={answer.summary} />
          <ToolTrace steps={answer.trace} warn={answer.traceWarn} />
          <VerdictCard verdict={answer.verdict} />
          <CalcList steps={answer.calc} />
          {answer.entityCard ? <Datasheet card={answer.entityCard} /> : null}
          <CiteSeals cites={answer.cites} />
          <SensitivityCta sensitivity={answer.sensitivity} cta={answer.cta} />
        </div>
      </main>
      <Composer followups={answer.followups} />
    </>
  );
}
