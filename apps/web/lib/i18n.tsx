"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

export type Lang = "en" | "zh" | "es";
const LANG_KEY = "aic_lang";

// Flat dictionary: English source string -> [中文, español].
// Missing keys fall back to English, so untranslated strings never break the UI.
const DICT: Record<string, [string, string]> = {
  // Navigation & shell
  "Dashboard": ["仪表盘", "Panel"],
  "Learn": ["学习", "Aprender"],
  "Practice": ["练习", "Práctica"],
  "Mock Interview": ["模拟面试", "Entrevista simulada"],
  "Tasks": ["任务", "Tareas"],
  "Progress": ["进度", "Progreso"],
  "Sign out": ["退出登录", "Cerrar sesión"],
  "Local mode": ["单机模式", "Modo local"],

  // Auth
  "Sign in": ["登录", "Iniciar sesión"],
  "Signing in…": ["登录中…", "Iniciando…"],
  "Email": ["邮箱", "Correo"],
  "Password": ["密码", "Contraseña"],
  "No account?": ["没有账号？", "¿Sin cuenta?"],
  "Register": ["注册", "Registrarse"],
  "Create your account": ["创建账号", "Crea tu cuenta"],
  "Name": ["姓名", "Nombre"],
  "Password (min 8 chars)": ["密码（至少 8 位）", "Contraseña (mín. 8 caracteres)"],
  "Start free": ["免费开始", "Empieza gratis"],
  "Have an account?": ["已有账号？", "¿Ya tienes cuenta?"],
  "Creating…": ["创建中…", "Creando…"],

  // Dashboard
  "Start a mock interview": ["开始模拟面试", "Iniciar entrevista simulada"],
  "Streak": ["连续学习", "Racha"],
  "days": ["天", "días"],
  "Interviews completed": ["已完成面试", "Entrevistas completadas"],
  "Recent avg score": ["近期平均分", "Puntuación media reciente"],
  "Tasks pending": ["待办任务", "Tareas pendientes"],
  "Today's tasks": ["今日任务", "Tareas de hoy"],
  "View all": ["查看全部", "Ver todas"],
  "No pending tasks. Finish a mock interview to generate a study plan.":
    ["暂无待办任务。完成一场模拟面试即可生成学习计划。",
     "No hay tareas pendientes. Completa una entrevista simulada para generar un plan de estudio."],
  "Weak areas": ["薄弱领域", "Áreas débiles"],
  "No weak areas identified yet.": ["尚未发现薄弱领域。", "Aún no se han identificado áreas débiles."],
  "This week": ["本周目标", "Esta semana"],
  "Complete your pending tasks, then take the recommended mock interview to measure progress.":
    ["完成待办任务，然后进行推荐的模拟面试来检验进步。",
     "Completa tus tareas pendientes y luego haz la entrevista simulada recomendada para medir tu progreso."],

  // Tasks page
  "Learning tasks": ["学习任务", "Tareas de aprendizaje"],
  "Rebuild study plan": ["重建学习路线", "Rehacer plan de estudio"],
  "Generate study plan": ["生成学习路线", "Generar plan de estudio"],
  "Planning…": ["规划中…", "Planificando…"],
  "Rebuild the study plan? Pending plan tasks will be replaced.":
    ["重建学习路线？未完成的计划任务将被替换。",
     "¿Rehacer el plan de estudio? Las tareas pendientes del plan serán reemplazadas."],
  "Up next": ["接下来", "A continuación"],
  "Week {n}": ["第 {n} 周", "Semana {n}"],
  "task": ["个任务", "tarea"],
  "tasks": ["个任务", "tareas"],
  "Completed": ["已完成", "Completadas"],
  "Mark done": ["标记完成", "Marcar hecho"],
  "Take quiz": ["去做题", "Hacer quiz"],
  "Start interview": ["开始面试", "Iniciar entrevista"],
  "Open Learn": ["去学习", "Ir a Aprender"],
  "from interview": ["来自面试", "de la entrevista"],
  "study plan": ["学习路线", "plan de estudio"],
  "Due": ["截止", "Vence"],
  "No tasks yet — finish onboarding to generate a study plan, or complete a mock interview.":
    ["还没有任务——完成引导设置生成学习路线，或先完成一场模拟面试。",
     "Sin tareas todavía: completa la configuración inicial para generar un plan, o haz una entrevista simulada."],

  // Learn page
  "Chapter quiz →": ["章节测试 →", "Quiz del capítulo →"],
  "Mastery": ["掌握度", "Dominio"],
  "Coach": ["教练", "Coach"],
  "Pick a topic to start learning.": ["选择一个知识点开始学习。", "Elige un tema para empezar a aprender."],
  "Ask the coach anything about this topic.": ["就这个知识点向教练随便提问。", "Pregunta al coach lo que quieras sobre este tema."],
  "Ask the coach…": ["向教练提问…", "Pregunta al coach…"],
  "Send": ["发送", "Enviar"],
  "Coach is thinking…": ["教练思考中…", "El coach está pensando…"],
  "Coding": ["算法编程", "Programación"],
  "Backend": ["后端", "Backend"],
  "System Design": ["系统设计", "Diseño de sistemas"],
  "CS Fundamentals": ["计算机基础", "Fundamentos de CS"],
  "Infrastructure": ["基础设施", "Infraestructura"],
  "AI Infrastructure": ["AI 基础设施", "Infraestructura de IA"],
  "Machine Learning": ["机器学习", "Machine Learning"],
  "Lesson →": ["辅导课 →", "Lección →"],
  "Tutor": ["辅导老师", "Tutor"],
  "Tutor is thinking…": ["老师思考中…", "El tutor está pensando…"],
  "Answer the tutor… (Enter to send, Shift+Enter for newline)":
    ["回答老师…（Enter 发送，Shift+Enter 换行）", "Responde al tutor… (Enter para enviar)"],
  "Read the tutor's replies aloud": ["自动朗读老师的回复", "Leer en voz alta las respuestas del tutor"],
  "Restart lesson": ["重新上课", "Reiniciar lección"],
  "Restart this lesson? The current conversation will be cleared.":
    ["重新开始这节课？当前对话将被清空。", "¿Reiniciar la lección? La conversación actual se borrará."],
  "Practice editor": ["练习编辑器", "Editor de práctica"],
  "Hint": ["提示", "Pista"],
  "Dismiss": ["关闭", "Cerrar"],
  "Insert into editor": ["插入编辑器", "Insertar en el editor"],
  "Ask for a hint on the current exercise": ["就当前练习要一个提示", "Pide una pista sobre el ejercicio actual"],
  "Share with tutor": ["发给老师点评", "Compartir con el tutor"],
  "Switch the editor language": ["切换编辑器语言", "Cambiar el lenguaje del editor"],
  "explain": ["讲解", "explicar"],
  "quiz": ["测验", "quiz"],
  "flashcards": ["记忆卡", "tarjetas"],
  "review mistakes": ["错题复习", "repasar errores"],

  // Voice
  "Voice input": ["语音输入", "Entrada de voz"],
  "Stop recording": ["停止录音", "Detener grabación"],
  "Transcribing…": ["转写中…", "Transcribiendo…"],
  "Auto-read": ["自动朗读", "Leer en voz alta"],
  "Read the interviewer's replies aloud": ["自动朗读面试官的回复", "Leer en voz alta las respuestas del entrevistador"],
  "Read the coach's replies aloud": ["自动朗读教练的回复", "Leer en voz alta las respuestas del coach"],
  "Read-aloud speed": ["朗读速度", "Velocidad de lectura"],
  "Voice call": ["语音通话", "Llamada de voz"],
  "Hang up": ["挂断", "Colgar"],
  "Connecting…": ["连接中…", "Conectando…"],
  "Talk to the interviewer in a live voice call — everything is transcribed into the chat":
    ["和面试官实时语音对话——内容会自动转成字幕进入聊天记录",
     "Habla con el entrevistador en una llamada de voz en vivo: todo se transcribe al chat"],
  "Talk to the tutor in a live voice call — everything is transcribed into the lesson":
    ["和老师实时语音对话——内容会自动转成字幕进入课程记录",
     "Habla con el tutor en una llamada de voz en vivo: todo se transcribe a la lección"],

  // Practice page
  "Short, targeted sessions — 5, 15 or 30 minutes.":
    ["短小精准的练习——5、15 或 30 分钟。", "Sesiones cortas y enfocadas: 5, 15 o 30 minutos."],
  "Daily Drill": ["每日一练", "Ejercicio diario"],
  "A 15-minute mixed drill from your weakest topics.":
    ["15 分钟混合练习，专攻你最薄弱的知识点。", "Un ejercicio mixto de 15 minutos con tus temas más débiles."],
  "Coding Practice": ["编程练习", "Práctica de código"],
  "Take a focused coding mock interview instead.":
    ["来一场专注的编程模拟面试。", "Haz una entrevista simulada de programación enfocada."],
  "System Design Mini Drill": ["系统设计小练习", "Mini ejercicio de diseño"],
  "One design prompt with coach feedback.": ["一道设计题 + 教练点评。", "Un ejercicio de diseño con feedback del coach."],
  "Topic quizzes via the coach (quiz mode).": ["通过教练做知识点测验。", "Quizzes de temas con el coach."],
  "Flashcards": ["记忆卡片", "Tarjetas"],
  "Rapid-fire concept cards via the coach.": ["快节奏概念卡片复习。", "Tarjetas de conceptos rápidas con el coach."],
  "Mistake Review": ["错题复习", "Repaso de errores"],
  "Re-test the mistakes from your last interviews.":
    ["重测你最近面试中犯过的错误。", "Vuelve a practicar los errores de tus últimas entrevistas."],
  "Quiz": ["测验", "Quiz"],
  "min": ["分钟", "min"],

  // Interview setup
  "New mock interview": ["新建模拟面试", "Nueva entrevista simulada"],
  "Interview type": ["面试类型", "Tipo de entrevista"],
  "Algorithm problem with a live Python sandbox":
    ["算法题 + 实时代码沙箱", "Problema de algoritmos con sandbox en vivo"],
  "Backend design with a text whiteboard": ["后端设计 + 文字白板", "Diseño backend con pizarra de texto"],
  "Role": ["目标岗位", "Puesto"],
  "Level": ["级别", "Nivel"],
  "Company style": ["公司风格", "Estilo de empresa"],
  "Duration (minutes)": ["时长（分钟）", "Duración (minutos)"],
  "Difficulty": ["难度", "Dificultad"],
  "Language": ["编程语言", "Lenguaje"],
  "Focus areas (optional)": ["重点领域（可选）", "Áreas de enfoque (opcional)"],
  "Preparing your interviewer…": ["正在准备你的面试官…", "Preparando a tu entrevistador…"],

  // Interview room
  "End Interview": ["结束面试", "Terminar entrevista"],
  "Interviewer": ["面试官", "Entrevistador"],
  "You": ["你", "Tú"],
  "Interviewer is typing…": ["面试官正在输入…", "El entrevistador escribe…"],
  "Talk to your interviewer… (Enter to send, Shift+Enter for newline)":
    ["和面试官对话…（Enter 发送，Shift+Enter 换行）",
     "Habla con tu entrevistador… (Enter para enviar, Shift+Enter para nueva línea)"],
  "Ask Clarification": ["澄清问题", "Pedir aclaración"],
  "Request Hint": ["请求提示", "Pedir pista"],
  "Could I get a hint?": ["能给我一个提示吗？", "¿Me das una pista?"],
  "Run Code": ["运行代码", "Ejecutar código"],
  "Running…": ["运行中…", "Ejecutando…"],
  "Submit": ["提交", "Enviar solución"],
  "Design whiteboard (plain text / markdown)": ["设计白板（纯文本 / Markdown）", "Pizarra de diseño (texto / markdown)"],
  "Share design with interviewer": ["把设计发给面试官", "Compartir diseño con el entrevistador"],
  "Loading interview…": ["加载面试中…", "Cargando entrevista…"],
  "End the interview?": ["确定要结束面试吗？", "¿Terminar la entrevista?"],
  "Generate your scoring report now? Choose Cancel to end without a report — you can generate it later from the report page.":
    ["现在生成评分报告吗？选择“取消”则只结束面试，之后可以在报告页随时生成。",
     "¿Generar tu informe de evaluación ahora? Elige Cancelar para terminar sin informe: podrás generarlo después desde la página del informe."],

  // Report page
  "Interview report": ["面试报告", "Informe de entrevista"],
  "Start your study plan": ["开始学习计划", "Empezar plan de estudio"],
  "Overall score": ["总分", "Puntuación global"],
  "Hire signal": ["录用信号", "Señal de contratación"],
  "Level assessment": ["级别评估", "Evaluación de nivel"],
  "Summary": ["总结", "Resumen"],
  "Dimension scores": ["各维度评分", "Puntuación por dimensión"],
  "Strengths": ["优势", "Fortalezas"],
  "Weaknesses": ["弱点", "Debilidades"],
  "Key mistakes": ["关键错误", "Errores clave"],
  "Missed opportunities": ["错失的机会", "Oportunidades perdidas"],
  "Ideal answer outline": ["理想答案思路", "Esquema de la respuesta ideal"],
  "Evidence": ["评分依据", "Evidencia"],
  "Your auto-generated study plan": ["自动生成的学习计划", "Tu plan de estudio generado automáticamente"],
  "No tasks generated for this session.": ["本场面试未生成任务。", "No se generaron tareas para esta sesión."],
  "Generating report…": ["报告生成中…", "Generando informe…"],
  "No report yet": ["还没有报告", "Aún no hay informe"],
  "This interview ended without scoring. Generate the report now to get your scores and study plan.":
    ["这场面试结束时没有评分。现在生成报告即可获得评分和学习计划。",
     "Esta entrevista terminó sin evaluación. Genera el informe ahora para obtener tu puntuación y plan de estudio."],
  "Generate report": ["生成报告", "Generar informe"],

  // Quiz page
  "Chapter quiz": ["章节测试", "Quiz del capítulo"],
  "Back to Learn": ["返回学习", "Volver a Aprender"],
  "Preparing questions…": ["出题中…", "Preparando preguntas…"],
  "Mastery is now": ["掌握度现为", "Tu dominio ahora es"],
  "learning task completed ✓": ["个学习任务已完成 ✓", "tarea de aprendizaje completada ✓"],
  "Try another set": ["再来一组", "Otra ronda"],
  "Back to tasks": ["返回任务", "Volver a tareas"],
  "Submit answers": ["提交答案", "Enviar respuestas"],
  "Grading…": ["判分中…", "Calificando…"],
  "Answer all questions to submit": ["答完全部题目后提交", "Responde todas las preguntas para enviar"],
  "✓ Correct.": ["✓ 答对了。", "✓ Correcto."],
  "✗ Not quite.": ["✗ 不太对。", "✗ No exactamente."],

  // Progress page
  "Interviews": ["面试场数", "Entrevistas"],
  "Tasks completed": ["已完成任务", "Tareas completadas"],
  "Skill mastery": ["技能掌握度", "Dominio de habilidades"],
  "Complete tasks and interviews to build your skill map.":
    ["完成任务和面试来构建你的能力地图。", "Completa tareas y entrevistas para construir tu mapa de habilidades."],
  "Interview history": ["面试历史", "Historial de entrevistas"],
  "Date": ["日期", "Fecha"],
  "Type": ["类型", "Tipo"],
  "Score": ["得分", "Puntuación"],
  "Signal": ["信号", "Señal"],
  "Report": ["报告", "Informe"],
  "No interviews yet.": ["还没有面试记录。", "Aún no hay entrevistas."],
  "in progress": ["进行中", "en curso"],

  // Onboarding
  "Set up your prep plan": ["设置你的备战计划", "Configura tu plan de preparación"],
  "This calibrates your coach, interviewer and study plan.":
    ["这些信息用于校准你的教练、面试官和学习计划。",
     "Esto calibra a tu coach, entrevistador y plan de estudio."],
  "Target role": ["目标岗位", "Puesto objetivo"],
  "Current level": ["当前级别", "Nivel actual"],
  "Target level": ["目标级别", "Nivel objetivo"],
  "Target companies": ["目标公司", "Empresas objetivo"],
  "Interview date (optional)": ["面试日期（可选）", "Fecha de entrevista (opcional)"],
  "Hours per week": ["每周可投入小时", "Horas por semana"],
  "Preferred language": ["偏好编程语言", "Lenguaje preferido"],
  "Strong areas": ["擅长领域", "Áreas fuertes"],
  "Finish setup & build my study plan": ["完成设置并生成学习路线", "Finalizar y crear mi plan de estudio"],
  "Saving…": ["保存中…", "Guardando…"],
  "Building your study plan…": ["正在生成学习路线…", "Creando tu plan de estudio…"],

  // Landing
  "Mock interviews that turn into a": ["模拟面试自动转化为", "Entrevistas simuladas que se convierten en un"],
  "personalized study plan": ["个性化学习计划", "plan de estudio personalizado"],
  "Learn → practice → mock interview → automatic scoring → review → new plan. The loop that most interview tools are missing.":
    ["学习 → 练习 → 模拟面试 → 自动评分 → 复盘 → 新计划。这是大多数面试工具缺失的闭环。",
     "Aprende → practica → entrevista simulada → evaluación automática → repaso → nuevo plan. El ciclo que le falta a la mayoría de las herramientas."],
  "Start your free mock interview": ["免费开始你的第一场模拟面试", "Empieza tu entrevista simulada gratis"],
};

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (text: string) => string;
}

const I18nContext = createContext<I18nContextValue>({
  lang: "en",
  setLang: () => undefined,
  t: (text) => text,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "zh" || saved === "es" || saved === "en") setLangState(saved);
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    localStorage.setItem(LANG_KEY, next);
    document.documentElement.lang = next;
    // Keep the backend profile in sync so the AI answers in this language too.
    api.updateProfile({ locale: next }).catch(() => undefined);
  }, []);

  const t = useCallback(
    (text: string) => {
      if (lang === "en") return text;
      const entry = DICT[text];
      if (!entry) return text;
      return lang === "zh" ? entry[0] : entry[1];
    },
    [lang]
  );

  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
